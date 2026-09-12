# Multi-mint / engine-protocol & message-mapping lessons

Covers the multi-wallet mint path: `components/MultiMintPanel.tsx`,
`lib/server/engine-protocol.ts`, `app/api/multi-mint/route.ts`, plus how
`.runtime/sessions/multirun-*.json` exposes the real run log. These are the
session-tested bugs from the 2026-08-24 "multi wallet mint" + "consolidate"
reports.

## A. Diagnose from the run log, not the screenshot or the summary line
Emad reports errors with `web.gem.elixir.sh/uploads/….png` screenshots. The two
big sources of truth are:
1. `.runtime/sessions/multirun-<ts>.json` → `logs[]` is the full OSNM-Z
   transcript (stages, funding checks, SIWE retries, tx hashes, "Mint confirmed
   for 0x… in block N", "transaction reverted in block M"). Read THIS to know
   what actually happened.
2. On-chain state via `eth_getBalance` / `eth_getTransactionReceipt`.
The summary line ("failed", "swept 0/N") frequently lies; the log + chain do not.

If `vision_analyze` returns an "attached natively" image you cannot parse into
text, OCR it: `tesseract <img> <out>` is installed (brew). It reads the exact
error strings that drive the fix.

## B. OpenSea SIWE 429 during auth — FIXED in engine (2026-08-25), don't just raise env knobs
The multi-mint flow authenticates every wallet with OpenSea SIWE before the
approval prompt. A synchronized burst of N wallets reads as abuse and 429s ALL
of them at once; fixed-cadence retries (8 × flat 3000ms) never outlast the
rate-limit window, so every wallet gets skipped → "no wallet remains eligible".
Raising `OPENSEA_MAX_ATTEMPTS`/`OPENSEA_RETRY_INTERVAL_MS` alone does NOT fix
this (proven: all 10 still failed at 8/3000).

The real fix (commit b19958a; verified in a fresh dry-run: 10/10 wallets
authenticated cleanly, and a 2/2 live multi-wallet mint through SIWE):
1. **Exponential backoff** in `engine/osnm-z/src/opensea.rs`: `retry_delay()`
   scales by a per-client transient-failure counter (`auth_attempts`, reset on
   success) → interval, 2×, 4× … capped at 16×.
2. **Staggered wallet starts** in `multi_mint.rs::prepare_sessions`: each
   manifest index sleeps `400ms × index` before authenticating, spreading the
   burst across the window instead of firing N at once.
Rebuild after touching the Rust: `cd engine/osnm-z && cargo build --release`
(then `cargo test --release`; 126 tests). The runner copies
`target/release/opensea-mint` per-run, so no extra deploy step.

## C. Phase selector must require an ACTIVE stage for live mints
`engine-protocol.ts` old regex matched `(active|upcoming)` for the stage line
`/N. Stage X | PUBLIC_SALE | active | … | available/`. For a LIVE mint, picking an
"upcoming" stage makes the contract revert ("transaction reverted in block N").
Fix: `allowed = this.input.live ? /active/ : /active|upcoming/` — live refuses
anything not active yet; rehearse may still validate an upcoming/schedulable
path. Also note a `max=1` stage reverts a duplicate mint cleanly (that is
expected, not a funding failure).

## D. Error-message mapping: don't conflate causes (the "low ETH" mislabel)
`MultiMintPanel.plainError()` originally mapped "no wallet remains eligible /
funding shortfall" → "wallets were low on ETH … top up". That was WRONG: the same
engine line also fires on a **contract revert** (`transaction reverted`) or an
**OpenSea SIWE 429 skip**, neither of which is a funding problem. Emad tops up,
still fails, and rightly gets angry at the misleading guidance. Order the checks
cause-first and keep the wording honest per cause:
1. SIWE 429 → OpenSea rate-limited, wait/retry.
2. `transaction reverted|execution reverted|EVM rerun` → contract rejected the
   mint: not open yet / stage gates / allowlist — NOT funding. Rehearse or check
   the mint page.
3. `no wallet remains eligible|funding shortfall` → generic "none could run the
   mint", point at contract/open-stage, suggest Rehearse first — do NOT claim
   low ETH unless the log actually shows a funding/shortfall line.
Rule: never map a generic engine failure to a specific cause unless the log shows
that cause. When in doubt, show the real log tail instead of a confident-but-wrong
translation.

## E. The multi-mint "reverted then 0 succeeded" is often a PARTIAL success
Example: 1 of 10 wallets authenticated through SIWE, minted a real NFT
("Mint confirmed for 0x… in block 45132852"), THEN a second tx on the same
max-1 wallet reverted and the run reported `succeeded=0, failed=1`. A run that
ends "failed" can still have landed real tokens. When reporting back, check the
log for any "Mint confirmed" lines and count those as real wins before telling
Emad "nothing worked". `transactionHashes[]` in the session JSON records every
tx that left.

## F. Emad wants these bugs to "never recur" — pin them with regression tests
When Emad says "make sure these errors don't occur again", the answer is NOT a
promise and NOT a memory note — it's regression tests that run in `npm test` and
fail the build if a change re-breaks the behavior. After fixing a bug in this
area, add a test to the matching file:
- `tests/execution.test.ts` — EngineProtocol behavior: live refuses `upcoming`
  stages (`["q\n"]`, status `blocked`); rehearse may pick `upcoming/schedulable`;
  multi-wallet flow still answers the final `Approve …? Answer [y/N]:` prompt
  (`n\n` rehearse → `rehearsed`, `yes\n` live → `armed`) even after the Funding
  prompt returned early.
- `tests/receipt-status.test.ts` — the shared `parseReceiptStatus` helper
  (`lib/server/receipt-status.ts`) accepts a mined receipt as parsed-object,
  JSON-string, or pending-null, and returns the status or null (never throws).
Making the fix a tested contract (not a one-off edit) is exactly what
"these errors don't recur" means operationally. Also reference the 
`references/wallet-ops-receipts-rpc-batching.md` for the consolidate-counting
bug that this discipline originates from.

## Verification / restart
Same as wallet-ops: `curl -s http://127.0.0.1:3000/api/wallets`,
`launchctl kickstart -k gui/$(id -u)/com.patelai.rh-mint-room`, then
`curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/`.
Tell Emad to hard-reload (Cmd+Shift+R) to get the new client bundle.

## G. Verifying engine fixes can MINT — never pipe `y` into a real run without checking mode first
Reproducing a multi-wallet fix by running the binary directly (`printf 'y\n' |
opensea-mint mint`) is a LIVE self-funded mint if the manifest wallets are
funded and the stage is active — it spent real RH gas in the 2026-08-24 session
before the second attempt got blocked as needing consent. Before any direct
engine verification run: (1) check whether the stage shows `active` (live) vs
`upcoming` (safe), or use an unfunded/throwaway wallet so funding checks stop
the run pre-broadcast; (2) treat any run that reaches "Submitting transaction"
as live spend needing Emad's explicit OK. Also remember the engine reads `.env`
from cwd (or parents), needs `RECIPIENT_ADDRESS` non-zero, and a valid RPC_URL
(`https://rpc.mainnet.chain.robinhood.com` for RH). If a test DID land tokens,
tell Emad exactly which wallet received them and what it cost — don't bury it.
Two more prompt-order traps hit 2026-08-25: the setup-funding "Top up … s to
skip" prompt fires BEFORE the approve y/N prompt (so `target\Ny\ns\n` misroutes
— feed `target\ns\n…`), and answering `s` when ALL wallets are underfunded
retains zero and errors out. Prompt order can differ between collections;
read the log tail before scripting stdin.

