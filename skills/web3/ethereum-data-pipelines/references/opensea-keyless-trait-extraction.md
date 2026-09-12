# OpenSea keyless trait extraction (trait types, values, counts)

Goal: full trait breakdown for any OpenSea collection — trait categories, every
distinct value, per-value counts/percentages — WITHOUT an API key. Needed for
rarity assessment, trait-count studies, and mint-intelligence work.

## Dead ends (verified 2026-08-15)

- `GET /api/v2/collections/{slug}/traits` → 404 Not Found
- `GET /api/v2/chain/{chain}/contract/{addr}/traits` → 404 Not Found
- `GET /api/v2/chain/{chain}/contract/{addr}/nfts` → 401 "Missing an API Key"
- `GET /api/v1/collection/{slug}` → 410 "v1 API has been permanently removed"
- The collection page HTML (`/collection/{slug}`) does NOT contain trait data
  (client-rendered; only breadcrumb/brand ld+json).

## Working path: scrape the traits tab page

```
curl -s -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125.0 Safari/537.36" \
  "https://opensea.io/collection/{slug}/traits" -o traits.html
```

The page (~1.5 MB) embeds the GraphQL hydration JSON with two useful shapes:

### 1. Group listing — COMPLETE distinct value set per category

```
{"traitType":"Body","values":[{"__typename":"CollectionAttributeValue","value":"Hot Magenta"},...],"__typename":"CollectionAttribute"}
```

Regex: `\{"traitType":"([^"]+)","values":\[(.*?)\],"__typename":"CollectionAttribute"\}`
then pull every `"value":"..."` inside. This is the authoritative total of
distinct values per trait type.

### 2. Flat value counts — per-value count/percent (paginated)

```
{"traitType":"Eyes","traitValue":"Low Bar","count":379,"percent":0.00947,...,"__typename":"CollectionAttributeFlatValue"}
```

Regex: `\{"traitType":"([^"]+)","traitValue":"([^"]+)","count":(\d+),"percent":([\d.]+)`
Dedupe by `(traitType, traitValue)` — the page repeats blocks.

**Pagination trap:** flat values come paginated (`nextPageCursor` present) so the
first page shows only a SUBSET (e.g. 35 of 100 values). Use the group listing for
the complete distinct-value count; use flat values only for counts of values that
appear.

## Verified example: rh-machines (Robinhood Chain, 10,000 supply, 2026-08-15)

- 5 trait categories, 100 distinct values: Body 31, Eyes 42, Headwear 25,
  Background 1 (Acid Lime), Type 1 (1 of 1).
- Most common: Body Royal Purple 504, Eyes Low Bar 379, Headwear Halo 469.
- Rarest mainstream: Headwear Blueberries 37 (0.37%); Eyes Battou 16.
- 1-of-1 lives in the Type trait.

## Pitfall: the collection description prose lies

rh-machines' description claims "99 hand drawn traits across bodies, headwear and
screens" — actual parsed data is 100 values, there is NO "Screens" category (it's
Eyes), and the count is off by one. Never trust the description for trait stats;
always parse the page data and report the real numbers (and flag the mismatch
when the description is used for marketing claims).

## Cross-check with collection stats

`GET /api/v2/collections/{slug}/stats` works keyless for floor/volume/sales/owners
(verified 2026-08-15: rh-machines floor 0.037 ETH, 14,562 sales, 2,574 owners).
Useful context alongside the trait study.
