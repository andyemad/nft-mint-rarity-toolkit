# Collection + artist deep-dive playbook (proven 2026-08-22 on GOOFYZ)

Emad's recurring ask: "analyze this collection, and the associated twitter/artist.
use moni api credits on the artist." Full workflow, all verified live.

## Moni API (artist/KOL influence scoring)

- Key: `~/.hermes/secrets/moni_ai_api_key` (starts `moni_`). Free tier ~300 credits/mo, 1 RPS.
- Base is **NOT** moni.ai or api.monitic.com (both dead ends). Working endpoint:
  `GET https://api.discover.getmoni.io/api/v3/accounts/<handle>/info/full/`
  header: `Api-Key: <key>` (not Bearer).
- Response fields: `meta.accountAgeDays`, `smartEngagement.{smartsCount, moniScore,
  mentionsCount, smartMentionsCount}`, `smartProfile.smartTags/chains`.
- Read it as: MoniScore is /10000-ish scale; <500 = bottom-tier influence no matter
  the follower count. smartsCount = quality-weighted engagers. Empty tags = Moni has
  them unclassified = nobody. One full-info call per handle was enough (cheap).
- Find the handle from the collection first: OpenSea v2 `/collections/<slug>`
  → `.twitter_username` (keyless).

## Twitter/X profile facts without auth

`https://api.fxtwitter.com/<handle>` returns JSON: followers, following, tweets
count, media_count, bio, join date, website. The killer ratio: **tweets ÷ account
age days** — 111k tweets over ~4.4 years ≈ 70/day hyper-poster with tiny engagement
= spam-volume account, not an influencer. No timeline endpoint (only profile +
individual status by id).

## Vision-analyzing NFT art when vision_analyze 404s on the image

vision_analyze can fail with model-404 on direct URLs (especially .gif). Workaround
that worked: curl the file locally → PIL → if animated, paste 2-3 frames side-by-side
into one PNG → vision_analyze the LOCAL path (worked immediately). Frame extraction:

```python
im = Image.open(path)
frames = [seek(i); im.convert('RGB') for i in [0, mid, last]]
canvas = Image.new('RGB', (w*3, h)); paste each
canvas.save('/tmp/composite.png')
```

Also read dominant palette via `getcolors()` after resize(64,64) to characterize style cheaply.

## Identical-token collections: churn forensics (no traits exist)

When every tokenURI/image is identical (check: `/collections/<slug>/nfts?limit=50`
→ count unique image_url; metadata URI shared = pre-reveal OR deliberately uniform),
there is NO rarity play — the analysis flips to flow forensics via the events API
(`/api/v2/events/collection/<slug>?limit=200&event_type=sale`, keyed):

- **Turnover ratio** = sales in window ÷ total supply. 2797 sales vs 2655 supply in
  ~24h = entire collection rotated in a day → pure degen churn.
- **Price distribution shape**: bid-side cluster (0.0015–0.0021) far below floor ask
  (0.0028) = pump holding, bids will eat late bagholders.
- **Buyer concentration**: top buyer taking 24 tokens in hours + one wallet selling
  18 = accumulator→recycle flip pool. Count repeats among buyers AND sellers.
- Verdict template: real art hand vs slop (say which), churn numbers, whale-flipper
  evidence, artist influence verdict from Moni+ratio, actionable edge or none.

## Gotchas hit this session

- `~/.hermes/secrets/opensea_api_key` (95-char) is STALE — events/listings return
  `{"errors":["Invalid API key"]}` while the 32-char `opensea_key` works. If one key
  401s, try the other before assuming endpoint trouble.
- OpenSea activity route is `/api/v2/events/collection/<slug>` — there is no
  `/collection/<slug>/activity` (404).
- web_search/web_extract may be unconfigured (Firecrawl credits) — curl + fxtwitter +
  OpenSea API covers NFT research fully without them.
- Delegation note: subagent batches of 3 ran fine for parallel recon (on-chain /
  platform RE / ecosystem) — give each explicit file paths for already-fetched raw
  material so they don't re-fetch.
