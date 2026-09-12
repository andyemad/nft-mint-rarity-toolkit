# Dev-fronted mint & wash-trade forensics ("is this launch organic?")

Verified 2026-08-15 on Brokers Holders (Robinhood Chain, contract
`0x0a6299B78edE13092Bab1C03181B84DE9574507E`, dev `0x2e38cae576af…f95055`).
Use when asked to "analyze this collection's mint / look into the developer
wallet" or to judge whether a drop's traction is manufactured. Complements
`opensea-activity-and-small-cap-trade-assessment.md` (market-side tells); this
file is the DEV-side forensic chain.

## Answer shape (verdict first)

Organic vs manufactured launch, dev's actual take, the ring evidence, then the
plain-money read for Emad (net $ / time / risk — no percentage-ROI dressing).

## Recipe (no keys: OpenSea page + public RPC + Blockscout)

1. **Identity + stages** from the OpenSea page hydration JSON
   (`opensea-collection-page-intel.md`): contract, `owner.address` (= dev
   profile), `drop.stages[]` prices/times, supply, stats.
2. **Count mints**: `Transfer` from-zero `eth_getLogs`, chunked ≤900 blocks,
   from the deploy block (creation tx from Blockscout
   `/api/v2/addresses/<contract>`).
3. **Classify payment by ACTUAL tx value, not stage-time buckets.** Batch
   `eth_getTransactionByHash` over unique mint tx hashes. Stage times can
   predate the real mint window entirely (Brokers Holders: stages set for
   Aug 13–14, all minting happened Aug 15 04:38–05:36; every one of 715 mint
   txs paid exactly the final-stage 0.0039 ETH). tx value is ground truth;
   stage-time bucketing misclassifies whenever the windows don't overlap.
4. **Submitter concentration**: count `tx.from` across mint txs. Dev-submitted
   ≥ ~95% of mints, minting to hundreds of distinct recipients, = dev-fronted
   mint — recipients paid nothing on-chain; the "650 holders" are mint
   recipients of one operator.
5. **Recycle proof**: Blockscout `/api/v2/addresses/<dev>/internal-transactions`.
   SeaDrop (`0x00005ea00ac477b1030ce78506496e8c2de24bf5` on RH) → dev internal
   refunds concurrent with each mint = creator-payout flowing straight back to
   the wallet that fronted the ETH. Contract balance ~0 + this stream = the
   loop.
6. **Dev wallet age**: paginate `/api/v2/addresses/<dev>/transactions` to the
   end via `next_page_params`. If the wallet's FIRST-EVER tx is the mint, it's
   a purpose-built launch wallet.
7. **Wash-ring detection**: scan ALL Transfers (drop the from-zero topic),
   keep from!=0 = secondary. Counters: sellers, buyers, unique tx hashes.
   Ring tells: (a) same wallets appear as both seller AND buyer; (b) many
   transfers packed into few txs (99 transfers in 14 txs = batched washes);
   (c) those same wallets sent ETH back to the dev after the mint. Also check
   sale-tx `tx.value` and WETH receipt flows for settlement.
8. **Earnings wrap-up**: `royaltyInfo(1, 1e18)` (zero = no secondary income),
   contract + dev `eth_getBalance`, `balanceOf(dev)` for withheld inventory.

## Free-mint deployer take (FABLINGS, 2026-08-18): when the mint value is 0

When the mint itself is genuinely **0-value free** (`mintFree()`, verified by
sampling mint txs — all `value=0`), the "what did the dev make" answer is
almost always **~$0 so far**, and the honest shape is different from a paid
dev-fronted mint:

- **Deployer wallet balance ≠ revenue.** FABLINGS deployer
  `0x717308a9312D61717E7ba0F82a31d0490f61a9cB` held 0.0233 ETH (~$44) — that's
  operating/gas float, not mint proceeds. Walk external txs for incoming value;
  it received ~0.000012 ETH (≈$0.02). Quoting the wallet balance as "made" is
  wrong.
- **Check BOTH sinks, not just the dev address.** A 10% `royaltyInfo` route
  pointed at a SEPARATE payout contract (`0x7d7d…c7`) — it had ~0.000054 ETH
  (~$0.10). If royalties accrued at all, they'd land there, not in the dev EO
  A. Read `royaltyInfo(1, 1e18)` for the receiver, then balance that address.
- **Free-mint "revenue" is deferred to the token/hype stage.** 37,664 mint
  transfers + 8,260 secondary transfers, yet dev take ≈ pennies. These
  projects monetize on a companion token launch or on later secondary
  royalties, not the free stage. Say that plainly rather than inventing a
  "profile margin."
