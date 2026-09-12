---
name: nft-collection-price-analysis
description: "Use when deciding if a live NFT collection is a buy."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [nft, market-analysis, price-action, contract-audit, opensea]
---

# NFT Collection Price Analysis

## Trigger

Use when Emad asks whether an NFT collection is a buy, requests technical analysis or price predictions, or shares a live marketplace collection link for evaluation.

This skill produces a source-grounded market-microstructure analysis, contract/supply audit, probabilistic forecast, and action-framed trade verdict. It does not buy, bid, list, post, or create a watcher without the required approval.

## Inputs

Minimum:

- Marketplace collection URL or slug.

Discover rather than ask when possible:

- Canonical collection slug.
- Chain and verified contract address.
- Official website and social account.
- Current marketplace/API credentials already configured locally.

Optional:

- Maximum entry price.
- Desired holding period: intraday flip, 1–7 day momentum, or long-term collection.
- Preferred wallet and spend cap.

Never print API keys, wallet keys, or secret-file contents.

## Output contract

Lead with a direct verdict: `BUY`, `WAIT`, `BID ONLY`, or `AVOID`, plus the exact entry condition.

Then report:

1. Timestamped live snapshot.
2. Price-action regime and support/resistance.
3. Ask depth and executable bid depth.
4. Holder/supply concentration and remaining mint/claim overhang.
5. Contract controls and metadata/royalty risks.
6. Organic demand versus flipping/wash proxies.
7. Artist/project fundamentals and catalysts.
8. Probabilistic 6h, 24h, and 7d scenarios whose probabilities sum to 100% at each horizon.
9. Trade plan: entry, invalidation, break-even, target, liquidity risk.
10. Exact sources.

Separate floor-price analysis from rare-item prices. Never let grail sales distort floor conclusions.

## Workflow

### 1. Resolve identity and sources

1. Read the user-provided marketplace URL first.
2. Resolve slug, chain, contract, collection owner/editors, verification status, official site, and official social handle.
3. Cross-check the contract address on at least one explorer or official project page.
4. Record a UTC timestamp for every live snapshot.
5. Label facts as live, historical, or inferred.

Preferred OpenSea V2 endpoints:

- `/collections/{slug}`
- `/collections/{slug}/stats`
- `/events/collection/{slug}?event_type=sale&limit=100`
- `/listings/collection/{slug}/best?limit=100`
- `/offers/collection/{slug}/all?limit=100`
- `/chain/{chain}/contract/{address}/nfts/{token_id}`

Use `X-API-KEY` from the configured secret file without echoing it.

### 2. Build the recent-sales tape

1. Cursor-page at least 1,000 item-level sales; target 2,500 for a fresh/high-volume launch.
2. Deduplicate by transaction, order/event identity, and token ID. Bundle events are item-level; do not collapse them into one sale when measuring items.
3. Record coverage start/end, distinct transactions, buyers, sellers, and tokens.
4. Calculate 30m bins and rolling 1h, 3h, 6h, 12h, and 24h metrics:
   - sale count and distinct transactions
   - volume
   - median and mean
   - P10/P25/P75/P90
   - unique buyers and sellers
5. Treat median and lower percentiles as the floor-relevant tape. Exclude rare/grail outliers from floor trend estimates.
6. Identify regime sequence: launch expansion, peak, distribution, capitulation, rebound, or base.
7. Compare rebound price with rebound volume. Rising price on sharply declining volume is usually a relief bounce, not confirmation.

### 3. Measure bundle and churn effects

Calculate:

- multi-item transactions as a share of transactions
- bundled items as a share of sold items
- largest bundle
- bundled versus single-item median
- direct self-sales
- buyer/seller wallet overlap
- share of purchases and sales involving two-sided wallets
- token round trips where a buyer resells within 24 hours
- repeated buyer/seller pairs

Interpret carefully:

- Zero direct self-sales does not prove clean volume.
- High two-sided participation indicates flipping or market-making, not automatically wash trading.
- Report evidence as `organic`, `speculative churn`, `wash-risk proxy`, or `confirmed wash`; do not overstate.

