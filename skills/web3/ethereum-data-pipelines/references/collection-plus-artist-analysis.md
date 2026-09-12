# "Analyze this collection + the artist (use Moni credits)" recipe

Verified 2026-08-22 on GOOFYZ (`g00fyz`, RH chain, `0xfcf7…decc`). Use when
Emad drops an OpenSea collection URL and asks to analyze it AND its associated
Twitter/artist, explicitly authorizing Moni API credit spend. This is the
market+social combined pass; `nft-collection-call-due-diligence.md` covers the
narrative/claim-verification side.

## Sequence (each step verified this session)

1. **Collection identity**: `GET /api/v2/collections/{slug}` with header
   `x-api-key` works — returns name, description, contracts[] (address +
   chain), total_supply, twitter_username, discord_url, created_date.
   `twitter_username` here is the direct artist link (GOOFYZ → FilthyTrikksEth).
2. **Stats**: `GET /api/v2/collections/{slug}/stats` (same key) — volume/sales/
   num_owners/floor_price + 1d/7d/30d intervals. GOOFYZ: 2,797 sales vs 2,655
   supply in ~3 days = entire collection turned over; churn signature.
3. **Activity/events**: `/collection/{slug}/activity` is 404 — the working path
   is `GET /api/v2/events/collection/{slug}?limit=200&event_type=sale`
   (same key). Returns asset_events with payment.quantity (wei), buyer, seller,
   nft{}. From a 200-sale page compute: price distribution, top buyers (repeat
   accumulators), top sellers (dumpers), recency window.
4. **Artist via Moni** (credit spend pre-authorized by Emad's ask):
   `GET https://api.discover.getmoni.io/api/v3/accounts/<handle>/info/full/`,
   header `Api-Key`. Returns meta.accountAgeDays,
   smartEngagement{smartsCount, moniScore, mentionsCount, smartMentionsCount},
   smartProfile. Cost 8 points. Moni Score 435/10000 = bottom-tier influence;
   near-zero lifetime mentions despite follower count = reach is not real.
5. **Twitter profile without web tools**: `https://api.fxtwitter.com/<handle>`
   returns followers, tweets count, media count, joined date, bio, website.
   Hyper-volume tell: 111k tweets / 4.1k followers ≈ spam-poster cadence, not
   an engaged audience.
6. **Artwork inspection when vision fails on remote URL**: download locally
   first (seadn.io URLs work with curl); for GIFs extract representative frames
   side-by-side into one PNG via PIL and vision_analyze that local file.
   vision_analyze on the remote i2c.seadn.io gif URL failed repeatedly;
   the local-frame composite worked first try.

## Flip-pool verdict template

GOOFYZ pattern: identical tokens (one shared metadata URI + one GIF for all
2,655 — probe several tokenURIs before claiming any rarity angle), full-supply
turnover in days, two wallets buying 24 each within hours, floor ask above the
bid cluster. Verdict shape: credit the real drawing hand + name the textbook
degen rotation; play only as momentum-flip near bid, never hold; state plainly
"no rarity angle exists" when all tokens are identical.

## Gotchas

- Two OpenSea key files exist under ~/.hermes/secrets/: `opensea_api_key`
  (95 chars — INVALID for v2 events endpoints) and `opensea_key` (32 chars —
  WORKS). If one returns {"errors":["Invalid API key"]}, try the other file.
- Moni base host is api.discover.getmoni.io (NOT api.monitic.com or
  api.moni.ai); wrong hosts return misleading 404s or HTML.
