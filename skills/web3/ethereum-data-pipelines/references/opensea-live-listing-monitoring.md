# Live listing monitoring with an OpenSea API key (RH chain)

The skill's "known RH Chain gap" — no reachable floor/orderbook — is solved once you
have a valid OpenSea V2 API key. The working path is the **events feed**, not the
orders endpoint.

## Endpoint shapes (verified 2026-08-18 on BUNKER: Genesis Artifacts)

- **WORKING — live listings with traits + price:**
  `GET https://api.opensea.io/api/v2/events/collection/{slug}?chain=robinhood&event_type=listing&limit=N`
  with header `X-API-KEY: <key>`.
  Returns `asset_events[]`, each with:
  - `order_hash` (dedupe key for "already alerted")
  - `order_type: "listing"`
  - `payment.quantity` (wei; `symbol: "ETH"`) → price = quantity / 1e18
  - `asset.identifier` (tokenId), `asset.name`, `asset.traits[]` (full trait list —
    filter `trait_type == "Rarity"` / any custom trait)
  - `maker` (seller), `asset.contract`
  - `asset.opensea_url` / build link: `https://opensea.io/assets/robinhood/{contract}/{tokenId}`

- **DOES NOT WORK — generic orders endpoint returns 405 even with a valid key:**
  `GET /api/v2/orders/robinhood/seaport/listings?collection_slug=...` → `405 Method Not Allowed`.
  `/api/v2/orders/robinhood/seaport/v1/listings` → 404. Don't burn time on the generic
  orders shape; the events feed is the verified RH monitor primitive.

## Exact active-book endpoints on Ethereum (verified 2026-08-27)

Do not generalize the generic orders-path failure into “OpenSea has no readable active book.” On Ethereum, the collection-specific routes work with an API key:

- `GET /api/v2/listings/collection/{slug}/all?limit=100` — cursor-paginated active listings, with `status`, `price.current`, maker in `protocol_data.parameters.offerer`, and token ID in `asset.identifier`.
- `GET /api/v2/offers/collection/{slug}?limit=100` — active collection offers.
- `GET /api/v2/offers/collection/{slug}/all?limit=100` — cursor-paginated active item, trait, and collection offers.

For exact order-book depth, use these active routes rather than filtering historical listing events by expiry. Events remain appropriate for arrival velocity and alert dedupe. Coverage is chain-specific: the successful Ethereum routes do not supersede the RH events-feed recipe until independently live-probed on RH. See `references/opensea-market-microstructure-analysis.md`.

## Key facts that made it work

- **The API key is required** — events feed returns `401 Missing an API Key` without
  `X-API-KEY` on RH chain (keyless coverage is name/image only, as the main skill says).
- Key is a 32-hex-char string, tied to the maker's OpenSea account. Store at
  `~/.hermes/secrets/opensea_key` (chmod 600), read via urllib with
  `User-Agent: Mozilla/5.0` + `X-API-KEY` headers.
- Each listing event includes `asset.traits` inline — no separate metadata call needed
  to know rarity/family.

## Monitor design that worked

- Poll every ~2 min, `event_type=listing`, filter `Rarity == "Epic"`, keep a bounded
  `seen_orders` set keyed on `order_hash` so a listing alerts once.
- Alert when price is a DEEP discount below the rarity-specific floor (do NOT alert
  on anything at/below the floor — see threshold lesson below).
- Silent when nothing qualifies; only emit the alert + OpenSea link when triggered.
- Reference implementation: `~/.hermes/cron/output/bunker_monitor_state.json` state +
  `~/Projects/bunker-snipe/monitor.py`.

## Pitfalls (learned the hard way 2026-08-18)

- **Shallow newest-N grab MISSES cheap listings — sweep, don't sample.** Fetching only
  the N most-recent events (`limit=50` once, or even a `--last 200` seed pass) means a
  low-priced "snipe" listing that ages out of that window (or lands between 2-min
  polls) is INVISIBLE — exactly the one you want to catch. Root cause of missing a
  0.001 ETH floor-dump that the user expected an alert for. FIX: sweep by `next`-cursor
  pagination every run (~20 pages ≈ 1000 events) and dedupe with the persisted
  `seen_orders` set. Sweeping wide every run is safe because the dedupe set stops
  re-alerts. Prime `seen_orders` from the wide sweep's first run so historical batch
  doesn't all fire at once.

- **`after` + `next` cursor = HTTP 400.** Adding `after=<ISO-8601 UTC>` alongside the
  `next` cursor makes the events endpoint return **400 Bad Request**. Use plain
  next-cursor pagination only and rely on the `seen_orders` set (or your own
  `last_run_ts`) for incremental logic — don't gate by timestamp server-side.

- **Alert on DEEP discounts only, or you spam the user.** Alerting on anything priced
  at/below the trait floor fires on ALL the at-floor noise (e.g. dozens of 0.0034–0.0038
  listings) and the user rightly complains "you spammed me." They want only genuine
  floor-dump snipes ("snipe if someone lists for 0.001 like that"). Set the threshold
  well under the trait floor (e.g. `ALERT_UNDER = floor * ~0.5`, ~47%+ off). On IRC the
  alert must carry an explicit `@nick` mention so it actually tags the user.
