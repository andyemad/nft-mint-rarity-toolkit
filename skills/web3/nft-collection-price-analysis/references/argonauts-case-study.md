# Argonauts Case Study — 2026-08-27

This is a dated example of the workflow, not a source of current market data.

## Identity

- OpenSea slug: `argonauts`
- Ethereum contract: `0x387c41b0b2f1128de44db1bcf8baad085f26392c`
- Artist: Alpha Centauri Kid
- Snapshot: 2026-08-27 21:41 UTC

## Market findings

- Floor: 0.1969998 ETH
- Best credible non-crossed bid: 0.185 ETH
- Active listings: 1,163 / 9,024 = 12.9%
- 24h: 532.813 ETH across 1,872 marketplace sales
- 2,500-sale tape: 716 buyers, 808 sellers, 323 wallets on both sides
- 56.32% of sampled purchases involved wallets that also sold in the sample
- 44.3% of sampled items traded in multi-item transactions
- Zero direct same-wallet sales, so the correct label was speculative churn rather than confirmed wash trading

Regime sequence:

1. 0.32–0.38 launch expansion
2. 0.375 local median peak
3. Distribution through 0.30 → 0.27 → 0.25 → 0.23 → 0.20
4. Capitulation: 226 sales/30m at 0.1715 median
5. Reflex rebound to roughly 0.1945–0.197 on lower volume

This established 0.17–0.18 as demand support, 0.156–0.162 as hard observed support, and 0.203–0.216 then 0.23–0.25 as immediate resistance.

## Order-book findings

- Only 6 credible collection bids totaling 1.104 ETH at or above 0.18
- 48 asks within 10% of floor
- 107 asks within 25% of floor
- 545 total listing makers; largest full-book maker only 1.9%
- Thin immediate asks could enable a squeeze, but credible bids could not absorb a broad liquidation

## Contract and supply findings

- Hard maximum: 10,000 ERC-721s, IDs 0–9999
- Token 0 is an on-chain website; 9,999 artwork cards
- 7,208 paid sale at exactly 0.12 ETH — fully minted
- 620 owner reserve — fully minted
- 2,171 signed free claims — 1,195 claimed, 976 unclaimed
- 976 free-claim overhang = 9.76% of final supply / 10.82% of then-current minted supply
- No burns
- Artist held 413 / 4.58%; top ten held 15.44%
- No ERC-2981 royalty; marketplace reported only its required 1% platform fee
- Standard unrestricted ERC-721 transfers
- Trait table and sale pool frozen, but owner could replace renderer/site and change signers/claim state
- Owner could technically convert remaining claim IDs into reserve inventory

## Special economic feature

Each NFT carried one physical print right while metadata showed `Print: Unclaimed`. The 30 cheapest listings sampled were all unclaimed. The workflow therefore treated claimed and unclaimed tokens as economically different assets.

## Forecast example

The prediction was conditional rather than deterministic:

- 6h: 50% 0.175–0.215; 27% 0.215–0.260; 23% 0.145–0.175
- 24h: 43% 0.16–0.22; 27% 0.22–0.30; 30% 0.11–0.16
- 7d: 40% 0.08–0.16; 32% 0.16–0.25; 18% 0.25–0.40; 10% below 0.08

Bullish invalidation required sustained floor above 0.216 and acceptance above 0.23. Repeated sales below 0.16 confirmed deeper unwind.

## Lessons

- Legitimate artist does not guarantee an attractive entry.
- Launch liquidity can coexist with poor holder quality and short-lived churn.
- A price rebound on declining transaction volume is not a confirmed reversal.
- Exact claim/reserve classification materially changes supply-risk analysis.
- Live executable bids matter more than headline offer counts.
- Fees must come from the actual collection/marketplace, not generic assumptions.
- A one-time analysis is not a watcher, and no live action should be implied unless verified.
