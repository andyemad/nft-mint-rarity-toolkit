# Session 2026-08-24/25 — UI polish, queue cancel, Set-and-forget filter

Session-specific detail for the Mint Room umbrella. All items were implemented,
tested (750/750 vitest + typecheck), rebuilt, and verified against the live
launchd service before commit.

## 1. Unstyled Advanced Task Panel (placeholder look)

Root cause: `AdvancedTaskPanel.tsx` referenced `styles.secondary`, but
`.secondary` does not exist in `CommandCenter.module.css` (grep exit 1). Every
tab/input/button rendered as an unstyled default browser control, which read as
"broken placeholders" even though all four modes (manual/opensea/merkle/batch)
were fully wired.

Fix: added real classes (`.atpTabs/.atpTab/.atpInput/.atpButton/.atpCopy/
.atpResult`) to CommandCenter.module.css, replaced inline `style={{}}` markup,
labeled the mystery `1`/`0` inputs ("Quantity" / "Value ETH"), active tab state.

Lesson: **when a Next.js CSS-module class name is missing, the component renders
unstyled rather than erroring.** If a user reports "placeholders"/"looks broken",
grep for every `styles.X` used in the component and confirm each exists in the
module CSS before assuming logic is missing.

## 2. Dead options removed (user rule)

CreateTaskGroupModal had a decorative mint-source rail (Manual / Scatter /
Rarible / Proof API / Signature API) with only OpenSea wired behind it. User:
"you have placeholders for the other stuff which is not good." Removed the rail
entirely; modal is one flow: paste collection link → Fetch → Create.

Standing preference: **remove dead UI rather than render disabled/fake options.**

## 3. Group vs task copy

Plain-English split now in TasksView toolbar hint: "Add task = rehearse a mint
yourself · New Group = arm an auto-mint that fires on eligibility". Rail titled
"Auto-Mint Groups", button "New Auto-Mint". Test expectations updated to match.

## 4. Queue-store ENOENT leak into UI

The queue-and-forget card displayed a raw ENOENT including local paths.
Causes fixed across two commits:

- `updateQueue` write race during server restarts → atomic tmp+rename with one
  retry; concurrent-update detection discards stale writes.
- Worker errors persisted verbatim → sanitize `~/...`
  prefixes to `<local path>` before storing on the queue record.
- Cleared stale error from the live queue file by hand after deploy.

## 5. Queue cancel vs worker tick race (critical)

First cancel returned 200/state:canceled but the worker's already-loaded tick
wrote stale "waiting" back over it. For a set-and-forget feature this is the
worst possible bug (cancel-after-arm would silently un-cancel).

Fix: cancel wins over in-flight ticks — updateQueue refuses writes that would
overwrite a `canceled` record; worker re-checks state before writing. Verified
held across multiple ticks. Commit `cbda045`.

## 6. Set-and-forget shows only active queues

Finished queues (canceled/expired/failed/confirmed/blocked) lingered forever,
contradicting the "0 ACTIVE" badge. Filtered out; section hides entirely when
empty. Commit `eab7f79`. Same pattern applies to any status list: **finished
items drop off; the badge and the list must never disagree.**

## 7. Multi-wallet SIWE 429 — root cause and fix (commit b19958a)

Failure shape: all N wallets authenticate OK initially, then ALL fail
`OpenSea SIWE authentication failed with HTTP status 429` during prepare, each
retrying at a FIXED interval (8 × 3 s) that never outlasts OpenSea's window →
"no wallet remains eligible".

Two-part fix in `engine/osnm-z`:

- `retry_delay()` exponential: `interval << min(attempt_hint,5)` capped at 16×;
  per-client transient-failure counter reset on success.
- Wallet authentications staggered 400 ms × manifest_index so a burst of N
  reads as spread-out traffic, not abuse.

Verified end-to-end: rebuilt engine minted 2/2 wallets through OpenSea SIWE +
on-chain confirm (blocks 45343964/65).

## 8. Funding gate: reserve vs mint price (updated 8/25 late)

Rehearse mode does NOT bypass funding checks — setup runs before the approval
prompt. The check per wallet is:

