# the control room floor + listings feed (added 2026-08-22)

## What exists

- `lib/server/opensea-listings.ts` — the reusable module:
  - `resolveContractSlug(contract)` → OpenSea slug via `/api/v2/chain/robinhood/contract/<ca>` (`.collection` field). Listings endpoints are slug-keyed ONLY; a raw CA 404s on `/listings/collection/<ca>/...` with "Collection ... not found or inactive".
  - `fetchBestListings(slug, maxPages=60)` — pages `/api/v2/listings/collection/<slug>/all?limit=50&next=...`, reduces to cheapest-per-token (`Map<tokenId, wei>`), returns `{best, floorWei, listedCount, partial}`.
  - `bestPricesFromListings(rows)` — pure reducer, unit-testable. Reads `offer[0].identifierOrCriteria` + `consideration[0].startAmount`.
  - `fetchCollectionStats(slug)` — `/collections/<slug>` totals (floor/volume/supply/owners) as fallback when no listings exist.
- `app/api/floor/route.ts` — loopback-guarded endpoint combining the above.
- `app/api/rarity-gallery/route.ts` — listings merge:
  - Fresh scan path: after ranking + image merge, resolve slug, fetch listings, set `token.price`, persist `{slug, listedCount, floor}` in ScanState.
  - Cached path: `&listings=1` triggers a cheap listings-only refresh on a cached scan (ranks/images untouched), rewrites ranked.json.
  - PITFALL: two token arrays exist in that route — `tokensFinal` (built after image merge; prices attach HERE) and nothing else usable. Earlier edits mistakenly targeted a pre-image array and broke compile.

## Verified numbers

- the test collection (0x1e64…c9f8): 87 listing rows → 75 unique tokens listed, floor 0.000188 ETH. Both stored keys work for listings (`~/.hermes/secrets/opensea_key`, len 32; the launchd plist key also valid).
- the rarity-test collection (0x512f…d55c): 535 listed of 5000; cheapest at-floor: #3174 (rank 550), #1857 (rank 1423), #486 (rank 1533), #2483 (rank 1540), #4284 (rank 2253) — all at 0.000094.
- the test collection best-listings endpoint paginates (>100 rows); /best returned exactly 100 with next cursor.

## API quirks learned live

0. **OpenSea contract endpoint response shape:** `/api/v2/chain/robinhood/contract/<ca>` returns TOP-LEVEL `{address, chain, collection, contract_standard, name}` — there is NO `nft_contract` wrapper. A resolver reading `data.nft_contract?.name` silently returns null for every collection (this broke the /rarity saved-scans switcher names until fixed; correct read is `data.name ?? data.collection`). — bare urllib gets 403 Forbidden with a VALID key; adding `'user-agent': 'Mozilla/5.0...'` fixes it instantly. curl works without UA.
2. **`/best` vs `/all`:** `/best?limit=100` returns each token's cheapest order but appears to cap ~100 rows and pagination is unreliable; `/all` pages cleanly through the whole book. For full coverage use `/all` + own per-token min reduction (that's what `fetchBestListings` does). Note: earlier session notes said "sum consideration" for true buyer cost — for RANKING/sniping purposes `consideration[0]` (seller price) is the right comparison number; fees are constant-ish on top.
3. **Slug resolution is required and cheap** (~200ms), cache it in ScanState (`slug` field) so cached-scan refreshes don't re-resolve.
4. Rate limiting: no 429s observed paging 2 pages of 50; the module still retries 429/502/503 with 1.2s backoff ×3.

## UI surface (/rarity page)

- Header line gains `· floor ◇ X · N listed` when status=ranked.
- Cards show `◇ price` badge bottom-right; gold background = price ≤ floor (at-floor deal flag), dark otherwise.
- "Refresh listings" button (ranked state only) calls the API with `listings=1&page=0`.
- Detail sheet shows "Listed at ◇ X · floor ◇ Y" when the token has a price.
- CSS: `.priceBadge` added to RarityGallery.module.css; gold text color via `[style*="fbbf24"]` attribute selector hack.

## Verification recipe (rerun after changes)

```
curl -s "http://127.0.0.1:3000/api/floor?collection=os:testcollection"
# expect {"slug":"testcollection","floor":"0.000188","listedCount":75,...}
curl -s "http://127.0.0.1:3000/api/rarity-gallery?collection=0x512faa1354c8d634cd0e78e6ec5ba1d9fe19d55c&page=0&maxRank=24&listings=1"
# expect slug raritytest-888, floor 0.000094, some tokens with price
python3 - <<'EOF'
import json
d=json.load(open('.runtime/rarity/0x512faa1354c8d634cd0e78e6ec5ba1d9fe19d55c/ranked.json'))
print(d['slug'], d['floor'], d['listedCount'], sum(1 for t in d['tokens'] if t.get('price')))
EOF
```
Then `npm run check` (must exit 0 — as of this session it does again; the old wallets-page lint error was fixed by wrapping the initial refresh in setTimeout) and restart via launchctl kickstart.

