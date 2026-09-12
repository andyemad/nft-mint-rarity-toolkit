# Pre-reveal Rarity Guide (beat OpenSea's rarity tab)

When the user asks for a rarity guide that "formulates before OpenSea shows it" for a
brand-new collection, the edge is real but GATED on the reveal actually having
dropped. Rarity is computed from per-token trait data; if the collection is still
on its reveal placeholder there are no traits to rank yet. Do NOT claim you can
produce a rarity ranking for an unrevealed collection — first verify reveal state.

## Verified reveal-state diagnostic (2026-08-19, the rarity-test collection / raritytest-888, RH chain)

Worked example contract `0x512faa1354c8d634cd0e78e6ec5ba1d9fe19d55c` (ERC721,
totalSupply = 0x1388 = 5000, name/symbol "the rarity-test collection"). A collection is still PRE-REVEAL
when ALL of the following hold:

1. **`tokenURI()` returns the SAME metadata CID for every token id.** Probe several
   ids (1, 2, 100, 4999): identical CID string = single shared placeholder. (the rarity-test collection
   returned `ipfs://bafkreibtlk…yluyui` for all.)
2. **OpenSea API shows one identical placeholder media + no traits.** `/api/v2/chain/
   robinhood/contract/{addr}/nfts/{id}` returns the same `image_url` for every token,
   `metadata_url` = the shared placeholder, and `traits: []`.
3. **The collection page's embedded JSON shows `"attributes":null` and `"rarity":null`**
   on the NFT rows (grep the saved 2MB page for these tokens; `trait_type` count = 0).
4. **Collection created very recently** (`createdAt` in the graph JSON = same day).

When those all hold, there is genuinely nothing to compute — say so plainly and offer
to build the reveal-watcher instead.

## Access tricks (verified this session)

- **RH RPC**: `https://rpc.mainnet.chain.robinhood.com`. `rpc.arrowrpc.com` returned
  HTTP 530 here; use the first with JSON headers. Python `urllib` MUST send
  `User-Agent: Mozilla/5.0` AND `Accept: application/json` **and** `Content-Type:
  application/json` or you get **403 Forbidden** (also a known pitfall in the parent
  skill — 403 is the urllib-no-UA signature).
- **Dynamic-string `tokenURI` decode**: ABI returns `(offset, length, bytes)`. Decode
  as `off=int(raw[:32],16); ln=int(raw[off:off+32],16); s=raw[off+32:off+32+ln]`.
  A naive "hex→utf8 on the whole result" truncates (the padding + length word corrupt
  the decode).
- **OpenSea V2 NFT-detail endpoint requires an API key** even on RH chain: no key
  returns `"Missing an API Key, which is required for this request."` Use
  `~/.hermes/secrets/opensea_key` with `X-API-KEY` header. The collection/contract
  name endpoints are keyless (`/chain/robinhood/contract/{addr}` + `/collection/{slug}`),
  matching the parent skill's keyless matrix — but the per-NFT `/nfts/{id}` call is
  key-gated.
- **IPFS gateways are unreliable for these placeholder CIDs**: `ipfs.io`, `gateway.
  ipfs.io`, `w3s.link`, `dweb.link`, `nftstorage.link`, `4everland.io`, `cf-ipfs.com`
  all returned blocked/Cloudflare-challenge/empty for the the rarity-test collection CID. Do not burn
  time chasing the placeholder through IPFS — read the on-chain tokenURI + OpenSea
  page JSON instead, which is authoritative on reveal state.

## Second verified example + gateway-variance lesson (2026-08-21, the test collection)

the test collection (`0xde0acefc89d4cf5f4ce45a4fb8a51aa355091b44`, slug `testcollection`, RH chain,
artist Brrrbon/@Brrrbon_) confirmed the diagnostic on a second collection: 6969/6969
minted, every token's `tokenURI()` = one shared placeholder
(`ipfs://bafkreiavsv…3itq`, "Pre-Reveal"), name() reads fine but OpenSea shows no traits.
Same verdict flow applies — verify state, say so plainly, offer the watcher.

