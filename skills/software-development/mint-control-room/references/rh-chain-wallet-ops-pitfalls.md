# RH-chain wallet-op & RPC pitfalls (wallets API, consolidate/distribute/create)

Session-tested bugs and their fixes for the Wallets page ops
(`app/api/wallets/route.ts`, `lib/server/wallet-ops-store.ts`, `lib/server/rpc.ts`)
on Robinhood chain. the user drives these one-click; he wants them **fast** and to
report **honest on-chain results** — no hung buttons, no false "0/N" summaries.

## 1. RH RPC rate-limits parallel bursts → batch JSON-RPC
Firing N `eth_getBalance` calls via `Promise.all` (13 wallets + OG) trips HTTP 429
mid-list ("RPC HTTP 429 transient"). Fix: send ONE JSON-RPC batch array in a single
POST (`[{jsonrpc,id,method,params}, ...]`), map results back by `id`. If the batch
fails wholesale (unsupported/throttled), fall back to sequential reads with a
~120ms gap. Same batch pattern used by the vendored OSNM-Z engine.

## 2. `rawRpcCall` returns `payload.result` — object results must NOT be JSON.parse'd
`rawRpcCall` returns `payload.result` as-is. For `eth_getTransactionReceipt` that is
a JS **object**, not a string. `JSON.parse(object)` throws synchronously, gets
silently swallowed by a `catch {}`, so the receipt never resolves → 45s timeout →
false "swept 0/N (0 ETH)" + the button stuck on "Sweeping…" — even though the txs
mined fine on-chain. Fix in receipt polling:
```ts
const raw = await rawRpcCall("eth_getTransactionReceipt",[hash],chain);
if (!raw || raw === "null") return null;
const parsed = JSON.parse(raw); // only when raw is a JSON string
// otherwise treat any payload containing "status" via regex /"status"\s*:\s*"(0x[01])"/
```
After a bounded confirm window (RH confirms a legacy transfer in ~1-2 blocks, so
~12s is plenty), mark anything unconfirmed as `"broadcast"` (honest) rather than
lying "0/N". Verify on-chain with `eth_getBalance` — the sweep may well have landed.

## 3. Exact-balance sweeps: use legacy type-0 txs
ethers defaults to EIP-1559 whose envelope overhead can push exact-balance sweeps
under "insufficient funds for intrinsic cost". Force `type: 0` and `gasLimit: 21000n`.

## 4. Engine's upfront funding check = gasLimit × maxFeePerGas — pin fees low
OSNM-Z requires each wallet to afford `GAS_LIMIT(300k) × maxFeePerGas` *before*
broadcast (worst case). With `FEE_AUTOMATIC=true` on RH this rounds to ~0.0003 ETH —
which is rightly treated as absurd for a mint on a cheap chain. Pin
`FEE_AUTOMATIC=false`, `MAX_FEE_PER_GAS_GWEI=0.1`, `MAX_PRIORITY_FEE_PER_GAS_GWEI=0.01`
in the engine .env (in `lib/server/multi-runner.ts` buildMultiRuntimeConfig). RH base
fee is ~0.001-0.02 gwei; 0.1 gwei is 100x headroom. The engine's `parse_gwei` accepts
fractional gwei. Funding requirement drops to ~0.00004 ETH.

## 5. Consolidate speed: parallel broadcasts, batched balance read
Old serial loop (balance → sign → send ×N) took ~40s before the first sweep left.
Fix: one batched `eth_getBalance`, then `Promise.all` the sends (each wallet has its
own nonce so parallel is safe), short ~12s confirm window. Lands the whole sweep in
~2-3s.

## 6. `appendOp` / store defaults — inject real fs fns
`wallet-ops-store.ts` `appendOp`/`readOpsLog` require deps (`deps.mkdir!` etc.). If a
route calls them with no deps, minified runtime error "a.mkdir is not a function"
(surfaces on consolidate/create/distribute). Fix: give the store real defaults
(`import { mkdir, readFile, writeFile, chmod, rename } from "node:fs/promises"` +
`const d = deps.mkdir ?? mkdir; ...`) so production callers need not inject; tests
override per-call and stay hermetic. Cast `readFile`'s encoding to `BufferEncoding`.