### 4. Pull the exact active ask book

1. Cursor-page all currently `ACTIVE` listings; do not substitute historical listing events.
2. Dedupe duplicate orders for the same token when measuring unique sellable inventory, while also reporting raw active orders when relevant.
3. Calculate:
   - listed supply percentage
   - floor
   - P10/P25/median/P75/P90 asks
   - asks within floor +1%, +2%, +5%, +10%, +15%, +25%, +50%, and +100%
   - maker count and top-maker/top-five concentration near floor and across the full book
4. Compare near-floor makers against collection owner/editors and known reserve wallets.
5. Flag a one-wallet floor stack. A distributed floor is healthier but can still be fragile.

### 5. Validate executable bids and offers

1. Separate collection bids from item and trait offers.
2. Exclude crossed or anomalous `ACTIVE` offers unless balance, allowance, and fillability are independently verified. Marketplace `ACTIVE` status alone is not proof of executable support.
3. Report:
   - best credible non-crossed collection bid
   - bid/floor spread
   - units, makers, and notional at key thresholds
4. Compare bid depth with near-floor asks and recent sales velocity.
5. A handful of bids can support individual exits but cannot absorb a broad liquidation.

### 6. Reconstruct holder and mint structure

Preferred hierarchy:

1. ERC-721 `Transfer` logs from deployment to tip.
2. Blockscout token-holder API.
3. Marketplace owner count as reconciliation, not sole proof.

From transfer logs derive:

- current minted supply and burns
- holders and single-token holders
- top 1/5/10/20/25/50 concentration
- Gini coefficient when practical
- mint recipients and current holder changes
- first/last mint timestamps

Identify creator, artist, editor, reserve, exchange/vault, and major external wallets. Distinguish initial minted allocation from current balance.

### 7. Audit the verified contract

Obtain verified source from RouteScan, Blockscout, Etherscan, Sourcify, or direct explorer APIs. Cross-check live bytecode/state.

Determine:

- proxy/upgradeability status
- hard maximum supply and token-ID range
- paid pool, free claims, owner reserve, and special/site tokens
- exact paid mint price and max per transaction
- current sale/claim state
- remaining mintable claims or reserves
- owner/admin powers
- whether reserve comments are actually enforced
- transfer restrictions, pause, blacklist, operator filter, tax, burn, or soulbound behavior
- ERC-2981 or other royalty implementation
- renderer/base URI/site mutability
- whether raw traits are frozen separately from presentation
- randomness mechanism and any fairness implications

Read comments as claims, not controls. Verify enforcement in code.

Critical supply arithmetic:

- Final artwork supply = paid pool + signed claim allocation + owner reserve.
- Remaining overhang = final claim allocation minus claimed count.
- State overhang as both percentage of final supply and current minted supply.
- If owner can reclassify unclaimed IDs as reserve, say so explicitly.

### 8. Inspect floor-item quality

Hydrate at least the 20–30 cheapest unique listings and collect:

- rarity rank/percentile
- meaningful traits
- redeemed/unredeemed physical or utility status
- owner and maker
- current listing price

For projects with physical redemption, a redeemed NFT and an unredeemed NFT are economically different assets. State whether the current floor still includes redemption rights.

Do not recommend a random floor token when a materially better rank or unredeemed asset is available within a few percent.

### 9. Research fundamentals and catalysts

Verify:

- artist/team track record and prior sales
- established collectors and public whale allocations
- reputable gallery/auction/marketplace history
- launch terms, roadmap/utility promises, and exact claim window
- current social amplification and engagement
- upcoming reveals, physical claims, free claims, unlocks, auctions, or announcements

Distinguish durable artist demand from one-day influencer attention. A legitimate artist can still have a bad entry price.

### 10. Compute economics correctly

Use the collection's actual fees, not a generic royalty assumption.

- Break-even sale price = `(entry + acquisition gas) / (1 - verified seller fee rate)`.
- If creator royalty is absent, do not invent one.
- State ETH and approximate USD using a timestamped ETH price.
- Include gas where meaningful.
- Compare floor-implied collection value and fully diluted floor value.