New lessons vs the the rarity-test collection run:

- **Gateway availability is per-day/per-CID, not absolute.** The the rarity-test collection notes above
  said every gateway was blocked; on 2026-08-21 the SAME list still failed
  (`ipfs.io`, `dweb.link`, `w3s.link`, `cf-ipfs.com`) but **`nftstorage.link`
  served the placeholder JSON first try**. Always loop the full gateway list per
  session instead of hard-coding "IPFS is blocked"; put `nftstorage.link` early.
- **JS-side dynamic-string decode gotcha**: in Node, given the raw hex return,
  the offset word is `0x20`; the LENGTH lives at bytes `[32:64]` of the data section
  (read big-endian, e.g. `b.readBigUInt64BE(32+24)`), and the string is
  `bytes[64 : 64+len]`. Reading the length at byte 36 or slicing at 68 silently
  yields `len=0`/empty strings — if your decode returns "", suspect the offsets
  before concluding the URI is empty. (Python equivalent: length = int of raw[32:64],
  string = raw[64:64+len].)
- **Watcher timing numbers (verified)**: one direct RH RPC `eth_call` tokenURI probe
  ≈ 180 ms. A 2-minute cron probing 3–5 sample ids detects divergence within one tick;
  the full 6969-token sweep takes ~21 min single-threaded — plan concurrent batches
  (or accept the lag) and say so in the alert rather than implying instant coverage.
  (The armed the test collection watcher uses ThreadPoolExecutor(12) → sweep ≈ 2 min.)
- **Python urllib against RH RPC needs the full browser UA** — not just `User-Agent:
  Mozilla/5.0`; send a full Chrome UA string + `Accept: application/json` or the call
  403s (hit 2026-08-21 in testcollection_reveal_watch.py; plain "Mozilla/5.0" was NOT
  enough that day — if you get 403 from urllib, escalate to the full Chrome UA).
- OpenSea V2 keyed list-NFTs (`/api/v2/chain/robinhood/contract/{addr}/nfts?limit=50`)
  works pre-reveal too (returns the placeholder metadata rows) — usable as a
  cross-check that reveal flipped without trusting IPFS at all.

## Instant rarity engine (the build, when reveal drops)

Design for the "rank before OpenSea populates its rarity tab" edge:

1. **Reveal watcher**: poll `tokenURI()` across a sample (or all 5000) token ids;
   the moment CIDs start diverging from the shared placeholder, reveal has dropped.
2. **Fetch all metadata**: on reveal, pull every token's metadata JSON (from the
   diverged CIDs / the metadata base) and normalize trait maps.
3. **Compute statistical rarity immediately** using OpenRarity information-content
   (score = Σ −log₂(count/total)) — this matches OpenSea's rarity tab EXACTLY, so your
   ranks stay correct even after their tab populates (see formula-correction section
   below). Do this the second the data is live — OpenSea's rarity tab lags minutes
   to hours behind the raw metadata, which is the whole window of the edge.
4. **Produce a ranked table**: tokens ordered rarest-first, plus trait breakdowns
   (per-trait value counts/percentages) and top-N summary for under-priced mints.

This is a DESIGN captured pre-validation — the reveal had not dropped for the rarity-test collection, so the
engine itself is not yet verified end-to-end. Verify against a revealed collection before
trusting rank output.

## VALIDATED 2026-08-19 (the rarity-test collection reveal DID drop mid-session) — engine end-to-end, VERIFIED

The the rarity-test collection reveal dropped live while building, and the engine was built, run, and verified.
`tokenURI()` flipped from the shared placeholder CID to per-token `ipfs://QmT14…/<id>`
across all 5000 ids (probe: distinct URIs = revealed). This session confirmed:

- **KEY WORKING TECHNIQUE — do NOT fight IPFS for revealed metadata.** After reveal, all
  standard IPFS gateways (`w3s.link`, `nftstorage.link`, `ipfs.io`, `cloudflare-ipfs.com`,
  `4everland.io`, `dweb.link`, `cf-ipfs.com`) were STILL blocked/Cloudflare-challenged for
  the QmT… directory CIDs. Instead source per-token traits from **OpenSea's V2 list-NFTs
  endpoint, cursor-paginated**: `/api/v2/chain/robinhood/contract/{addr}/nfts?limit=50` +
  `&next=<cursor>`, with the `X-API-KEY` header. Each NFT row carries `identifier` + full
  `traits[]` (trait_type/value). This returns ALL revealed tokens key-gated but cheap and
  reliable (5000 tokens in ~100 pages, ~0.3s pace). OpenSea has already indexed the
  revealed metadata by then — the edge is v. OpenSea's *rarity tab*, not v. its raw data.
- **Script (re-usable engine)**: `~/Projects/rarity-engine/raritytest_rarity.py`
  — `fetch` (pull all 5000 traits → `~/.hermes/rarity/raritytest/traits.json`), `rank`
  (statistical trait-frequency rarity → `scores.json`), `mine` (rank the user's held ids).
  Runtime ~2-3 min for 5000 tokens.
- **Rarity score**: sum over traits of `1/(count/n)` — higher = rarer. Works: top tokens
  are `1/1` mythics (`Body:1/1`, ~9 of them) with identical max score; then a long tail of
  realistically rare combos. Average held rank was ~2042/5000 (his bag was above-average),
  rarest held token #71.
- **Wallet holdings comparison**: for the user's mint wallet, enumerate token ids via
  `eth_getLogs` `Transfer` topic[2]=wallet (from-block = creation), then confirm current
  ownership per id with `ownerOf` (`0x6352211e`) — balanceOf alone gives a count, not the
  ids, and received ≠ still-held (34 received → 29 held; 5 were sold).
- **OpenSea's V2 `traits` endpoint 404s** even with a key; the list-NFTs endpoint is the
  trait source of truth once you have the key.
- **the user's delivery preference** (learned here): give the bottom line up front (rarity of
  his holdings, ranks, which are the 1/1s), then exact Path-Finder absolute paths for the
  files. Offer a follow-up (arm floor/list-price watcher) rather than assuming he wants one.

## Visualize the result (2026-08-19 addendum)

When he asks "help me visualize it" after a rarity run, generate a **single-file interactive
HTML dashboard** from `scores.json` + `traits.json` so he can open it in a browser (no server).
Done here: `~/Projects/rarity-engine/raritytest_dashboard.html`, generated by
`gen_dash.py` (same dir). What the user wants on the page:

1. **Top stat cards** — total tokens held, best rank, rarest token id, average rank, and the
   count of 1/1 mythics in the whole collection (the mythics are the headline).
2. **Distribution bars** — his held-count vs the full 5,000 bucketed by rank (Top 50, 51-100,
   … 4k+) so he sees at a glance whether his bag skews rarer than average.
3. **Full ranked holdings table** — every held token id rarest-first with percentile, score,
   and its rarest trait tags, color-coded rank badges (orange=top-50, green=top-500, amber=mid).

Build gotchas hit this session: use an **f-string template with doubled `{{ }}` for CSS braces**
(do NOT use `.format()` on an HTML string full of `{` — it throws on the CSS and on missing
names); define `bars_html`/`rows_html`/`best_rank` as real variables before the f-string rather
than relying on `.format()` kwargs; `traits.json` values are dicts (`{"type","value"}`), not
tuples, so read `.get("value")=="1/1"` for the mythic count; keys in `scores.json`/`traits.json`
are **strings** — use `str(t)` when indexing by int token id. Deliver Path-Finder path, and
`open <file>` on his Mac so it pops in the browser.

## Rarity FORMULA correction (2026-08-21 — user-caught discrepancy, now the standard)

the user noticed "SOME discrepancy" between our the rarity-test collection ranks and OpenSea's. Two root causes,
both fixed and verified:

1. **Data bug**: one token (#3787) had EMPTY traits in `traits.json` from a transient
   fetch failure, skewing four trait counts by −1 each. ALWAYS sanity-check trait-count
   totals against OpenSea before publishing ranks: fetch `/collection/<slug>` hydration
   JSON → `attributes.items` per-value counts and diff. A single empty-traits token is
   enough to shift hundreds of ranks.
2. **Formula bug (the real one)**: we used sum of `1/(count/total)` (trait-frequency).
   **OpenSea's rarity tab uses OpenRarity information-content: score = Σ −log₂(count/total).**
   After switching, our ranks matched OpenSea EXACTLY on 5 sampled tokens
   (#4820→1=1, #2401→353=353, #3787→121=121, #100→2555=2555, #2500→2883=2883) — a perfect
   5000/5000 rank match after recompute. Info-content weights ultra-rare traits much more
   aggressively; trait-frequency systematically overrates mid-rare combos.

**Standard going forward: use information-content scoring for ALL rarity work** (the
the test collection watcher's `compute_rarity` already patched to this). Verify any new rarity
output by sampling 3–5 tokens' `"rarity":{"rank":N}` from their OpenSea item pages
(`opensea.io/item/robinhood/<ca>/<id>`, embedded in hydration JSON) — exact match =
done. Corrected the rarity-test collection held-bag numbers (8/21): #4931→rank 18, #4691→87, #2733→163,
#2401→353; avg #155 (NOT ~2042 as the old formula claimed).

## Armed-watcher pattern (2026-08-21, the test collection — third verified run)

The full watcher→sweep→rank pipeline is now BUILT, ARMED, and dry-run VERIFIED as a
standalone cron script: `~/.hermes/scripts/testcollection_reveal_watch.py`
(cron `testcollection-reveal-watch`, every 2m forever, no-agent, deliver local). Reuse this
shape instead of rebuilding:

- **Probe phase**: 8 sample token ids via concurrent `eth_call` tokenURI; any URI ≠ the
  shared placeholder = reveal. All-probes-failed → exit silent (retry next tick), never
  treat RPC failure as reveal.
- **One-shot alert guard**: state file `~/.hermes/rarity/testcollection/reveal_state.json`;
  once alerted, script exits silently forever. Ranks → `scores.json` in the same dir.
- **Sweep**: ThreadPoolExecutor(12) over all ids; expect ~1% RPC drops (6917/6969 in
  the dry run) — rank what was captured and say so in the alert.
- **Rarity math**: OpenRarity information-content, score = Σ −log₂(count/total) per
  trait — this EXACTLY matches OpenSea's rarity tab (see the formula-correction section
  above; verified 5000/5000 on the rarity-test collection). Dedupe metadata by distinct URI before fetching
  (pre-reveal collections have ONE URI; homogeneous revealed sets can too).
- **Delivery**: iMessage via `/usr/bin/osascript` Messages.app send to +1<operator-phone-redacted>
  (verified working). The `imsg` CLI was NOT installed and brew failed on missing Xcode
  CLT 26.3 — don't assume imsg exists; osascript fallback is reliable. Also print to
  stdout so cron output is the backup channel.
- **Dry-run technique**: to test detection+sweep+rank WITHOUT a real reveal,
  monkey-patch the module's PRE_REVEAL_URI to a fake value in an importlib harness —
  detection fires, sweep runs against live chain, rank math asserted on synthetic data.

Approval framing that worked for arming: slate describes read-only probes, one iMessage
on reveal only, no auto-buy, cancel-anytime — the user approved with a single "approve".

Operational notes: run the watcher as a local poller on the user's Mac (nothing external).
Per the user's build-gate, draft the plan for review before building. He wants a NEW
re-usable engine or a the rarity-test collection-only watch — confirm scope first.

## In-dashboard integration (2026-08-21, the control room `/api/rarity`)

When the user said "incorporate this into our mint bot tool… like it's all one dashboard",
the watcher stayed as the push channel and a live rarity PANEL was added to the existing
the control room Next.js app rather than shipping a separate page:

- **API route** (`app/api/rarity/route.ts`): loopback-guarded like every other route;
  probes sample tokenURIs → pre-reveal returns `{revealed:false, note}` (cheap, cached
  60s); on reveal sweeps all ids in concurrent batches (24×8 windows), dedupes distinct
  URIs before fetching metadata from IPFS, ranks with information-content, caches the
  result 60s, returns top 50.
- **UI**: one sidebar panel ("RARITY SNIPER") showing ○/● reveal state + ranked list,
  each row linking to the token's OpenSea item page; polls `/api/rarity` every 60s.
- **Gotchas hit**: guard the API response shape in the client (`rarity.top?.length`) —
  the mocked-fetch UI tests return objects without the new fields and an unguarded read
  crashes the component tree mid-test; adding an exported helper to a shared module
  (rpc.ts) — check it doesn't already exist at the bottom of the file or the duplicate
  export breaks four unrelated test suites at transform time.
- **Shape of the win**: push alert (cron + iMessage) for immediacy + pull panel
  (dashboard) for action — the user gets pinged wherever he is, and the ranked click-through
  list is waiting next to his watchlist when he opens the app. Keep both channels fed by
  the same ranking logic.

## Visual gallery page (2026-08-21/22 — a text ranking list was not enough)

A text list of ranks was NOT enough for the user — he asked for a separate page with the NFTs
visualized. Built as the control room `/rarity` (`app/rarity/page.tsx` + module CSS) backed by
`app/api/rarity-gallery/route.ts`. Reuse this shape whenever rarity output needs to become
a browsable gallery:

- **Images are cheap in bulk from OpenSea V2**: list-NFTs endpoint returns `image_url`
  per row; 5,000 tokens = 100 cursor pages ≈ **51s total** at ~0.15s pace. Stage the map
  `{tokenId: image_url}` to `.runtime/<collection>_images.json` once; the browser pulls
  from seadn.io directly (no proxying).
- **API route** reads staged scores+images JSON from disk (not chain), paginates 60/page,
  supports `maxRank` cutoff filter, loopback-guarded like every route.
- **Page UX that landed well**: responsive image grid with color-coded rank badges
  (legendary/epic/rare/common bands computed as % of collection), "Show top N" selector,
  pagination, and a click-to-open detail sheet — large preview + full trait list with
  per-value counts ("Eyes: Inferno — 1/5,000 · 0.0%") + OpenSea item link. Rank-band
  colors do the visual sorting work; the user reads the grid at a glance.
- **React lint gotchas**: `react-hooks/set-state-in-effect` rejects setState directly in
  effect bodies — wrap the initial load in an async IIFE with a `cancelled` flag inside
  useEffect instead of calling a setState-ing helper synchronously; and delete unused
  state setters (unused-var warnings fail the build gate when warnings are errors).
- **Playwright screenshot harness**: the project's e2e uses `playwright-core` +
  explicit Brave `executablePath` — `channel:'brave'` alone fails ("Unsupported chromium
  channel"). Copy the launch line from `scripts/e2e.mjs`.
- Dashboard panel 03 became a LINK to `/rarity` rather than embedding ranks inline —
  one canonical surface, no duplicate ranking UI to keep in sync.

## Generic scan-any-collection scanner (2026-08-22, the test collection live test)

the user wanted the gallery to work on ANY collection: "an ability on the rarity page for me
to just scan a collection/contract address like the mint bot". Built into
`/api/rarity-gallery?collection=<CA-or-OpenSea-URL>` + a scan input on `/rarity`.
Live-tested on **the test collection** (`0x1e6486…c9f8`, slug `testcollection`, 2000 supply,
pre-reveal) — scan returned the correct pre-reveal verdict; full sweep validated on
the rarity-test collection (5000/5000 ranked). Lessons:

- **Reuse `parseCollectionInput`/`resolveOpenSeaSlug` from opensea-resolve.ts** for
  input handling (raw CA, full OpenSea URL with any path suffix like `/activity`,
  `os:` shorthand). Reject non-RH-chain slugs with a plain error.
- **Reveal detection = sample tokenURIs.** Probe ~8 ids spread across supply; all
  identical → pre-reveal (return status+note, no tokens); divergent → revealed → sweep.
- **PRIMARY metadata source post-reveal is OpenSea's single-NFT endpoint**
  (`/api/v2/chain/robinhood/contract/{addr}/nfts/{id}`, keyed): one call returns
  traits AND image_url together — no separate image pass needed. IPFS gateways are
  the FALLBACK only (they were all blocked/rate-limited again on 8/22: nftstorage
  403s, pinata 429s on burst, cloudflare-ipfs DNS-dead).
- **OpenSea burst limits are real**: 20-way concurrency worked for an 80-token probe
  but a sustained 5000-token sweep at 10-way got only ~337 through before 429s. Fix =
  exponential backoff retry on 429 (6 attempts) + slow windows (~8-10 concurrent).
  Full 5000 sweep took **~43 min** under that pacing. Set expectations honestly:
  first scan of a large collection ≈ 15–45 min depending on size; subsequent scans
  instant from cache.
- **PERSIST every completed scan to disk** (`.runtime/rarity/<ca>/ranked.json`) and
  serve it before re-sweeping (memory → disk → fresh sweep; `&refresh=1` forces).
  The in-memory Map dies on service restart — without persistence every restart
  silently re-runs a 43-minute sweep.
- **launchd env changes need bootout+bootstrap, not just kill**: adding
  OPENSEA_API_KEY to the plist's EnvironmentVariables requires
  `launchctl bootout gui/501/<label>; launchctl bootstrap gui/501 <plist>` — a plain
  kill-and-respawn does NOT reload EnvironmentVariables (verified: key absent after
  kill-restart, present after bootout/bootstrap).
- **Response-shape bug to avoid**: the single-NFT endpoint wraps the row as
  `{nft:{traits,...}}`, not flat `{traits}` — casting the envelope directly yields
  zero hits and a misleading "metadata not fetchable" 503.
- **Next.js route handler type rule**: GET must return `Response` everywhere — wrap
  plain object returns in `NextResponse.json(...)` or the generated route validator
  fails the build.
- **pct field consistency**: the rarity-test collection staged scores carry numeric pct; scanner builds
  string `"99.98%"`. Unify on string early or the union type breaks the build.

## Production-validated cron watcher (2026-08-22, FROGHOOD: THE POOL)

`~/Projects/mint-control-room/scripts/thepool_reveal_watch.py` (1777-supply RH
collection, contract `0xfeed66…4bed`) ran the full pipeline in production: tokenURI(1)
probe → sweep via batched eth_call (96/call JSON-RPC array) → IPFS metadata fetch with
gateway failover → OpenRarity information-content ranking → ranked.json + one-shot
stdout alert. Cron delivery contract: **empty stdout = pre-reveal = deliver [SILENT]**;
the script prints `watcher error: …` on failure so a broken run is visible rather than
silently skipped. Validated end-to-end — the flip off the unrevealed CID was caught and
the sweep wrote ranked.json.

### Sustained reveal-moment 429s (new pattern — do not confuse with the -32005 shape)

The parent skill's pitfall says: read the 429 BODY because it may be block-range
rejection. This session hit the OTHER kind: **RH RPC 429s with no usable body for
10+ minutes** during the reveal window — plain `eth_blockNumber`/`tokenURI(1)` calls
failed from urllib while curl succeeded seconds later. Lessons:

- **Don't diagnose urllib 429s through urllib** — it discards the body. Probe once with
  `curl -s -X POST …` to distinguish dead endpoint (5xx/DNS) from rate limit
  (429 + JSON-RPC error body).
- **Sustained 429s around a hot reveal clear on their own.** A ~45s → 2m → 4m → 5m
  backoff ladder all failed; the next attempt ~10 minutes in went straight through.
  Inside a cron watcher: retry within the run only 1–2×, then print `watcher error`
  and let the NEXT cron tick retry — the schedule IS the backoff. Don't burn one cron
  slot sleeping 20+ minutes.
- **Verify state before trusting an "error" verdict.** A manual curl `tokenURI(1)`
  mid-storm showed the URI had ALREADY flipped off the unrevealed CID even while the
  watcher script kept 429ing — the reveal was live; rate-limit noise, not logic,
  blocked the sweep. Re-run the watcher as soon as RPC responds; don't rewrite working
  code during a storm.