```
required = gas_limit × tx_count × maxFee × bump^(attempts-1) + stage_mint_price
```

Emad ruled (standing instruction): RH chain gas is effectively free; keep the
gas reserve near **0.0001** for free mints — he tops up "by instinct" only when
a paid mint demands it. Runner env tuned accordingly (`lib/server/multi-runner.ts`):
`GAS_LIMIT=250000`, `MAX_FEE_PER_GAS_GWEI=0.15`, `TRANSACTION_MAX_ATTEMPTS=2`
→ reserve ≈ **0.000084**/wallet. Note maxFee must stay ABOVE the chain's
observed base-fee ceiling (~0.145 gwei that night) or txs underprice and stall.

Critical distinction discovered after tuning: the Farting Unicorn run STILL
failed at the new reserve because its public sale gained a **0.0005 ETH mint
price** (it was free when the wallets were funded). Decompose one wallet:
`required − reserve = implied mint price`; an exact round remainder means the
sale is paid now — no env tuning fixes that, wallets need price+gas or skip.
Gotcha: live verification mints spend gas FROM THE SAME registry wallets and
can push them below the gate — check balances before claiming a fix works.

## 9. Engine prompt order (drives EngineProtocol replies)

Multi-mint prompt sequence: Mint target → (stage auto-select) → Setup funding
(top-up/skip/quit) → Approve [y/N]. The approval prompt comes AFTER funding,
so protocol replays that answer `n` for rehearse only when funding passes.
When hand-driving the binary via stdin, feed answers in that order.

## 10. Live-spend consent during verification (hard rule reinforced)

Reproducing engine fixes by piping `y` into a real run minted 2 live NFTs
(gas spent from the same registry wallets being tested) before the second
attempt was blocked as needing consent. Before any direct engine run: check
stage `active` vs `upcoming`, use unfunded wallets so funding checks stop the
run pre-broadcast, and treat any run reaching "Submitting transaction" as live
spend needing Emad's explicit OK. If tokens DID land, say exactly which wallet
received them and the cost — don't bury it.

## Ops notes

- `.next` wiped between sessions → launchd loop-crashed with "Could not find a
  production build"; fix is `npm run build` then
  `launchctl kickstart -k gui/$(id -u)/com.patelai.rh-mint-room`.
- After `npm run build`, give the kickstart a beat — kicking immediately raced
  the build output once and the server 500'd on a missing route chunk
  ("Cannot find module .next/server/app/api/rarity/route.js"); a second clean
  `kickstart -k` after `sleep` fixed it. If a fresh deploy 404s/500s on routes,
  restart once before debugging code.
- Logs: `.runtime/logs/launchd.{out,err}.log`.
- FAB 4200 queue entry canceled per user ("fab is dead"); collection contract
  0xef08…d758 resolves under slug farting-unicorn-nft-698920750 whose actual
  contract is 0xa6c63298f04401fc0414aefb33997089bc0e568e — pass the CONTRACT,
  not a made-up address, or resolve fails with "OpenSea collection was not
  found".

## 11. Direct-contract minting shipped (commit 8a90105, same session)

Full detail in `references/multi-mint-engine-protocol.md` §J. Summary: for
non-OpenSea collections use DirectMintPanel ("Mint direct contract" on Command
Center) → Read contract → dry run → LIVE. Price is discovered by SIMULATING
the mint, never by trusting getters; Doge Brokers' real price proved to be
0.0001 ETH EXACTLY via a value ladder (0.00005 revert / 0.00009 revert /
0.0001 PASS / 0.0002 revert — strict equality rejects overpays). An earlier
"0.01/mint" claim came from decoding InsufficientValue(uint256,uint256) revert
words in the wrong order — always bisect actual passing eth_call values from a
funded address instead of trusting one decoded word pair.

Test gotchas added with it: vitest here has no `globals`, so component tests
must call `cleanup()` in afterEach or renders stack up and TestingLibrary
reports duplicate buttons; and check button-label collisions across sibling
panels (DirectMintPanel's inspect button became "Read contract" because
CommandCenter already owned "Inspect collection"). Suite after: 772/772 across
84 files. Live dry-run verified 10/10 wallets; no live broadcast yet through
this path.