## 7. Wallets page — give the user a visible Refresh control
Balances only reloaded on mount / after actions, so after a launchd restart the page
looked stale and there was no way to force it → "refresh balances doesn't work".
Add a `↻ Refresh balances` button + `updated HH:MM:SS` timestamp (local state
`lastUpdated`) + `Refreshing…` busy label so it visibly works.

## 8. Transient node gas-price floor → "intrinsic gas too low" batch failures (fixed 2026-08-24)

the user reported "distributor wasn't working" / "Distributed to 0/13 wallets". Ops log
showed whole batches of legacy type-0 txs (gasLimit 21000, gasPrice = eth_gasPrice×1.2,
well-funded sender) rejected with `-32000 "intrinsic gas too low"` — while the SAME
code succeeded at other times. Diagnosis method that pinned it: re-sent signed probes
with a **bogus nonce (999999999)** via eth_sendRawTransaction — safe because such a tx
can never mine; the node validates gas BEFORE queueing, so `nonce too high` response
= gas checks PASSED at today's price. Conclusion: RH's node intermittently enforces a
gas-price floor well above `eth_gasPrice`; single-shot pricing fails whenever the
floor spikes mid-batch.

Fix in `app/api/wallets/route.ts`: shared `sendFrom()` helper retries up to 3 times
with escalating gas price (+20% first, ×1.5 per retry) when the error matches
/intrinsic gas too low|gas price/i; other errors throw immediately. Both distribute
and consolidate sweeps now route through it (distribute previously had its own inline
send with fixed 1.2× pricing). Verified live: 13/13 confirmed on two consecutive
real distributes.

Related: one failing batch in the ops log contained EIP-1559 raws (`0x02f8…`) from
`lib/server/custom-runner.ts` (mint engine path uses maxFeePerGas) — different path;
the wallet-ops rule stays legacy-only.

## Verification / restart
- Direct API probe: `curl -s http://127.0.0.1:3000/api/wallets` (should answer in
  ~0.2-0.5s with fresh balances).
- Restart: `launchctl kickstart -k gui/$(id -u)/com.the agent.rh-mint-room`; then
  `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/wallets`.
- the user is on a browser tab — tell him to hard-reload (Cmd+Shift+R) to pick up a new
  client bundle after restarts. Wallets `0xde…` hold ~dust (0.00001 ETH) after a
  free-mint run burns gas; a real (paid) mint's leftovers are what consolidate exists.

## ⚠️ Port-3000 zombie trap (bit twice, 2026-08-24)

When dev-server responses look stale after code edits, FIRST check who owns port
3000: `lsof -nP -iTCP:3000 -sTCP:LISTEN`. Orphaned `next-server` processes
(parent pid 1, no watcher) keep serving old compiled code and silently eat every
request — while a freshly started `next dev`, finding 3000 busy, binds **3001**
instead. You then debug "why is my fix not live" against the wrong process.
Detection recipe: add a unique marker string to source, grep `.next/dev/server/
chunks/` for it; absent marker + API still answering = zombie on 3000. Fix:
`kill -9` ALL next-server pids, wipe `.next`, restart via a tracked background
terminal (never a `(nohup … &)` subshell — those die and orphan the worker), then
verify the bound port from the startup log before testing anything.

This bit a THIRD time the same evening: after all kills, `next dev` still bound
**3001** (something re-squatted 3000 within seconds), and the user's tab pointed at
the old port. Always end a dev-server recovery by telling the user which port the
app is actually on.

## NFT-consolidate owner check vs gated contracts (fixed 8/24 evening)

First real use of Send-to-OG errored three ways, all in
`app/api/nft-inventory/route.ts`:

1. Route-level `providerFor()` still passed the `{chainId}` object — same
   ethers pitfall as nft-listing. Symptom exactly as screenshot: "invalid
   network object name or chainId". Pass `undefined`.
2. Keyfile lookup used `${ownerName}_key`; OG rows carry ownerName "OG wallet"
   → map to `bot_wallet_key`.
3. The pre-transfer defensive `ownerOf` check blocked everything on gated
   contracts: the test collection reverts EVERY ownerOf with custom selector
   `0xdf2d9b42` (same gating family as its reverting isApprovedForAll).
   New semantics: revert/null = cannot verify → proceed on the fresh
   inventory scan; a returned address ≠ scanned owner = block. Verified:
   clay #3309 sweep tx confirmed on-chain after these fixes.
