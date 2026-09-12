# OpenSea collection market-microstructure analysis

Validated 2026-08-27 on Ethereum collection `argonauts`. Use for read-only analysis requiring a large sales tape, exact active listing depth, offers, holder concentration, bundle effects, price regimes, and short-horizon scenarios.

## Authoritative source split

Use each OpenSea V2 surface for what it actually proves:

- Collection identity/config: `GET /api/v2/collections/{slug}`
- Aggregate floor/owners/volume/sales: `GET /api/v2/collections/{slug}/stats`
- Historical sales tape: `GET /api/v2/events/collection/{slug}?event_type=sale&limit=50`, cursor-paginated with `next`
- **Exact active listings:** `GET /api/v2/listings/collection/{slug}/all?limit=100`, cursor-paginated
- **Active collection offers:** `GET /api/v2/offers/collection/{slug}?limit=100`
- **All active item/trait/collection offers:** `GET /api/v2/offers/collection/{slug}/all?limit=100`, cursor-paginated

Send `X-API-KEY` and a browser-like User-Agent. The generic Seaport orders paths can return 405; do not infer that active-book access is unavailable. The collection-specific `/listings/.../all` and `/offers/...` routes are the correct read primitives.

## Listings: exact book, not event approximation

Historical listing events are useful for listing velocity, but filtering them by start/expiry does **not** prove an order remains live: cancellations and fills are not reconciled. For current depth, use the active-listings endpoint and require `status == ACTIVE`.

For each listing:

- Price: `price.current.value / 10**price.current.decimals`
- Maker: `protocol_data.parameters.offerer`
- Token: `asset.identifier`

Report:

- total active listings and listing/supply ratio
- floor and ask percentiles
- cumulative item and distinct-maker depth at floor +1%, +2%, +5%, +10%, +15%, +25%, +50%, +100%
- top-1/top-5 maker share inside each near-floor band

Floor-maker concentration should be computed from the **active** book. A recent-events sample can wildly overstate concentration when one maker rapidly relists or replaces orders.

## Offers: normalize quantity and screen crossed anomalies

Collection-offer `price.value` can be the total consideration for multiple units. Normalize:

`per_item_bid = price.value / 10**decimals / remaining_quantity`

Report cumulative units, makers, and total notional above selected per-item bid thresholds. Keep collection offers separate from item/trait offers; the latter often contain automated rarity bids and can be dominated by a few bots.

An OpenSea `ACTIVE` status does not prove current WETH balance/allowance or practical executability. If a collection bid is crossed far above the floor, flag it as anomalous and show both:

1. the literal active quote, and
2. the best credible non-crossed quote used for support/spread analysis.

Do not silently treat a crossed quote as a reliable floor bid.

## Sales-tape method

Pull at least 1,000 sales when available; 2,500 gives a stronger intraday sample. Deduplicate item-level events by a tuple including transaction, order hash, token ID, event timestamp, buyer, and seller. One order hash or transaction can legitimately cover several NFTs.

Compute:

- item sales, distinct transactions, elapsed coverage, volume
- median, mean, P05/P10/P25/P75/P90/P95, min/max
- rolling 1h/3h/6h/12h/24h windows
- distinct buyers/sellers and top-5 shares
- wallets appearing on both sides, plus their buy/sell item shares
- direct self-trades (`buyer == seller`) separately
- 30-minute medians/P10/P25/P75 for regime detection
- rounded price clusters for support/resistance

OpenSea aggregate interval counts and an independently cursor-paginated event sample can differ because snapshots move and aggregation semantics/lag differ. Label them separately rather than forcing reconciliation.

## Bundle effects

Group item-level sales by transaction hash:

- bundle transaction = transaction with more than one item-level sale event
- report bundle transaction share, bundle item share, maximum bundle size
- compare bundle-item median/mean against single-item median/mean

Large bundle-item share can inflate apparent activity even when buyer/seller concentration looks moderate. A small bundle discount suggests sweeps/batch exits near market; a large discount suggests distressed block liquidity.

## Holder reconstruction

For a new Ethereum ERC-721 collection, reconstruct current ownership from complete `Transfer` logs:

1. Query the contract from a block range that begins before deployment/mint.
2. Use 500-block chunks when provider result caps are uncertain.
3. Sort by block number, transaction index, and log index.
4. Decode only logs with exactly four topics.
5. Mint (`from == zero`) assigns the token to `to`; burn (`to == zero`) removes it; otherwise update token owner.
6. Reconcile token count and holder count to OpenSea supply/owners before trusting concentration metrics.

Report top-1/top-5/top-10/top-20 supply shares, Gini, max holding, and single-token holder count. Cross-reference large holders against collection owner/editor wallets from collection metadata; label that relationship without assuming malicious intent.

## Price regimes and probabilistic scenarios

Use 30-minute tape bins plus the live book to identify expansion, distribution, capitulation, rebound, and consolidation. Support should be grounded in repeated sales clusters and bid depth; resistance should combine prior high-volume shelves with cumulative ask depth.

For 6h/24h/7d scenarios:

- probabilities must sum to 100% at each horizon
- use ranges, not false-precision point forecasts
- state invalidation conditions (for example, sustained acceptance above resistance or repeated sales below support)
- widen ranges and increase uncertainty with horizon
- distinguish a reflex rebound from a confirmed trend reversal

Always state snapshot timestamps in UTC and do not buy, bid, list, or create alerts during a read-only analysis.