# OpenSea activity and small-cap NFT trade assessment

Use this workflow for live collection activity, especially low-priced Robinhood Chain NFTs.

## No-key OpenSea activity extraction

1. Fetch `https://opensea.io/collection/<slug>/activity` with redirects and a browser user agent.
2. Locate an embedded hydration fragment containing `"collectionActivity":{"items":`.
3. Start at the object immediately after `collectionActivity` and decode one balanced JSON object. Each item can include:
   - `eventTime`, `type`, `transactionHash`
   - item contract/token ID
   - buyer and seller addresses
   - `price.token.unit`, symbol, and USD estimate
   - `saleType`, marketplace, chain, and quantity
4. Deduplicate events by event `id`. A single marketplace transaction may contain many item-level sale events.
5. Treat query-string page results cautiously. OpenSea may return overlapping, repeated, or freshness-shifted hydration instead of stable historical pagination. Verify each page's first/last timestamps and event IDs before claiming a longer lookback.
6. Parse the separate rich `collectionBySlug` fragment for floor, supply, owner count, listed count, rolling volumes, floor change, mint stages, verification, and metadata-storage clues.

## Metrics that distinguish liquidity from sweep theater

For the sampled sales window report:
- item-level sales and distinct transaction count
- distinct buyers and sellers
- total and median price; min/max
- top-5 buyer and seller concentration
- bundle sizes per transaction
- elapsed time covered by the sample

Compare rolling volumes: 1m, 5m, 15m, 1h, and 24h. If nearly all lifetime or daily volume occurred in the last hour, call it a fresh momentum event rather than an established market. Large sale counts can be misleading when a few wallets sweep bundles.

## Cost and risk framing for this user

Emad is an experienced NFT trader who reports prior gains around 45 ETH. Judge current opportunities by net dollars, time, risk, and scalable liquidity—not percentage ROI alone. A triple-digit return that produces one or two dollars is economically negligible in Buford and should not be praised as a successful income result.

Separate:
- realized proceeds and profit, including known gas, failed fills, and approvals
- open inventory marked to a realistically executable bid/floor, not a headline listing
- missed upside after exit, which is opportunity cost rather than a realized loss

For tiny collections, check owner concentration, listing ratio, verification, metadata hosting, supply-description inconsistencies, original mint price versus floor, and whether early holders still have extreme profit cushions. Also check the creator's X handle via `https://api.fxtwitter.com/<handle>` (account age, follower count, verification, bio) — a multi-year doxxed creator with prior live collections lowers rug-risk but NOT post-mint price-compression risk. Recommend a position only when expected net dollars and exit depth justify the user's attention. If momentum is concentrated, prefer one-unit probes and predetermined exits over bundle sweeps or averaging down.