## H. Queue-and-forget races (queue-store / queue-worker)
Two race bugs fixed 2026-08-24, both worth remembering for any read-modify-write
JSON store with a background worker:
1. **Cancel losing to in-flight tick**: DELETE set state=canceled but the worker
   had loaded the queue earlier and overwrote it back to "waiting" — user saw a
   cancel silently undo itself. Fix at root: `updateQueue` refuses writes that
   would overwrite a canceled state (re-read before rename; discard stale write).
2. **Atomic-write ENOENT leaking raw paths into UI**: tmp-file + rename raced
   during server restarts; error text with `/Users/emad…` paths rendered verbatim.
   Fix: retry-once on rename failure AND sanitize all worker errors
   (`<local path>`) before persisting to the queue record.
Also UI rule Emad enforced: finished queues (canceled/expired/failed/confirmed/
blocked) must NOT render in "Set and forget" — filter them out so the section
disappears when nothing is active; stale cards contradicting the "0 ACTIVE"
badge read as broken.

## I. Funding reserve math + the "0.0001 wallet" target (2026-08-25)
The engine's setup-funding check demands `gas_limit × tx_count × maxFee ×
bump^(attempts-1) + mint_value` per wallet BEFORE it will run, even in rehearse.
With the old settings (300k gas × 2 txs × 0.1 gwei × two 1.125 bumps) that was
~0.00058 ETH/wallet and every ~0.0001-funded mint wallet failed. Emad's rule:
RH chain gas is near-free (base ~0.071 gwei, ceiling ~0.145), so the reserve
should fit his standard 0.0001/wallet funding for FREE mints. Shipped settings
in `lib/server/multi-runner.ts` (commit 9541ce2): `GAS_LIMIT=250000`,
`MAX_FEE_PER_GAS_GWEI=0.15` (must clear the observed base-fee ceiling),
`TRANSACTION_MAX_ATTEMPTS=2` (one bump) → reserve ≈0.000084 ETH/wallet.
Diagnosing shortfalls: required − (gas component) = the collection's real mint
price. Farting Unicorn looked free but its public sale now charges 0.0005/mint;
the shortfall delta exposed it exactly. When a run fails on funding, decompose
the number before telling Emad to top up — the price term may be the story.
Rehearse does NOT bypass funding checks; unfunded wallets stop pre-broadcast
(which also makes them safe for engine verification runs).

## J. Direct-contract minting SHIPPED (2026-08-25) — use it for non-OpenSea collections
OSNM-Z only speaks the OpenSea-hosted SeaDrop/SIWE protocol; a plain ERC721 with
a payable `mint()` returns "the collection is not an OpenSea-hosted SeaDrop" and
the OpenSea engine dies. Emad hit this on Doge Brokers (0x5Ef5…F3B) and called
the gap out sharply. The generic path now EXISTS (built 2026-08-25, live-
verified against Doge Brokers; suite/build/commit were still pending at session
end):

- `lib/server/direct-detect.ts` — read-only eth_call probe: tries mint
  candidates (`mint(uint256)`, `publicMint(uint256)`, `mintTo(address,uint256)`,
  `safeMint`, `publicSaleMint`, `mintPublic`), discovers price by SIMULATION,
  reads supply/maxPerWallet. ERC-165 `supportsInterface` reverts on contracts
  that skip it → kind falls back to `erc721` when a working mint + name exist.
- `lib/server/direct-runner.ts` — same EngineSession contract as multi-mint
  (`direct-<ts>` ids), same fab_wallets.json registry + keyfile/address check,
  simulate-every-wallet-first rehearse, funding reserve identical to §I,
  receipt = status 1 + Transfer(0x0→wallet). Live still requires rehearsal +
  arm lock.
- `app/api/direct-mint/route.ts` — GET ?id= | ?inspect=1&contract=&quantity=
  (read-only inspection), POST action=mint|cancel; loopback+same-origin guards.
- `components/DirectMintPanel.tsx` — "Mint direct contract" section on Command
  Center below MultiMintPanel: Inspect → dry-run → LIVE.

### Price discovery: getters lie, SIMULATE — and decode reverts carefully (Doge Brokers lesson, twice)
1. First pass got Doge Brokers WRONG in both directions within one session:
   read the `InsufficientValue(uint256,uint256)` revert words as
   (provided, required)=(0.0001, 0.01) and reported price 0.01; word order was
   ambiguous and the truth was **price = 0.0001 EXACTLY** — proven by a value
   ladder: 0.00005 revert, 0.00009 revert, 0.0001 PASS, 0.0002 revert (strict
   equality, overpays rejected). Never trust one decoded revert word pair;
   bisect actual passing values with eth_call from a funded address.
2. `eth_call` returning empty-but-successful (`result:"0x"`) at a candidate
   value = the mint passes at that price. That is the ground truth signal.
3. Detection algorithm that works: probe value 0n → if revert, decode custom
   error words as candidate prices and retry each → else try getter prices
   (`price()`, `mintPrice()`, …) × quantity → accept the first value whose
   simulated mint succeeds.
4. rawRpcCall throws bare "execution reverted" WITHOUT hex data, so revert
   decoding must happen via direct curl/RPC inspection when needed — the throw
   message alone carries nothing.

Manual fallback (pre-direct-mint repos or one-offs): same probes by hand per
steps above; ask Emad's OK per spend before broadcasting N paid mints.

### Ship-state update (same day, 2026-08-25)
Commit `8a90105` landed everything above: direct-detect.ts, direct-runner.ts,
app/api/direct-mint/route.ts, components/DirectMintPanel.tsx ("Mint direct
contract" panel on Command Center below MultiMintPanel), tests
`tests/direct-mint.test.ts` + `tests/direct-mint-panel.test.tsx` (13 new;
suite 772/772 across 84 files). Built and live on launchd port 3000.
Live-verified: inspect on Doge Brokers returns erc721 / mint(uint256) /
0.0001 ETH exactly / 8405-10000 supply; 10/10-wallet rehearse dry-run passed
with worst-case spend ~0.0014 ETH. No live broadcast has been performed
through this path yet.

Test-writing gotchas from this work:
- vitest config here has NO `globals`, so `.tsx` component tests MUST call
  `cleanup()` in `afterEach` — otherwise every render accumulates and
  TestingLibrary cascades "found multiple elements" errors across tests.
- Check button-label collisions across sibling panels before naming new
  buttons: DirectMintPanel's inspect button had to become "Read contract"
  because CommandCenter already owned "Inspect collection".

## K. Sold-out drops: fail fast BEFORE authenticating wallets (2026-08-25, dream-pups)
A live multi-wallet run armed, authenticated all 10 wallets, ran funding checks
for ~50s, then died with "OpenSea reported that the requested mint exceeds an
allocation or supply limit". Root cause: **dream-pups was fully minted**
(totalSupply = maxSupply = 444/444). The engine never checked supply pre-flight,
so it burned a minute of setup + N SIWE sessions against a drop that can never
mint again. Fixed in `engine/osnm-z/src/opensea.rs`:

1. `COLLECTION_QUERY` now fetches `maxSupply` / `totalSupply` — they exist ONLY
   inside an inline fragment (`... on Erc721SeaDropV1 { maxSupply totalSupply }`),
   NOT on the `Drop` interface and NOT on `Erc1155SeaDropV2`. Querying them at
   the interface level returns `FieldsOnCorrectType` errors → whole response is
   errors → misleading "GraphQL response drifted from the verified capture".
   Introspection queries are DISABLED on gql.opensea.io, so discover fields by
   trial fragments, not `__type`.
2. New `OpenSeaError::DropSoldOut`; `decode_collection` returns it when
   `total_supply >= max_supply > 0` — fires at resolution time, BEFORE any
   wallet authentication.
3. Verified E2E: dream-pups now fails in ~1s with "the drop is fully minted…";
   control check on a non-sold-out collection resolves and authenticates
   normally (no false positive). All 142 cargo tests pass.

Diagnostic playbook that found it (reusable for any "limit"-class mint error):
- The SIWE "attempt N/M failed transiently" WARN lines are NOISE that recovers;
  always read the END of `.runtime/sessions/multirun-*.json` `logs[]` for the
  FATAL `[ERROR]` line — don't fixate on the retries filling the screenshot.
- Check supply directly: `eth_call` `totalSupply()`=`0x18160ddd` and
  `maxSupply()`=`0xd5abeb01` on the NFT contract via
  `https://rpc.mainnet.chain.robinhood.com`. Equal ⇒ sold out, stop there.
- To see WHY a mint reverts on-chain: pull a recent successful mint tx
  (`eth_getLogs` Transfer with topic1=0x0), replay its exact calldata+value via
  `eth_call` from a funded address. SeaDrop sold-out reverts carry selector
  `0xa1148100`; the public-sale minter (`mintPublic`, selector `0x4b61cd6f` on
  SeaDrop 0x00005ea00ac477b1030ce78506496e8c2de24bf5) reverts `0xe12d2314`
  carrying (maxSupply, totalSupply) as its two words.
- OpenSea-side confirmation: the same gql endpoint with
  `{ collectionBySlug(slug) { drop { ... on Erc721SeaDropV1 { maxSupply totalSupply } } } }`.
- Engine direct-run env recipe (no app): cwd must contain `.env` with
  `RPC_URL=https://rpc.mainnet.chain.robinhood.com`, `FEE_AUTOMATIC=true`,
  `GAS_LIMIT=300000`, `WALLETS_FILE=<abs path>`, `SPONSORED=false`,
  and `RECIPIENT_ADDRESS=<non-zero>` (required when SPONSOR_KEY unset);
  copy an existing manifest from `.runtime/engine/multirun-*/wallets.json`.
  `calldata` subcommand is the safe no-signing probe.
