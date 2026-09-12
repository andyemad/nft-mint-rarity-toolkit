# Keyless OpenSea collection-page intelligence

Read a live OpenSea collection's full commercial picture with ZERO API keys —
drop economics, floor/volume windows, holder count, mint progress, and the
actual artwork — straight from the collection page's embedded GraphQL
hydration JSON. Verified 2026-08-14 on `milady-pepe-547444867` (Robinhood chain).

## Why page HTML, not the REST API

- `https://api.opensea.io/api/v2/collections/<slug>` and
  `/api/v2/collections/<slug>/stats` return
  `{"errors":["Missing an API Key, which is required for this request."]}` —
  key-gated as of Aug 2026.
- The public page `https://opensea.io/collection/<slug>` is server-rendered
  with urql rehydrate blobs containing EVERYTHING (works with a plain browser
  UA curl, no key).

## Recipe

```bash
curl -s -L "https://opensea.io/collection/<slug>" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -o /tmp/col.html
```

Then in Python: the page has MULTIPLE `collectionBySlug` fragments — the first
is a partial (slug/contracts only). Pick the occurrence with the rich fields
(`name`, `drop`, `stats`, `address`). Extract:

- **Drop economics** (`drop`): `type` (`SEADROP_V1_ERC721` etc.), `maxSupply`,
  `totalSupply` (mint progress), `stages[]` each with `stageIndex`,
  `startTime`, `endTime`, `price` (native unit + usd), `activeDropStage`.
- **Stats** (`stats`): `uniqueItemCount`/`totalSupply`, `ownerCount`,
  `listedItemCount`, `floorPrice` (BestOrder), rolling `volume` for
  oneMinute/fiveMinute/fifteenMinute/oneHour/oneDay/sevenDays/thirtyDays.
- **Identity**: `name`, `description`, `address` (contract), `chain`,
  `twitterUsername`, `isVerified`, `imageUrl`, `externalUrl`.

Floor vs mint delta is immediate: floor $0.129 vs mint $0.094 → +37% over mint.

## Quick gross mint-revenue estimate

`totalSupply × activeDropStage.price` ≈ gross mint revenue to the dev, no
block scanning needed. Milady PePe: 1,593 × $0.0939 ≈ **$150** (a "made $200 in
mint fees" claim ≈ gross, not profit — some secondary buys push volume above
mint revenue; gas + OpenSea fees come off the top). For the full dev-earnings
analysis (royalties, fee splitter routing, per-stage binary search) use the
`mint-dev-earnings-analysis` workflow instead.

## Same-day launch traction read

A drop that mints 48% of supply in hours (1,593/3,333), 258 holders, 139
listed, with floor above mint = a hot meme launch. It also tells you the
winners were the first buyers in the volume window, not the dev — the dev's
gross is small; secondary momentum is where money moves.

## Artwork (seadn.io media) — AVIF gotcha

Preview/hero/logo URLs are `https://i2c.seadn.io/collection/<slug>/image_type_...`
(hero_desktop, hero_mobile, logo, preview_media). They often serve **AVIF**,
not PNG — `file` reports `ISO Media, AVIF Image`. On macOS convert with
`sips -s format png in.avif --out out.png`. Individual preview_media images
give you real token art to vision-check the collection's style and quality
(before downloading, confirm the URL returns bytes — one preview_media URL in
the test returned `Not Found`).

## Cloning assessment (when user asks "can we recreate this?")

Answer the capability question (yes/no) with the above facts, then flag the
two real gates:

1. **IP**: don't 1:1 clone a collection whose character is a copyrighted
   template (Pepe the Frog = Matt Furie; Milady art direction = Remilia).
   Recreate the STYLE with an original character + a different meme fusion.
2. **Distribution is the moat, not the art**: an anonymous clone with no
   existing channel makes ~$0. The reference collection's traction came from
   meme-IP pull + its Twitter channel. Cost/race framing: art + deploy is
   cheap and fast; buyer discovery is the expensive part.
