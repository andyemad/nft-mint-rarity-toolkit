# NFT Manager — live wallet inventory + consolidate

Shipped 2026-08-24 (resumed mid-flight after a rate-limited session reset).
Replaced the honest "Coming soon" inventory card with a working inventory UI.

## What exists now

- `app/api/nft-inventory/route.ts` + `lib/server/nft-inventory.ts`
  - `GET ?collection=…` — scans OG wallet + every fresh wallet for tokens
    owned in the collection (OpenSea-backed). Returns
    `{scan: {collection, walletsScanned, tokens:[{tokenId, ownerName,
    ownerAddress, listedEth, openseaUrl}], partial}}`. `partial: true` means
    OpenSea throttled mid-scan — UI says "Rescan for the rest".
  - `POST {action:"consolidate", collection, tokenIds}` — sends every owned
    token to the OG wallet; per-token statuses confirmed/broadcast/failed.
- `components/NftManagerView.tsx` — Inventory card sits ABOVE the collection
  inspector. Pressing **Inspect** auto-fires `scanInventory()` after the
  `/api/rarity-gallery` call, so ONE user action = TWO fetches to different
  endpoints. Rescan button appears once inventory exists.
- Consolidate button label carries the live count
  (`⇐ Send all N to OG wallet`); result message splits
  confirmed/broadcasting/failed honestly.

## Pitfalls hit (test migration after UI change)

- When a component migrates from placeholder → live UI, the OLD tests fail
  with "Unable to find element" — that is the signal to UPDATE THE TEST to
  the new contract, not to revert or special-case the component.
  This session: `nm-inventory-note` (coming-soon note) became
  `nm-inventory-empty` (pre-inspect hint); honesty assertions moved to the
  new copy ("OG + fresh", "tokens you own").
- NEVER assert total `fetchMock` call counts when one action fans out to
  multiple endpoints — filter by URL instead:
  `fetchMock.mock.calls.filter(([url]) => String(url).includes("/api/rarity-gallery"))`.
  Total counts break the moment a second auto-fired request is added.
- Full gates after any view change: `npm run check` (or bare
  `npx tsc --noEmit`), `npm test`, `npm run build`.

## Resume-after-crash pattern that worked

Session died mid-render (rate limit + fallback auth failure + compression
timeout). Recovery: `git status --short` showed the uncommitted feature
files + new untracked API dirs → read the failing tests to reconstruct the
intended contract → finish the migration → green suite. Uncommitted work
survives crashes fine; the tests ARE the spec of what was intended.

## First real-use fixes (8/24 evening — Emad's live session)

Emad's first hands-on use found: consolidate errored (`invalid network
object`), List appeared dead, and the "OpenSea ↗" label wasn't clickable.
All fixed and verified with real txs/orders:

- Route bugs (provider `{chainId}`, OG keyfile name, gated ownerOf check)
  → detailed in `references/opensea-listing-seaport-rh.md`.
- The OpenSea ↗ text was a `<span>`; only the token number linked. It's an
  `<a>` now. Lesson: when converting a row from one big link to a div of
  controls, EVERY affordance that looks like a link must be an anchor.
- List button is disabled until the shared price input has text. That is
  intentional but reads as "broken" at a glance — keep the placeholder
  self-explanatory ("Price in ETH") so the dependency is visible.

## List action (added later 8/24)

`POST {action:"list", collection, tokenIds:[one], priceEth, durationSeconds}`
signs and posts a Seaport listing for one owned token. Validation order:
0x contract → exactly one tokenId → positive decimal price → duration
300–2592000s → token must appear in the inventory scan (ownership check)
BEFORE any signing. Full wire shape, zone/conduit/fee requirements, and the
seaport-js config that works → `references/opensea-listing-seaport-rh.md`
(that file also records a LIVE test listing of #3309 left posted — check it).
UI: shared `nm-listing-price` input enables per-token `nm-list-{id}` buttons;
result line `nm-listing-msg`. Wallet-op log action `"nft-list"` added to the
union in wallet-ops-store.ts. The #3309 live test listing was cancelled by
Emad; feature is complete and validated (750/750 tests, tsc clean).

## Slug-from-URL bug (fixed 8/24 late — "No tokens owned across 14 wallets")

Emad pasted an OpenSea collection URL into the inspector; inventory returned
0 tokens while rarity-gallery worked. Root cause: slug extraction used
`.split("/").pop()` → picked up **"overview"** from
`https://opensea.io/collection/pixel-cats-hood/overview`, so no per-wallet
`nft.collection === slug` match ever hit.

Fix (in `lib/server/nft-inventory.ts`):

- `parseCollectionInput()` is now a pure exported function: parse with
  `new URL()`, filter out junk page segments (`overview, items, activity,
  supply, offers, listings, collection(s), assets`), take the LAST remaining
  segment as slug. A 0x address anywhere in the path wins (asset URLs).
- **Checksum pitfall**: `getAddress()` THROWS on mixed-case-but-wrong-EIP-55
  input — user-pasted addresses must go through a try/catch fallback to
  lowercase (`safeChecksum`). The regression tests caught this.
- Belt-and-braces: bare slugs get resolved to their contract once via
  `GET /api/v2/collections/{slug}` → `contracts[0].address`, so attribution
  matches by contract OR slug (account endpoint fields are inconsistent).
- Removed dead code: the old 20-page `/collection/{slug}/nfts` loop did
  nothing (attribution was always via account endpoint).
- Regression tests: `tests/nft-inventory-parse.test.ts` (7 cases incl. the
  exact `/overview` URL). E2E verify:
  `curl 'http://127.0.0.1:3001/api/nft-inventory?collection=<url-encoded OpenSea URL>'`
  → expect tokens non-empty. Suite after: 757/757.
- Debugging lesson: when a UI shows zero results but sibling features work,
  probe the API layer directly with the EXACT user input before touching
  components — one curl with the real URL reproduced `slug:"overview",
  tokens:0` instantly and isolated the bug to parsing.