**Verify the restart actually picked up the new build** — don't trust the 200:
- If you kickstart DURING a build, the log fills with `Could not find a production build in the '.next' directory` and an old next-server keeps serving. Check `.next/BUILD_ID` mtime vs the server process start (`ps -p <pid> -o lstart=`); process must be NEWER than the build.
- Confirm a UI change landed by grepping the served HTML for a new-feature string (e.g. `curl -s http://127.0.0.1:3000/rarity | grep 'Refresh listings'`). Note the /rarity page SSRs its initial empty state — controls like Refresh listings only appear after a collection scan, so grep for them in a fetched payload instead (`&listings=1` response containing `floor`) when the marker is conditional.

## Saved-scans switcher

- **UPDATED 2026-08-22 (the user directive — supersedes the paragraph below):**
  every collection ever scanned now persists to `.runtime/rarity/collections.json`
  (`{lowercaseCA: name|null}`), written by a fire-and-forget registry block in
  the gallery route at scan time. The saved endpoint unions that registry with
  legacy per-CA ranked dirs, so PRE-REVEAL collections appear in the switcher
  too. Pre-reveal scans also return live listings (cheapest-first token cards,
  floor/listedCount in payload) instead of an empty tokens array.
  Old behavior (kept for context): the endpoint listed only dirs with completed
  ranked.json, so pre-reveal collections were absent until reveal.
- Names resolve live from OpenSea (`name ?? collection`, see quirk 0); null name falls back to short-address label in the UI. **UPDATED 2026-08-22 (evening):** the gallery route itself now guarantees a name on EVERY response — after resolving the input it fills name from collections.json first, then `resolveOpenSeaName` (OpenSea contract endpoint), and writes newly resolved names back into the registry. Previously a pasted raw CA returned `name: null` because only slug-input scans resolved names; the header/switcher then showed wrong or stale labels.
- The switcher select's value is bound to `collection?.address`; picking an entry calls fetchPage(address, 0) which serves from the memory→disk scan cache. **CASE BUG FIXED 2026-08-22 (evening):** the API echoed back `getAddress()`-CHECKSUMMED addresses while saved options are lowercase, so the bound value matched no `<option>` and the dropdown label never changed when switching collections — silent, zero console errors. Fix: page.tsx lowercases `data.collection.address` before setState (`setCollection({address: data.collection.address.toLowerCase(), ...})`). General rule: normalize collection addresses to lowercase at every API↔UI boundary in the control room; whenever "the select doesn't update", diff case between bound value and option values first.
- Verified live after both fixes: `?collection=0x512f…d55c` (previously nameless) returns `collection:{name:"the rarity-test collection"}`; npm run check green; launchctl kickstart picked up new build.

## Pre-reveal UX (the user directive)

- "If I put a collection into this page, it needs to propagate no matter what" — scanning a pre-reveal collection must (a) register it in collections.json immediately and (b) still show live listings: cheapest-first token cards with placeholder tiles ("pre-reveal" text instead of image), price badges, floor + listedCount in the header, Refresh listings + Re-check reveal buttons. Empty-state pre-reveal responses are a design failure, not a graceful degradation.
- Pre-reveal cards carry `rank: 0` / empty traits; the UI branches on `rank > 0` for rank badge vs "listed" tag. Keep that branch intact when editing card markup.
- Verified: the test collection pre-reveal → 75 listed @ 0.000188 floor; the test collection → 341 listed @ 0.01644.

## Publish outcome (2026-08-22 evening)

Both repos went public, then **flipped back to PRIVATE the same evening** after
the user's friend cloned them ("my friend cloned them already so you can put it
back to private"). Publish → share → re-privatize is a normal cycle here:
- Clones survive privatization — only future pulls stop.
- Flip back: `gh repo edit <user>/<repo> --visibility private --accept-visibility-change-consequences` (same required flag as going public).
- If he wants the friend to keep receiving updates, offer collaborator invites.

Both repos are now PRIVATE:
- `github.com/andyemad/mint-control-room` — osnm-z engine VENDORED into the tree (submodule pointer removed via `git rm --cached` + rsync from a fresh clone of zunmax/osnm-z, excluding `target/` [2.1GB Rust build cache] and `.git`; local ~200 lines of submodule modifications captured that were never pushed upstream; upstream MIT LICENSE kept in-tree + README attribution). README with real setup + MIT LICENSE added. The publish commit also carried smart-wallets endpoints and probe scripts (`scripts/buy.py`, `thepool_reveal_watch.py`, etc.).
- `github.com/andyemad/mint-market-dashboard` — flipped private→public→private with `gh repo edit --visibility ... --accept-visibility-change-consequences` (the consequences flag is required non-interactively). `/.hermes/` scratch dir gitignored and committed BEFORE flipping so untracked junk can never push.
- Final 64-hex secret scan on the pushed tree: all hits triaged clean — contract creation-code hex, keccak constants, EIP-7702 probe addresses, `0xaaaa…` test wallets. Triage by grepping context, not by pattern alone.
