# OpenSea v2 no-key collection enrichment + indexer feed pitfalls (verified 2026-08-14)

How the mint-market-dashboard worker turned raw contract addresses into real collection
names + thumbnails with zero API keys, plus two bounded-store bugs found while wiring it.

## OpenSea v2 endpoint matrix (no API key)

| Endpoint | Status | Returns |
|---|---|---|
| `GET /api/v2/chain/robinhood/contract/{addr}` | **200 keyless** | `{ name, collection: "<slug>", contract_standard }` |
| `GET /api/v2/collections/{slug}` | **200 keyless** | `{ image_url, banner_image_url, name, ... }` |
| `GET /api/v2/chain/ethereum/contract/{addr}` | **401** `Missing an API Key` | — (key required for ETH) |
| `GET /api/v2/collections/casestudy-suites` (any slug) | 200 keyless | full collection object |
| `GET /api/v1/asset_contract/{addr}` | **410 permanently removed** | `{"errors":["The v1 API has been permanently removed..."]}` |

Consequences:
- **Robinhood-chain collections resolve name+image fully keyless** via the two-step
  contract → slug → collection. This is the cheap win for RH-first dashboards.
- Ethereum contract resolution needs an OpenSea API key; the slug endpoint does NOT
  help because you need the contract endpoint (key-gated) to learn the slug. Without
  a key, ETH collections keep the short-address fallback — say so honestly.
- The old "OpenSea REST API 401s without a key — don't build on it" rule is **wrong
  for the Robinhood chain**; correct it to "ETH contract endpoint is key-gated; RH
  contract + slug endpoints are keyless; v1 is dead."

## Instant API key for agents (when you DO want ETH names)

Docs: https://docs.opensea.io/reference/api-keys#instant-api-key-for-agents

- `POST https://api.opensea.io/api/v2/auth/keys` — no body, no signup, no wallet.
  Returns `{ api_key, name: "agent_free_…", expires_at, rate_limits: { read: "600/h",
  write: "30/h" } }`. Send it as `X-API-KEY` on all v2 requests.
- Free agent keys **expire after 7 days** — treat as a rotating secret, not a durable
  credential. Durable path: full key at https://opensea.io/settings/developer (needs a
  verified email; anonymous emails rejected).
- The instant pool is SHARED and rate-limited: `429 {"errors":["Maximum 2 keys per
  day."]}` means the pool is exhausted — retry the next UTC day, or use the developer
  portal. Do not loop-retry; it will not clear within minutes.
- Worker integration: read `OPEN_SEA_API_KEY` from bindings (optional secret); when
  set, add `X-API-KEY` and let Ethereum resolve through the SAME v2 contract → slug →
  collection flow as Robinhood. Wire the header before the key exists so the key is a
  drop-in, not a code change.

## No OpenSea market stats for Robinhood chain (verified 2026-08-14)

`GET /api/v2/chain/robinhood/collection/{slug}/stats` and
`/events?event_type=sale` both 404. OpenSea covers RH only at the **identity** level
(name/image/slug). MintGo-style Market columns (volume, change %, sales) for RH CANNOT
be sourced from OpenSea — derive them on-chain from marketplace sale events
(transfer/order-filled logs), and use OpenSea stats only where the API proves coverage
(Ethereum collections).

## OpenSea links: use the real slug, never slugify the display name

User-visible links must use the collection's REAL slug from the contract endpoint
(`collection: "onchain-cats-816755841"`), not a slugification of the display name
("Onchain Cats" → `onchain-cats` 404s). Build order:
- slug known → `https://opensea.io/collection/{slug}` (verified 200)
- ETH/no-slug → `https://opensea.io/contract/{chain}/{address}` — 308-redirects to
  the collection page (verified 200, e.g. → `/collection/casestudy-suites`)

## Enrichment pipeline (Cloudflare Worker + D1, cache-first)

