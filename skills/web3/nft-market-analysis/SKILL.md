---
name: nft-market-analysis
description: "Use when judging an NFT buy or predicting collection price."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [nft, market-analysis, price-action, orderbook, risk]
---

# NFT Market Analysis

Use for “is this collection a buy?”, launch/post-mint technical analysis, floor-price predictions, and entry/exit decisions. The goal is a fast, live, decision-grade answer—not a generic project summary.

## Operating rule for the user

When a live entry looks attractive, do two things in parallel:
1. Finish the assessment.
2. Dry-run one exact NFT and prepare the exact purchase-approval slate.

Never broadcast without approval. Conversely, do not stop at analysis while a time-sensitive entry disappears. If no entry qualifies, say why and do not fabricate urgency.

A one-time analysis is **not a watcher**. Explicitly state “snapshot only; no monitor was created” unless the authoritative scheduler/process state confirms a watcher exists. Never use wording like “next time I’ll tee it up” in a way that implies continuous monitoring.

## Live-source stack

Collect concurrently where possible:
- Marketplace collection metadata/stats, recent sales events, listings, offers, NFT traits/ranks.
- Verified contract source and read-only RPC calls.
- Explorer token-holder data and contract-creation data.
- Official project terms, mint/claim pages, snapshot/allocation pages.
- Artist history and primary social posts; separate organic catalysts from promotional coverage.

Timestamp every market snapshot. Deduplicate listings by token ID before measuring depth; multiple active orders for one token are not multiple sellable NFTs.

### Identity collisions

Never select a collection from its name alone. Old, disabled, migrated, and same-name collections can coexist. Trace the current official mint/site marketplace link, then require agreement among official site configuration, marketplace chain+contract metadata, and verified explorer source. Explicitly reject legacy candidates before analysis.

When collisions span NFT contracts, payment tokens, same-chain meme tokens, and an older cross-chain brand, build an identity matrix: exact contract, chain, marketplace slug, project-site contract, mint/payment-token contract, and social handle. Shared names or tickers are not affiliation evidence.

For JS mint sites, current contract and marketplace constants may appear in client chunks rather than rendered HTML. Use them only for discovery, then independently verify them.

## Fast assessment sequence

1. **Identity and structure**
   - Chain, contract, verified status, mint date/price, max and current supply.
   - Public allocation, claims, team/artist reserve, unminted overhang, claim deadline.
   - If claims/mints remain open, read supply and claim counters both before and after analysis; report the movement and never extrapolate a few minutes into a confident completion ETA.
2. **Price action**
   - Pull enough recent sales to cover launch or at least 24 hours.
   - Compute rolling 30m/1h/2h/4h/8h/12h/24h count, volume, median, p10/p25/p75.
   - Prefer medians to means; rare sales and bundles distort means.
3. **Order book**
   - Unique-token floor and cumulative asks at relevant levels.
   - For Seaport listings, calculate the buyer’s gross ask by summing every native/ERC-20 payment item in `consideration`; the first payment component can be only the seller’s net proceeds and will understate price by marketplace/creator fees.
   - Floor-maker concentration and whether makers match owner/editor/artist addresses.
   - Marketplace `ACTIVE` status is insufficient during fast launches: verify `ownerOf(tokenId) == offerer` throughout the lower book and remove stale-owner orders.
   - **ownerOf padding bug (bit me 2026-08-31):** `ownerOf` returns a 66-char `0x…` value zero-padded to 64 hex (24 leading zero bytes). Comparing it with `==` to the 42-char `offerer` string fails for EVERY listing → you'll wrongly flag the entire lower book stale (I got 50/50 "STALE" here). Always compare `owner[-40:] == offerer[-40:]` (`.lower()` both). A 3/60 genuine-stale ratio is normal in a hot launch; a 60/60 "all stale" result is a padding bug, not the market. Slice `[-40:]` rather than stripping `0x`/zeros.
   - **Batch-RPC failure must not become “stale.”** Some providers answer a JSON-RPC batch with one error object instead of a result array. Validate that the response is a list and that every requested ID has a non-empty `result`; missing/error results are **unknown**, never stale. If an entire lower-book batch is unknown or implausibly 100% stale, retry several cheapest tokens as singleton `eth_call`s. Publish a validated floor only after singleton or valid-batch owner matches; otherwise label it marketplace-reported/raw.
   - If owner validation is rate-limited, publish exact depth only through the last fully checked price band; label higher figures as raw marketplace depth.
   - Identify collection/trait criteria offers by Seaport item types 4/5; item types 2/3 are token-specific even when identifiers look ambiguous.
   - Normalize multi-quantity collection offers to a per-NFT bid using the NFT consideration’s original `startAmount`; do not divide by `remaining_quantity`.
   - Exclude token-specific offers from the collection bid. A null/zero identifier alone is not sufficient classification without checking the criteria item type.
   - Note thin-air squeeze zones and overhead inventory separately.
   - See `references/opensea-order-normalization.md` for executable parsing examples, owner validation, and the fast-launch publication refresh.
