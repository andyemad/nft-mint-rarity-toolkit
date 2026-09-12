# Session 2026-08-25 — Direct-contract minting built (non-OpenSea collections)

the user missed the Doge Brokers mint because the control room only spoke OpenSea
SeaDrop/SIWE ("the collection is not an OpenSea-hosted SeaDrop"). He ordered:
"build whatever it takes to get this fully functional. dev loop + implement
spec." The generic direct-mint path was built and live-verified in one session.

## What shipped

- `lib/server/direct-detect.ts` — read-only eth_call detection: mint-candidate
  ladder (`mint(uint256)` → `publicMint(uint256)` → `mintTo(address,uint256)`
  → `safeMint` → `publicSaleMint` → `mintPublic`), price discovery BY
  SIMULATION, supply/maxPerWallet getters. ERC-165 `supportsInterface` reverts
  on contracts that skip it → kind falls back to `erc721` when a working mint
  + name exist (Doge Brokers case).
- `lib/server/direct-runner.ts` — EngineSession contract identical to
  multi-mint (`direct-<ts>` ids, same statuses), fab_wallets.json registry with
  keyfile/address verification, simulate-every-wallet-first rehearse (zero
  spend), funding reserve = same math as multi-runner (~0.0001/wallet),
  receipt verified = status 1 + Transfer(0x0→wallet) count ≥ qty. Live still
  gated by rehearsal + arm lock.
- `app/api/direct-mint/route.ts` — GET `?id=` session | `?inspect=1&contract=
  &quantity=&chain=` read-only inspection; POST action=mint|cancel.
  Loopback + same-origin guards copied from multi-mint.
- `components/DirectMintPanel.tsx` — "Mint direct contract" section (#13) on
  Command Center below MultiMintPanel: Inspect shows name/price/supply in
  plain English before any spend decision.
- Tests: `tests/direct-mint.test.ts` (calldata encoding via real keccak,
  decodeErrorWords filters absurd words >1000 ETH, quoteSpend items+bumped-gas
  reserve). 7/7 green.

## Price discovery pitfalls — Doge Brokers got me TWICE in one session

1. First report told the user price = 0.01 ETH from reading an
   `InsufficientValue(uint256,uint256)` revert as (provided=0.0001,
   required=0.01). Word order is ambiguous without the contract source. Truth,
   proven later by a value ladder: **price = 0.0001 EXACTLY** — 0.00005
   reverts, 0.00009 reverts, 0.0001 passes, 0.0002 REVERTS (strict equality;
   overpays rejected too).
   Lesson: never report a price decoded from one revert word pair. Bisect
   passing values with eth_call from a funded address; a single PASS at value V
   plus reverts just below pins the exact price.
2. An eth_call that SUCCEEDS with empty result (`result:"0x"`) at candidate
   value V is the ground-truth "mint passes at V" signal. My detector's getter
   retry found this correctly — my manual curl labels were what lied.
3. rawRpcCall throws bare `"execution reverted"` with NO hex data, so custom-
   error decoding needs direct curl inspection of the RPC response, not the
   thrown message.

Detection algorithm that works: probe value 0n → if revert, decode custom-error
words as candidate prices and retry each → else try getters (`price()`,
`mintPrice()`, …) × quantity → accept first simulated-pass value.

## Wrong-directory write trap

Wrote new files to `~/mint-control-room/lib/server/` instead of
`~/Projects/mint-control-room/`. A stray similarly-named dir silently
accepts writes; tsc then can't find modules. Fix: `mv` into the real repo,
delete the stray (needs approval), re-run project tsc. Always confirm cwd with
`pwd && git rev-parse --show-toplevel` before creating files in a repo.

## State at session end (NOT finished)

Full suite run, production build + launchd restart, and commit were PENDING —
the tool-call budget expired mid-task. Next session: `npm test`, `npm run
build`, kickstart launchd, commit (files: direct-detect.ts, direct-runner.ts,
direct-mint/route.ts, DirectMintPanel.tsx, CommandCenter.tsx import+render,
tests/direct-mint.test.ts, .hermes/plans/direct-mint-spec.md). Then the user can
Inspect → dry-run → LIVE from the UI. Doge Brokers confirmed open at 8375/10000,
max 50/wallet, price 0.0001 ETH/mint (~0.001 total for all 10 wallets).

the user's frustration signal worth remembering: missing a mint he was actively
trying to hit reads as negligence, not backlog. Capability gaps discovered
mid-mint should be named immediately with a build plan, not explained away.