### 11. Build support, resistance, and forecasts

Support comes from observed trade clusters, credible bids, and capitulation lows—not round-number intuition alone.

Resistance comes from active ask depth, prior high-volume shelves, profitable-holder basis, and psychological levels.

For each horizon, give mutually exclusive scenarios summing to 100%:

- 6h: consolidation/retest, squeeze, renewed liquidation.
- 24h: base formation, recovery, mint-price breakdown.
- 7d: post-launch fade, stable secondary market, renewed catalyst, severe liquidity loss.

State explicit invalidation conditions, such as:

- Bullish: sustained floor above resistance plus renewed transaction volume and bid growth.
- Bearish: repeated sales below hard support plus expanding listings and shrinking bids.

Avoid false precision. Forecast the floor/range, not rare-item prices.

### 12. Convert analysis into action

Frame the recommendation around liquidity and risk/reward:

- `BUY`: attractive now; prepare one exact candidate.
- `BID ONLY`: good project, bad market-buy entry; name bid range.
- `WAIT`: require a specific breakout or stabilization condition.
- `AVOID`: contract, supply, legitimacy, or liquidity fails.

Emad dislikes illiquid NFT positions. Prefer liquid collections and fast, explicit exits.

If the entry is attractive during the assessment:

1. Immediately select one candidate rather than stopping at analysis.
2. Run the marketplace fulfillment dry-run/`eth_call` without broadcasting.
3. Report exact token, rank/traits, redemption status, cost, fees, gas estimate, and wallet balance.
4. Create one exact approval slate for that single purchase and stop for approval.
5. Never broadcast without approval.

If the entry is not attractive, do not create a purchase slate merely to appear proactive.

A one-time analysis is not a watcher. State explicitly whether any watcher exists. Creating a watcher that sends alerts requires its own approval.

## Parallel research pattern

For comprehensive requests, parallelize three read-only workstreams:

1. Market microstructure and forecasts.
2. Contract, allocations, holders, and admin controls.
3. Artist fundamentals, social catalysts, and sentiment.

Require each worker to return exact timestamps, URLs, methods, and uncertainty. Verify material claims yourself before reporting. A timed-out social worker does not invalidate independently verified market and contract results.

## Pitfalls

- OpenSea collection stats can lag the live listings tape.
- An API `ACTIVE` offer can be unfunded or unfillable.
- Item offers for grails are not collection-floor bids.
- Multiple listings may target the same token; dedupe unique inventory.
- Bundle sales can inflate item counts and distort average prices.
- A high round-trip rate is speculative churn, not automatically wash trading.
- `totalSupply()` may be absent on non-enumerable ERC-721 contracts; reconstruct from logs.
- Public RPCs may silently lack archive state. Reconcile deployment and mint timestamps before trusting historical `eth_getCode`.
- Explorer APIs can omit contract-forwarded mint requests; reconcile assignment events, exact-payment invariants, and final supply.
- “Fully on-chain” does not mean immutable if the owner can replace the renderer.
- Contract comments such as “never sold” are not enforcement.
- Free claims have zero purchase basis and are real sell-pressure overhang.
- Do not use a generic 10–11% royalty assumption; inspect actual royalty and platform fees.
- Do not claim a watcher, bid, dry run, or purchase exists unless verified from its authoritative source in the current turn.

## Verification

Before finalizing, verify:

- Slug, chain, and contract match across sources.
- Snapshot timestamps are explicit.
- Sales are deduplicated and coverage is stated.
- Active asks come from active-listing endpoints.
- Collection bids exclude anomalous/unfunded orders.
- Holder reconstruction reconciles to marketplace/explorer counts.
- Allocation arithmetic reaches the hard maximum exactly.
- Contract controls are supported by verified source or live calls.
- Fee/break-even math uses verified fees.
- Forecast probabilities total 100% per horizon.
- Verdict includes exact entry and invalidation conditions.
- Any recommended live purchase is dry-run verified and approval-gated.