4. **Participation quality**
   - Unique buyers/sellers, top buyer/seller concentration, owner ratio, average tokens per owner.
   - Check direct self-sales, repeated buyer↔seller pairs, fast round-trip flips, and buyer/seller overlap.
   - High churn is not automatically wash trading; label it speculative churn unless stronger linkage exists.
5. **Holder concentration**
   - Top 1/5/10/50 share, artist/team holdings, vault/contract addresses, known whales.
   - If transfer logs and holder APIs are blocked and the minted range is moderate/sequential, batch `ownerOf(1…totalSupply)`, validate every RPC result, retry unknowns singly, and tally normalized final-20-byte addresses. RPC errors are unknown, never burns.
6. **Contract and metadata risk**
   - Proxy/upgradability, owner-only controls, frozen traits/pool, renderer mutability, transfer restrictions, reserve minting.
   - “Fully on-chain” does not mean immutable if an owner can replace the renderer.
7. **Fees and break-even**
   - Verify marketplace fee and ERC-2981/creator royalty live. Never assume 10% royalty or reuse a generic 11% friction rate.
   - On Seaport, sum every payment consideration item for buyer gross, then separate seller proceeds, platform fee, and creator fee by recipient. A royalty marked optional in collection metadata may still be present in the executable order; order consideration wins.
   - Break-even = acquisition cost ÷ (1 − verified seller fee rate), plus gas/bridging.
   - For ERC-20-denominated mints, calculate live token-denominated mint cost, direct-pair liquidity/slippage, floor versus mint cost after fees, sink/burn share, and how token price changes future NFT dilution. Treat it as a reflexive two-asset market.
8. **Trait-specific rights**
   - Check redemption/claim status, rarity rank, and special rights. A claimed physical item can create a separate market from an unclaimed token.
9. **Fee-token + yield-NFT hierarchy**
   - Never compare the token’s unit price with one NFT’s floor. Compute token total-supply valuation, burn-adjusted valuation, economic-float valuation after provably permanent lockers, and NFT floor-/bid-implied collection values. Identify which asset actually owns revenue or redemption rights and which asset merely pays fees or is burned.
   - Reconcile `totalSupply()` with dead-address and locker balances. A dashboard “market cap” may exclude burns, locks, or neither; reproduce the displayed number before calling it wrong.
   - Value present backing separately from cumulative deposits/distributions. Read the vault’s current balance and liabilities; do not treat historical payouts as assets still backing today’s floor.
   - Trace the full fee path. A vault can safely protect funds after deposit while upstream royalty/creator-tax collection and the promised split remain operator-dependent. Marketplace fee recipients, fee escrow, and the vault must be checked separately.
   - Translate redemption copy literally from code: identify the exact ERC-20/instrument transferred. “Redeemable in gold” may mean a tokenized ETF/stock token, not physical bullion or a direct legal claim on metal.
   - Compare public scarcity claims against inherited admin methods. A custom contract may say supply only falls while an inherited `setMaxSupply`, mint-stage control, or mutable base URI remains callable by a live owner.
   - Model reflexivity: activation/climb/reissue burns can drive a launch squeeze, but finite upgrade caps, rising fiat activation cost, and normalized trading volume can sharply reduce future sink and yield.
   - See `references/fee-token-yield-nft-valuation.md` for the Reserve worked case and reusable audit checklist.

## Reading launch charts

- Falling rolling medians plus rising sale count often mark liquidation/capitulation.
- Reconcile extreme raw sale events against marketplace aggregate sales and volume. If a huge event is absent from recognized volume, exclude it from floor statistics and label it an anomaly or wash-risk proxy—not a legitimate comp.
- A rebound on progressively lower sale count/volume is a relief bounce until resistance is reclaimed with renewed participation.
- Thin asks immediately above floor can squeeze quickly, but do not ignore the cumulative wall 10–50% higher.
- Free claims and zero-basis allocations are supply overhang even when the public mint sold out.
- Compare floor market cap and fully diluted floor market cap with mint proceeds and total traded volume.

## Prediction format

