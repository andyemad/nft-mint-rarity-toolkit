# Alert-signal false positives: "buying" ≠ "recently acquired" (paid vs free-mint)

Verified 2026-08-18 on WIF Outlaw RH (Robinhood, `0x51ea87b2acaea9a933e8a4abac8c3ece6e22236d`).

## The trap
A "group is buying X" alert that counts a roster member as a buyer off **recency of
acquisition** (e.g. `wallet_positions.last_acquired_at >= window`) will treat a token
**free-minted/airdropped to the member's wallet** as a real buy. A dev-fronted scanner can mint
free tokens to 2+ roster wallets and the alert fires "Funkari buying X" as if there were demand.

## Repro evidence (WIF Outlaw RH)
- 2,106 mints; **985/990 mint txs submitted by the dev's own wallet** (the creator address).
- Tokens spread across ~970 recipient wallets that **paid nothing on-chain**. `tx.value>0` only
  because the *submitter* (dev) paid gas+price.
- Contract balance 0; dev received ~1,228 ETH in internal txs (SeaDrop→dev recycle loop).
- ~5 secondary transfers, ~1 with value. No real organic market.

## The rule for any buyer-signal / alert builder
**Require non-zero consideration, not just recency.** An "acquired recently" position is not proof
of a buy unless the wallet paid for it. If the source already carries cost basis (e.g.
`wallet_positions.cost_native` / `cost_usd`), filter acquisitions to those with
`cost > 0` (or a dedicated paid-since flag) before they can drive a "buying" alert.

## PAID-mint false-positive — non-zero consideration is NOT sufficient (ApeRunners, 2026-08-19)
A `cost > 0` filter is necessary but NOT sufficient. A dev-fronted mint can be fully *paid*
and still manufacture the exact same fake "whale buying" signal:
- Collection: ApeRunners (`0x5ffb9fd30952bcbcfd9239a13fae769773575e9f`, RH), slug `aperunners`, floor ~0.0394 ETH, supply 2,115/2,222.
- **780 / 783 mint txs submitted by a SINGLE wallet** `0x1ba1782652fc51838d846139309722ed3a8afbd4`, spread across 771 recipient-wallets = manufactured breadth, not demand.
- Every mint tx carried value (~16.29 ETH total) — so a paid-only gate passes 100% — yet the "bayc buying (28/25)" / "funkari buying (2/2)" alerts were false: the dev minted into hundreds of wallets that also hold BAYC/Funkari roster members.
- Only 4 secondary transfers, all sold by that same dev wallet; zero wash self-trades; floor pumped $13→$50→$75 with no real counterparty liquidity. Copycat "Ape" brand riding BAYC hype.

**The additional gate: submitter (tx.from) concentration, not just recipient payment.** Count who
SUBMITS the mint txs. If a single `tx.from` submits a large majority of mints (>~50%) and fans
out to many recipient wallets, flag as dev-fronted regardless of paid status. Genuine organic
demand shows many independent submitters. With paid mints, fetch per-mint `eth_getTransactionByHash`
(value AND `from`) so submitter concentration is computable alongside cost. Only re-enable a
flagged collection once submitter concentration materially diversifies AND real secondary
counterparties (non-dev buyers/sellers) form.

Honesty caveat: some chains have genuinely-demanded **free** mints where "demand" is real but the
buyer roster is silent on cost. Don't drop all zero-cost acquisitions from the UI — keep surfacing
free-recipient activity but as its own **labeled** category, and never call free recipients
"buyers" in alert copy. Match the repo's own naming discipline ("holding" vs "buying"), because
the codebase's recurring bug class is "a partial measurement presented as the whole."

## Sufficient fix at the SOURCE: per-acquisition-source tracking (mint-paid/free vs secondary)
Verified 2026-08-24, live production in mint-field-guide (eCalm Suites) alpha-group alert.

The alert's count today is `wallet_positions.last_acquired_at`, which a member's **mint** and a
member's **secondary buy** BOTH update — so a free mint still reads as "buying" even after the
cost/paid filters above, because `last_acquired_at` is one MAX statistic that cannot say WHICH
source acquired. Fix = stop conflating at the storage layer.

- Add three NULLABLE per-position source timestamps (migration): `last_mint_paid_at`,
  `last_mint_free_at`, `last_secondary_at`. NULL (never) must not collide with 0 (a valid Unix
  second). Written by the wallet-ledger fold from the event kind: `mint` with `native>0|usd>0` →
  paid, `mint` with none → free, `buy` (a sale-event acquisition) → secondary.
- **Keep `last_acquired_at` as the TOTAL (MAX over all sources) and keep firing/threshold on it.**
  The alpha-group bar was CALIBRATED on the total; swapping the firing read to a per-source
  timestamp silently transfers a threshold between two different statistics (the exact trap the
  repo documents above `getAlphaGroupActivity`). The split is a REPORTING difference, never a
  replacement of the calibrating statistic.
- Source-aware headline (Emad's chosen format, both webhook and board must agree): show each
  non-empty bucket with the slug leading the FIRST part only. `funkari minting (2/2) ·
  buying on secondary (1/2)`; mint-only = `funkari minting (2/2)`; secondary-only =
  `funkari buying on secondary (3/2)`. Paid-vs-free is a sub-distinction OF the minting bucket →
  rides in the message body (`Minting: 1 paid · 1 free`), omitted when nothing was free.
- Cost-averaged positions CANNOT tell paid/free of a single mint (avg basis mixes a free mint with
  a later paid buy) — that's why the split must be recorded at EVENT time, not re-derived from the
  aggregate cost fields.

## Edge-trigger == source-aware count

New acquisitions after deploy populate source stamps going FORWARD; pre-existing `wallet_positions`
rows (written before the migration) show 0s until re-acquired — additive-by-design, not a bug to
chase. The full-idle split kicks in as the cron ingests new mints/sales.

## Alert edge-trigger rule review
Edge-triggered alerts (fire on below→at/above threshold, once per crossing, `complete` snapshot
guard so a failed fetch reads as missing data, not "everything dropped to zero") are the correct
shape — the defect above is in the *underlying signal* (recency vs payment), not the trigger logic.

## Cross-reference
Fixing the *analysis* side of a launch is `references/dev-fronted-mint-wash-trade-forensics.md`;
this file is about the *alert construction* side (a live signal wrongly presenting manufactured
holder growth as buying). Both live under `ethereum-data-pipelines`.
