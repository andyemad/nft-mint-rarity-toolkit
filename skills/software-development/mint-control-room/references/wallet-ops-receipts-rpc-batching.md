# Wallet operations: receipt counting, RPC batching, DI defaults

Covers `app/api/wallets/route.ts` (create / distribute / consolidate), the
wallet-ops history log (`lib/server/wallet-ops-store.ts` + `/api/wallet-ops`),
and the `lib/server/receipt-status.ts` helper. Session-tested 2026-08-24.

## A. Consolidate "swept N/13 (~0.000000 ETH)" lies — the receipt-parsing bug
The sweep reported ~0 ETH received even when every tx landed on-chain, and often
"0/13 confirmed" / "Swept 0". Root causes, in order of how they present:

1. **JSON.parse on an already-parsed object.** `rawRpcCall` returns a PARSED
   OBJECT for a mined `eth_getTransactionReceipt` (the RPC's JSON body is decoded
   by `fetch().json()` already). Old code did `JSON.parse(await rawRpcCall(...))`
   → `JSON.parse(object)` throws → every confirmation silently discarded →
   `totalReturned` stayed 0. **Fix:** extract a shared `parseReceiptStatus(raw)`
   helper (`lib/server/receipt-status.ts`) that accepts object-shaped,
   JSON-string-shaped, and pending-null receipts and returns status or null
   without throwing. Point the route's `receiptFor` at it.
2. **Pending / unmined receipts.** While a tx is unmined the RPC returns
   `result: null`, which makes `rawRpcCall` THROW "returned no result" (it does
   `if (!payload.result) throw`). That is *pending*, not an error — catch and
   keep polling, don't treat as terminal.
3. **Reporting books "broadcast" as success but never adds to the ETH total.**
   At the end of the confirm window, txs that never got a receipt should be
   marked `broadcast` (honest) and the swept count should include them, but the
   ETH-received number only counts `0x1` confirmations. Keep the two honest and
   separate — never report a huge "broadcast" count with 0 ETH as a lie, and
   never call the run failed when confirmations actually landed.

## B. Rate limits: batch balance reads, parallelize broadcasts
- `GET /api/wallets` shipped 13 `eth_getBalance` calls at once
  (`Promise.all`) → Robinhood RPC HTTP 429 mid-list (saw "RPC HTTP 429 (transient,
  retrying)" on fabw_13). **Fix:** send ONE JSON-RPC batch
  (`[{jsonrpc,id,method:"eth_getBalance",params:[addr,"latest"]}, …]`) covering
  every wallet + the OG wallet, with a paced sequential re-read fallback if the
  batch fails. 1 HTTP call instead of 13.
- Consolidate now reads balances in one batch and broadcasts all sweeps in
  PARALLEL (`Promise.all`), then polls receipts in short windows (~12s), instead
  of the old serial "read → sign → send" loop that dragged a 13-wallet sweep to
  ~40s before the first tx left.

## C. Legacy type-0 txs + gas price floor
`sendFrom` uses `type: 0` (legacy) txs for exact-balance sweeps because ethers'
default EIP-1559 envelope overhead can push an exact-balance transfer under
"insufficient funds for intrinsic cost". Gas price: fetch `eth_gasPrice`, add
~20% +1. Sweep value = `balance − 21000×gasPrice×2` (2x headroom for base-fee
tickup; dust left behind is fine). A tx with that encoding still failed once
with `intrinsic gas too low` when the session had the gas price pinned far below
the chain's floor — trust the live `eth_gasPrice`, don't hardcode a stale price.

**Update (fixed 2026-08-24, see also rh-chain-wallet-ops-pitfalls §8):** the
"intrinsic gas too low" root cause is a TRANSIENT node-side gas-price floor well
above `eth_gasPrice`. `sendFrom` now retries ≤3× escalating price (+20%, ×1.5)
on /intrinsic gas too low|gas price/i, and distribute routes through it too.
Safe diagnosis probe: sign a tx with nonce 999999999 — it can never mine — and
eth_sendRawTransaction it; a `nonce too high` reply proves gas checks PASSED at
that price. Verified: 13/13 confirmed on two consecutive real distributes.

## D. The wallet-ops history log needs real fs defaults
`wallet-ops-store.ts` `appendOp`/`readOpsLog` accepted DI via `deps` (mkdir,
read, write, chmod, rename) but had NO real defaults — the route called
`appendOp(...)` with no deps, so production threw `a.mkdir is not a function`
(minified name) right after the first create/distribute/consolidate. **Fix:** add
real `node:fs/promises` defaults (`defaultMkdir` etc.) so production callers never
need to inject, while tests still override per-call via `deps`. This class of bug
(internal util with required DI + a caller that forgets to inject) recurs — when
tracing a "X is not a function" in a route, check the store util's deps defaults
first.

## Verification / restart
`curl -s http://127.0.0.1:3000/api/wallets | python3 -m json.tool`,
`launchctl kickstart -k gui/$(id -u)/com.the agent.rh-mint-room`, then
`curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/`. Tell the user to
hard-reload (Cmd+Shift+R). Regression tests: `tests/receipt-status.test.ts`.
