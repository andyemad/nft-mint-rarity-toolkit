# Session 2026-08-25 — Rarity trait filter + OS-primary rarity API fix

## 1. Gem-style trait filter panel at /rarity (shipped, live)

Emad pasted a screenshot of Gem's trait filter UI and asked for the same in
Mint Room. Pattern for "add filtering like this <screenshot>":

- `vision_analyze` the reference image FIRST; mirror its layout (collapsed
  accordion rows per trait type with a value-count on the right), don't invent
  an equivalent.
- Implementation (all client-side, no API change):
  - State: `traitFilters: Record<string, Set<string>>`,
    `expandedTraits: Set<string>`, `showTraitPanel: boolean`.
  - `traitIndex` useMemo builds type → [value, {count}] from loaded tokens,
    values sorted rarest-first.
  - Selection semantics: OR within a trait type, AND across types
    (`matchesTraitFilters`).
  - Panel: collapsible rows (▾ rotates), value buttons show
    `count · pct%`, active picks amber, header has Clear-all +
    active-count badge on the toggle button.
  - Composes with Snipe view: filter first, then floor-tier sort.
- CSS module additions: `.traitToggle .traitPanel .traitPanelHead
  .traitGroup .traitRow .traitName(.Active) .traitMeta .chevron(.Up)
  .traitValues .traitValue(.Active)`.
- LIMIT: filters only the LOADED page (60 tokens). Collection-wide filtering
  needs a server-side `traits=` param on `/api/rarity-gallery` — not built yet.

## 2. `/api/rarity` 503 "Reveal seen but metadata not fetchable" — two real bugs

Symptom looked like reveal lag; traits were already on OpenSea. Root causes:

1. `/api/rarity` fetched metadata ONLY via IPFS through `nftstorage.link`
   (dead gateway). Fix: OpenSea paged `/nfts?limit=200` as PRIMARY source,
   pinata gateway IPFS kept only as fallback for stragglers. Same shape as the
   gallery route's existing osPage loop.
2. `/api/rarity-gallery` read ONLY `process.env.OPENSEA_API_KEY` (never set)
   instead of falling back to `apiKey()` in `lib/server/opensea-listings.ts`
   (which reads `~/.hermes/secrets/opensea_key`). One-line fix:
   `process.env.OPENSEA_API_KEY ?? osApiKey()`.

Lesson: when a Mint Room route needs the OpenSea key, ALWAYS go through
`lib/server/opensea-listings.ts apiKey()` — never raw env or inline read.

## 3. Deploy mechanics gotchas (cost ~40 min)

- **Turbopack dev servers cache compiled routes**; `.next/server/.../route.js`
  stayed stale after edits. Mint Room runs under launchd `next start` (PROD) —
  edits require `npx next build` then
  `launchctl kickstart -k gui/$(id -u)/com.patelai.rh-mint-room`.
- **Never `rm -rf .next/server/app/api/<route>` while launchd is running** —
  I deleted the compiled route.js, causing MODULE_NOT_FOUND + "Internal Server
  Error" until rebuild.
- **Orphaned next-server processes squat on :3000** (respawned children with
  ppid 1). `lsof -nP -iTCP:3000 -sTCP:LISTEN` to find them; kill ALL
  next-server pids before testing, or you'll hit a stale server and conclude
  your fix didn't work. The launchd job is `com.patelai.rh-mint-room`
  (KeepAlive) — it respawns its own server; don't fight it with manual dev
  servers on the same port.
- Verify served code freshness by grepping the built chunk for new strings:
  `grep -rl 'new-marker' .next/static/chunks/`.

## 4. Trait panel v2 (later 8/25): sorting, Gem-style labels, smooth loading

User follow-ups on the same day — all three shipped:

1. **Sortable values**: `traitSort` state (`"rarity" | "count" | "az"`),
   dropdown in the panel head, applied inside the `traitIndex` useMemo
   (re-sorts per mode; rarity = count ascending).
2. **Gem-style labels**: header reads `TRAITS <active-count>` in letter-spaced
   caps (`.traitPanelTitle`); each expanded category shows an
   `ATTRIBUTE / COUNT / %` column head (`.traitValueHead`); every value row has
   a color-coded rarity badge matching Gem: orange ≤1%, purple ≤5%,
   blue ≤15%, neutral gray commons (`.rarityBadge{Rare,Epic,Uncommon,Common}`).
