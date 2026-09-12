# Cycle-Jackpot Economy (agent-gated) + local-EVM dry-run verification

Session 2026-08-20. Supersedes the earlier "winner-per-888 milestone, 50% pool"
jackpot design from `jackpot-mechanics-and-terms.md` for STILL UP. Emad reversed
the 8/19 handoff (24 supply, jackpot OUT) the same day a new design doc landed.

## CRITICAL WORKFLOW RULE (hit hard this session)

The repo carries a living design doc that **supersedes handoffs**: STILL UP's
current truth is `~/Projects/still-up-mint/docs/superpowers/specs/2026-08-20-still-up-economy-design.md`.
It explicitly declares it supersedes the economy sections of the `CLAUDE-TO-HERMES-...08-19...`
handoff. **When Emad reverses a plan, the newest spec is authoritative — read it
before building and before trusting any handoff's "locked" economics.** In this
session the stated task was literally "remove agentMint and build the economy the
new spec describes, it supersedes 8/19 which Emad reversed today." Building the
old 24-supply/no-jackpot design would have been a wasted, wrong deliverable.

## The cycle-jackpot economy (final locked shape)

Reference implementation: `~/Projects/still-up-mint/contract/StillUp.sol`
(compiled clean, 21,734 bytes / 60 ABI via `scripts/compile_check_sol.py`-style
py-solc-x). Verified 26/26 on a local EVM (`test/dryrun.py`).

| Param | Value |
|---|---|
| Supply | 8,880 = 10 cycles × 888 |
| Mint price | FLAT 0.0010 ETH (no curve, no per-wallet cap) |
| Pot share/cycle | 40% → 85%, escalating (stored as DATA, owner-tunable) |
| Cycle close | 888 mints OR 7-day timer, whichever first; permissionless |
| Draw | separate permissionless call, seeded by `blockhash(closeBlock+10)` |
| Mint gate | agent-gated EIP-712 permit (unchanged) |
| Fees split | pot slice escrowed in contract (Emad never custodies), remainder → `accruedCreator` |
| Full sellout | 5.55 ETH escrowed in pots = $11,100; creator keeps 3.33 ETH = $6,660 |

Design reasoning the spec made (don't re-litigate): escalating the PRICE was
modelled and rejected — any curve gentle enough for 8,880 steps leaves mints 1–450
nearly free (all realistic revenue) AND guts cycle-1's pot to ~$91 at exactly the
moment it must attract the first buyers. Escalating the POT SHARE gives the same
"getting bigger, get in now" pressure at only later-cycle cost. The no-per-wallet
cap is SAFE because a random draw makes farming unprofitable: for k entries at
price P with share s, net expectation = (s−1)·k·P, negative for every s<100% — no k
profits. This is why bots can't snipe it (a fixed "mint #888 wins" is trivially
snipeable with Emad's own `~/Projects/rh-mint-bot`).

Rate-limit/verify: the "a few hundred dollars" target is met at ~300 mints (~3%
sell-through) — 40% of ~$600 = $240 pot, $360 creator. Display the pot in ETH read
LIVE from chain, never hardcode a USD figure (ETH is the unit of account; USD is
decoration — sources disagreed wildly).

## Contract mechanics that matter (pitfalls)

- **Pot share is DATA, not logic.** Store `uint16[NUM_CYCLES] potShares` and read
  `potShares[cycle]` in the mint branch; add owner `setPotShare(cycle, bps)` gated
  to `mintCount==0` so it can't be retuned mid-cycle.
- **Timer fallback is mandatory** (spec §4.2): without it, at realistic low
  sell-through a cycle never fills, the count is never hit, and the page promises
  a jackpot the contract silently never pays — the exact rug-by-accident that
  shipped once before. `closeCycle(cycle)` is permissionless and requires
  `full || timedOut` on `cycle.openTime + 7 days`. Anyone can trigger it, so a
  stalled cycle still settles.
- **The draw must re-anchor on seed expiry**, never revert-forever and never treat
  zero as a valid seed (that makes winner selection deterministic/gameable).
  Pattern: `drawAnchor = closeBlock + 10`; in `draw()`: if `block.number <
  drawAnchor` revert "not ready"; if `blockhash(drawAnchor)==0` (the +10 window
  lapsed past 256 blocks) re-anchor `drawAnchor = block.number + 10`, emit
  `DrawReanchored`, and revert so a later re-call succeeds.
- **Cycle struct field ORDER is load-bearing in tests.** Adding a field (e.g.
  `openTime`) shifts the getter indexes. web3's public-struct getter FLATTENS a
  dynamic `address[]` member out of the tuple, so `cycles(0).call()` may not have
  a list where you expect. Prefer reading `winner` from the emitted
  `JackpotPaid` event, or from `c0[-1]`, over brittle fixed indexes.

## Local-EVM dry-run harness (proves the economy before deploy)

`~/Projects/still-up-mint/test/dryrun.py` — the fast, deterministic way to verify
a mint+jackpot contract without touching mainnet and without Foundry:

- `Web3(EthereumTesterProvider())` + `--with eth-tester --with py-evm`. **py-evm
  is required** — without it eth-tester silently falls back to MockBackend and
  `eth_estimateGas` throws MethodUnavailable (a silent-fail trap).
- **Raw Accounts (created with `Account.create()`) are NOT in the tester keystore**
  — `transact({"from": acct})` fails with "address must be a string". Build+sign+
  send manually with a `signed_call(acct, fnobj, value, gas)` helper (same
  `raw_transaction` + nonce/gasPrice/chainId pattern as a real mint). This is the
  difference between proving "ANYONE can close/draw" and failing to.
- **Time travel**: `w3.testing.timeTravel(ts)` then `w3.testing.mine(1)` to move
  the chain past a 7-day timer; loop `w3.testing.mine(1)` until `block_number`
  passes `drawAnchor`. Verify the "not ready yet" revert BEFORE mining past the
  anchor, then the successful draw AFTER.
- Read pot/draw state via `c.functions.cycles(0).call()` and assert pot==0 after
  draw, `drawn==True`, winner in minters set.
- Event filter in eth-tester: `create_filter(from_block="earliest")` (snake_case —
  `fromBlock` raises TypeError).
- Assert negative cases return `status==0` (eth-tester signals revert via status,
  not an exception) — a try/except-only detector reports every revert as pass.