- **Watch the digression trap:** a `Transfer`-topic log scan can return 0
  (truncated topic hash — see onchain-claim-reverse-engineering pitfalls) and
  waste an hour before you notice you're not actually counting anything;
  confirm 1+ mint receipt's topic before trusting a scan.

## Positive minter-legitimacy test (organic vs manufactured, 2026-08-24 Terminal Kids)

Use when the question is "are these minters legit?" rather than "did the dev front the
mint?". Both are dev-side forensics but the passing case gets its own recipe so a healthy
facade isn't misread as a red flag.

- **Near-parity submitter/recipient counts = organic.** Count unique mint-tx `from`
  (submitters) vs unique mint recipients (to in from-zero Transfers, drop the contract
  from the count). When they're within a few wallets of equal (Terminal Kids:
  **947 submitters ≈ 948 recipients**, 4,335 mints / 948 ≈ 4.5 per wallet) and no single
  submitter dominates (deployer submitted only 6), the mint was individual buyers
  self-minting — the exact inverse of the Brokers Holders red flag (704/715 from ONE
  wallet). Report this as the clean tell: "minters are legitimate, no fronting."
- **Real tx.value beats stage-time bucketing** (re-emphasized): a declining series of
  distinct paid values (0.010/0.008/0.006/0.004/0.002 ETH) is the signature of an organic
  falling-rock Dutch curve — decode mint-tx `value` per unique hash, not the stage
  schedule. 0.002 floor dominating + a few 0-value = normal decay to floor.
- **Gross mint revenue** = Σ distinct-value × count (Terminal Kids ≈ 6.50 ETH ≈ $12k).
- **Mint-to-contract reserved supply is the REAL flag in an otherwise-clean mint.** Sort
  recipient counts; if the CONTRACT ITSELF is the top "recipient" (Terminal Kids: 1,081
  tokens ≈ **25% of all mints** minted to its own address), that's withheld/reserved
  inventory held in the contract — potentially dev-controlled. Sum the contract-as-
  recipient share and flag it separately: "1 in 4 tokens may be dev-controlled" — do NOT
  let a clean minter set mask parked supply. This is the actionable caution even when
  every minter is legitimate.
- **Day-1 secondary churn is a faint signal, not a flood.** 144 transfers / 91 txs with a
  handful of both-buy-and-sell wallets and one packed 9-transfer tx is wash residue on a
  launch hours old — note the wallets but don't call the activity manufactured when it's
  small relative to the mint count. Revisit the both-sell-and-buy wallets if it grows.

Worked numbers (Terminal Kids, RH chain): 4,335 mint events / 948 recipients, deployer
`0xb3ff…0510` submitted 6/947, gross ≈ 6.50 ETH paid by 947 real submitters, 1,081 parked
in the contract (contract-as-recipient), 144 secondary transfers / 91 txs / 6 wash-ring
wallets. Verdict: minters legitimate; reserved supply is the caution.

## Brokers Holders worked numbers (2026-08-15)

- 1,723/1,777 minted (97%) in one 57-min window; unverified, no socials/description.
- 715 mint txs, **704 submitted by the dev wallet**; 656 unique recipients,
  none paid on-chain. Gross 6.7197 ETH ≈ $12.6k; after ~10% SeaDrop fee the
  dev's real take ≈ $11–12k. Royalties 0%.
- Secondary: 99 transfers in 14 txs among ~10 wallets that are BOTH sellers
  and buyers, and the same wallets that refunded the dev. OpenSea's quoted
  "1h volume" (0.49 ETH) is entirely that wash set.
- 0 OpenSea listings + one 0.01 WETH (~$18.8) top offer = bait offer, not demand.
- Verdict: manufactured launch; stay out.

## Pitfalls

- Blockscout `/api/v2/addresses/<a>/transactions?filter=to%7Cfrom` and
  `?sort=asc` → **HTTP 422**. Use the plain endpoint and paginate with
  `next_page_params` (walk all pages for oldest-tx age checks).
- Never conclude "minters paid nothing ⇒ free mint" from recipient-side
  evidence alone — track who SUBMITS and who receives internal refunds.
- OpenSea stats volume for RH can be 100% wash volume; verify the sale set
  on-chain before quoting any volume number.
- Dev-balance ≈ 0 proves nothing when SeaDrop routes payouts; the
  internal-tx stream is the evidence.