3. **Smooth loading on transient errors**: user hit "Contract did not report an
   ERC-721 totalSupply" once on a fresh Clay scan (worked on retry). Two-layer
   fix — server: `totalSupply()` retries 5× with growing backoff; client:
   `fetchPage` loops up to 3 attempts with a visible "Retrying — the collection
   contract is busy…" note instead of dumping raw errors. Lesson: fresh scans
   burst RPC calls; ANY single-shot eth_call in a scan path needs its own retry
   loop. RETRY ONLY TRANSIENT STATUSES (429/502/503/504) — v1 retried 422 too,
   which spun "attempt 3 of 3" on permanently-broken contracts (Emad's
   screenshot showed exactly this). Permanent 4xx = fail fast with the real
   server message.

## 4b. ComboX scraped as default (later 8/25)

Emad: "this is not a combox rarity gallery… combox never needs to show up as
default, scrape it." The `/rarity` page used to auto-load the legacy ComboX
gallery when no `collection=` param was present. Removed:

- API: no-collection GET on `/api/rarity-gallery` now returns
  `{ error: "No collection selected." }` (400). The combox_scores/images read
  is gone from the route.
- Client: the initial-load useEffect fetches ONLY the saved-scans list. Page
  opens with an empty state (`No collection loaded` + saved-scan quick-jump
  buttons + scan form), title is plain "Rarity Gallery"; collection name shows
  in the subtitle only after loading.
- Deleting a loaded collection now clears state WITHOUT re-fetching a default
  gallery (that call would have hit the removed legacy path).
- General rule Emad enforced: the tool has NO opinionated default collection;
  it opens neutral and waits for input.

### Reading screenshots when vision credits run out
`vision_analyze` can die mid-batch ("credit balance too low"). Fallback that
works on this Mac for UI screenshots: download the PNG, then OCR via a Swift
snippet using the built-in Vision framework (`import CoreImage; import Vision`,
`VNRecognizeTextRequest` with `.accurate`) run with `swift /tmp/ocr.swift
<img>` — tesseract returned empty on dark-theme screenshots, macOS Vision read
them cleanly.

## 5. Delete saved collections (later 8/25, shipped)

- API: `DELETE /api/rarity-gallery/saved` body `{address}` — removes from
  `collections.json` registry AND `rm -rf .runtime/rarity/<address>/`
  (ranked.json + images.json), so a later rescan starts fresh.
- UI: "✕ Delete" button beside the Saved scans dropdown, visible whenever the
  dropdown's current value is a saved collection (`pickedSaved ||
  collection?.address` must be in `saved`). After delete: drop from list,
  clear selection, show the empty state (no default gallery exists anymore —
  see §4b).
- Verified end-to-end via curl: POST a dummy → DELETE → GET shows gone.

Cross-ref: the standalone multi-collection reveal sniper lives in
bunker-snipe, not Mint Room → `references/reveal-sniper-multicollection.md`.

### Pitfall: "I don't see the X" after shipping a UI control
1. `/rarity` is a CLIENT component — server HTML never contains client-only
   strings, so `curl | grep 'new-button'` returning 0 proves nothing. Verify
   freshness by grepping built chunks instead:
   `grep -rl 'marker' .next/static/chunks/*.js`.
2. Emad's tab caches old bundles — tell him Cmd+Shift+R before concluding the
   feature is broken.
3. Design rule he reacted to: icon-only buttons (bare ✕) that only appear in a
   secondary state read as missing. Prefer labeled buttons ("✕ Delete") that
   appear as soon as the relevant selection exists, not after extra steps.
4. Deleting needs a target: tie destructive actions to the dropdown's selected
   value so the wrong collection can't be fat-fingered.

## 6. Failed scans must never register (later 8/25)

Emad hit "Could not read tokenURI from this contract." on Farting Unicorn and
the dead collection kept reappearing in Saved scans. Root cause: TWO
registration points ran BEFORE the tokenURI gate — the `resolveOpenSeaName`
block wrote `collections.json` during name resolution, and the post-probe
register block fired before the seenUris check. Fixes:

- ALL registration now happens AFTER the tokenURI gate (`seenUris.length === 0`
  → 502 return happens first). Name resolution only resolves for display.
- Client maps that error to plain language: "This contract doesn't expose
  readable token metadata, so it can't be ranked."
- Rule: any side effect (registry write, cache write) must sit behind every
  validation gate that can reject the request — otherwise rejected inputs
  leave permanent residue the user then has to delete manually.
- Emad's bar: "this error should never come up again" = fix the CLASS, not the
  instance. He notices when the same class of error recurs even once.