Give explicit support/resistance and mutually exclusive probability scenarios:
- Next 6 hours.
- Next 24 hours.
- Next 7 days.

Probabilities must sum to 100% per horizon. State what invalidates the base case. Prefer statements like “60% chance of revisiting 0.17 before 0.25” over false precision about one terminal price.

## Verdict format

Lead with one sentence: **buy / bid only / breakout only / avoid**, plus the exact level.
Then provide:
- Current floor and timestamp.
- Best entry and invalidation.
- Verified fee-adjusted break-even.
- Realistic exit target.
- Liquidity/overhang warning.
- Whether a dry-run approval slate was prepared.
- Whether monitoring exists (normally: no, snapshot only).

## Archive output for the user

When the user asks for the Argonauts `/chat/` format, deliver a fixed line-by-line research archive—not an editorial dashboard or a replacement for an existing report. Include:
- line numbers and readable section headings;
- copy-full-analysis control and raw `.txt` download;
- snapshot timestamp plus a prominent “not live” warning;
- explicit separation of source data, calculated metrics, interpretation, scenarios, and trade plan;
- source links and privacy scanning;
- desktop and 390px mobile QA.

If publishing externally is requested or clearly implied, finish and verify the local artifact first, then seek one deployment approval. Never expose credentials, local paths, wallet secrets, session metadata, or private chat identifiers.

## Post-entry and post-exit updates

When the user already owns the NFT, switch from entry analysis to executable-exit economics. Anchor to their exact cost basis and report gross mark-to-floor, fee-adjusted near-floor proceeds, and immediate best-bid proceeds separately. Recompute short rolling medians, listed-supply ratio, and remaining claim overhang. Do not defend an earlier call: state whether the entry zone still holds and which timing/risk assumption deteriorated. Give a direct no-average-down/reclaim/invalidation plan, but never list or accept an offer without approval.

When the user confirms they already exited, acknowledge whether the exit avoided the subsequent move using fresh data, then analyze the collection strictly as a **new re-entry decision**. Do not keep presenting open-position P&L, stops, listing suggestions, or approval slates tied to inventory they no longer own. Compare the live floor with the prior decision zone, identify what old support became resistance, and require either a patient bid with favorable risk/reward or a volume-backed reclaim before recommending re-entry.

## Mutable / evolving-trait collections (artist-controlled)

When the artist/owner can mutate traits (signalled by the artist's own social post framing the set as "performance art", "the art changes over time", or a live state-change tweet/meme comparing the *same token* in two states), treat the static rarity analysis as a **snapshot, not a truth**:
- Reject "common / rare" and "no bids ⇒ sell" as permanent conclusions — a plain token can be curated into rarity and vice versa. Downgrade rank-based advice; the thesis shifts from **scarcity** to **artist narrative + curation**.
- Confirm mutation is centralized: often a non-upgradeable contract whose tokenURI/metadata still points at an artist-controlled mutable source, or a linked mutable store. No decentralized value guarantee — it is a bet on the artist.
- Check whether the user's token's traits fall in the artist's likely-curation set (e.g. a specific prop/artifact the artist is mutating in posts). That token is the **exposed / lottery-ticket** position, not a floor hold.
- Post-entry: still give executable-exit economics (cost basis, fee-adjusted floor, best bid), but frame the hold decision as exposure to the artist rather than a safe floor hold. No averaging down; keep a mental stop.

## Verification

Before finalizing:
- Re-fetch floor/stats because launch markets move during research.
- Confirm the cheapest listing is active and owned by its maker.
- For an existing position, verify seller fees and compute net P&L at both floor and best bid; headline floor is not executable profit.
- If recommending immediate purchase, require a successful fulfillment `eth_call` dry run.
- Do not claim a watcher exists without reading scheduler/process state in the same turn.

## Worked references

- See `references/token-denominated-mints-and-sale-anomalies.md` for identity matrices, ERC-20 mint reflexivity, fee decomposition, holder reconstruction via `ownerOf`, and extreme-sale reconciliation.
- See `references/launch-collection-analysis.md` for the Argonauts worked example: OpenSea event windows, unique-token depth, Blockscout holders, Routescan verified source, allocation overhang, renderer mutability, and fee correction.
- See `references/opening-hour-collection-forensics.md` for identity-collision resolution, seller-owner floor validation, multi-quantity collection-offer normalization, supply-in-motion snapshots, and the line-numbered archive output pattern.
- See `references/post-entry-launch-risk.md` for cost-basis-aware post-entry TA, fee-adjusted floor versus executable bid, claim-overhang pressure, anxious-holder communication, and the Original Blokyz worked pattern.