- Migration: `collection_meta(chain_id, address, name, image_url, slug, resolved_at, PK(chain_id,address))`.
- Route `GET /collections?r=0x…,0x…&e=0x…,0x…` (comma-separated per chain):
  1. `SELECT` cache for all requested addresses (lowercased).
  2. Resolve only unknowns via OpenSea, **cap ~40 per call** (concurrency 3) so the
     worker stays inside the 30s wall-clock; unresolved leftovers retry on the next
     poll (frontend refetches every ~30s → converges in a couple of minutes).
  3. `UPSERT` results including nulls — a 404/no-listing cached as `name=NULL` so it
     is not re-fetched every call; it will only retry after a TTL/refresh.
- Frontend: collect unique collection addresses from stats + mints per chain, call
  `/collections`, merge into a map keyed by lowercased address; render `name ?? shortAddress`
  and `imageUrl ?? pixel-icon/avatar fallback`. Progressive — rows upgrade as metadata lands.

## Bounded-store bugs (learned the hard way)

1. **Per-chain bounded feed wipes other chains.** A `commitRecentFeed`-style
   `DELETE FROM mint_facts` + insert-top-N run once per chain, sequentially, means
   the LAST chain processed deletes every other chain's feed rows (Ethereum ran last
   and the "latest mints" feed showed only ~26 ETH mints; Robinhood vanished). Fix:
   scope the DELETE by `chain_id` so each chain keeps its own bounded window.
2. **Cross-chain "latest" must order by `observed_at`, not `block_number`.**
   Block numbers are incomparable across chains (Robinhood ~36.4M vs Ethereum ~25.7M),
   so a block-number sort always surfaces the numerically-higher chain.
3. **Mint "count" must count events, not summed quantity.** Aggregating
   `mintCount += fact.quantity` lets one ERC1155 mega-batch (e.g. 964,803,852) appear
   as absurd "+964M" momentum. For momentum/trending, `mintCount += 1` per mint fact
   (event semantics); reserve quantity sums for a supply-style metric if you have a
   column for it. After changing aggregation semantics, **clear the aggregate tables
   once** (`DELETE FROM minute_bucket_minters; DELETE FROM minute_buckets;`) so the
   data rebuilds uniformly — mixing old-sum rows with new-event rows corrupts totals.

## When enrichment sources are blocked: no-key fallback stack (verified 2026-08-14)

Blockscout (`robinhoodchain.blockscout.com`) returns **429 on EVERY endpoint from a
Cloudflare Worker** — datacenter egress is WAF/rate-blocked. Browser UA + Referer
headers do not help; the same endpoints return 200 from a home IP/node. Do not build
worker-side enrichment on Blockscout; verify explorer access from the actual runtime
egress, not from your laptop.

No-key fallback sources that DO work from the worker:
- **totalSupply** — `eth_call { to: addr, data: "0x18160ddd" }` (totalSupply()) on the
  chain RPC. Reliable for ERC-721; ERC-1155/non-standard contracts may revert → null
  → show minted-only.
- **holders ≈ all-time unique minters** — `COUNT(DISTINCT minter)` over your own
  aggregate minters table (NO time window). For fresh collections this matches
  Blockscout's `token_holders_count` exactly (verified: fuwacousin 222 both ways).
- **created ≈ earliest observed minute** — `MIN(minute_start)` of your own buckets.
  This is "first mint seen by us", NOT true deploy time; for a newly-ingesting
  indexer it under-reports age (e.g. "50m" vs true 17h). Accept the drift or label it.
- **creator** — no cheap keyless source when the explorer is blocked (deployer needs
  creation-tx metadata). Render a dash; do not fake it.

Detail-card propagation pattern (a card of dashes reads as "data doesn't propagate"):
populate MINT LIVE (minted from window stats, total from `eth_call` supply → progress
bar), HOLDERS (all-time minters), LATEST (max observedAt from the live feed), CREATED
(first-seen minute). Cache with a TTL (e.g. 3600s) and serve-stale-while-refreshing so
stale copies render while refresh runs. After a schema change that ADDS columns, clear
the cache once (`DELETE FROM collection_meta`) or cached rows keep pre-column nulls
for a full TTL — this bit us after adding enrichment columns.

## Next.js favicon gotcha caught during the same work

App Router `favicon` convention is **`.ico`-only** (`src/app/favicon.png` is silently
ignored; rename to `src/app/icon.png`), and a leftover default `favicon.ico` wins over
`icon.png` — delete it. Static brand assets belong in `public/`, not `src/app/`.
