# DecisionStack component architecture (established 2026-08-13)

`src/components/decision-stack/` is the independent "Decision Stack" UI, mounted from
`src/app/page.tsx` (replacing the rejected SIGNAL dashboard). It is **fixture-backed** —
no live network; every value comes from `fixtures.ts`.

## Files
- `decision-stack.tsx` (~1500 lines) — master-detail shell + leaf components (most are `export`ed and unit-testable).
- `fixtures.ts` — `FixtureSnapshot` + `fixtureSnapshot` + `MODE_TABS` (10 modes).
- `decision-stack.module.css` — CSS modules; design tokens on `.shell`.
- `decision-stack.test.tsx` — ~34 tests: shell, 9 surfaces, controls, keyboard/a11y, axe, empty states, data states, blocked-manager, USDT toggle, search-result navigation (UX-13).

## Props + render order
- `<DecisionStack snapshot loadingDelayMs=250 error=null>`.
- `loading` (initially true) → `<LoadingSkeleton role="status" aria-label="loading">`.
- then `error` (string) → `<ErrorState role="alert">`.
- else workbench + `SystemRibbon` + `EvidenceStage`.

## Master-detail (no router)
- Bands list: `<div role="list" aria-label="Decision bands">`; each `DecisionBand` is a `role="listitem"` with a main `<button aria-label="<name>, <verb>, <metricA label> <value>, ...">`.
- Selecting a band (click / `j`/`k` / ArrowDown/ArrowUp) sets `selectedId`; `resolveEvidence(snapshot, mode, activeId)` fills the `EvidenceStage` (`<aside aria-label="Selected">`, an `<h2>` holds the name).
- UX-13 (search-result routing): `resolveEvidence` also returns `address: string | null` (the collection contract). `collectionDetailHref(chain, address, query)` → `/collection/{chain}/{address}` (lowercased) with `?q=<query>` appended when a query is active; it is rendered as a "View collection ↗" `<a>` in the `EvidenceStage` header (which takes a `query` prop). Click and keyboard selection both produce the same canonical URL, and the originating query is preserved in the URL.

## Key exported pure helpers
- `buildBands(snapshot, BandFilters)` → `Band[]` for the current mode (live/new-mints/trending/runners/upcoming/search/collection/wallet/eligibility/mint-flow).
- `resolveEvidence(snapshot, mode, id)` → `Evidence | null` with tabs why-now / mint / market / creator / sources.
- `emptyMessageFor(mode, lang)` → per-surface empty copy: `emptySearch` / `emptyUpcoming` / `emptyWallet` / `emptyCollection` / `emptyFeed`.
- Leaf: `DecisionBand`, `EvidenceTabs`, `EvidenceStage`, `RefineLine`, `RefinePopover` (chain/free-paid/window/sort/volume-unit/lang), `WorkbenchModeSwitcher`, `SystemRibbon` (freshness/coverage/finality/errors), `ProvenanceLedger`, `EmptyState` (role="status"), `ErrorState` (role="alert"), `LoadingSkeleton` (role="status").

## State + persistence
- Persisted (localStorage `mint-market-dashboard:decision-stack:v1`): mode, chain, freePaid, trendingWindow, runnerWindow, runnerSort, volumeUnit, lang, `blocked: string[]`.
- Ephemeral (never persisted): query (debounced 200ms), refineOpen, selectedId, evidenceTab.
- `blocked: string[]` has inline block/unblock (`toggleBlock`) AND a dedicated `BlockedManager` surface (`<BlockedManager snapshot blocked onRestore lang>` + `restoreBlock`) that lists blocked projects and restores one without losing unrelated filters. (UX-10 closed.)
- RS-07: `volumeDenom` (`"native" | "usdt"`) + `onVolumeDenom` — a native-vs-USDT toggle distinct from the ETH/USD `volumeUnit` conversion; per-collection `volumeUsdt` in fixtures. DI-13: `UnavailableState` (`role="status"`, `.unavailable` CSS) distinct from the quiet `EmptyState`. EN-05: market metrics are `MarketMetric { label, value, window, sourceIds }` rendered by `MarketFieldList` with window + source labels.

## i18n + chains
- `EN` authoritative, `ES` partial; `t(lang, key)` falls back to EN. `CHAIN_LABEL` = ETH/RH. ARC rendered `coming soon` (disabled); Stable intentionally absent (DS-17).

## Fixture windows
- Trending: 1m/5m/10m/30m/1h/6h/12h/24h. Runner: 1m/5m/15m/1h/1d.

## Accessibility testing (UX-19) — jest-axe
- Deps: `jest-axe` **plus `@types/jest-axe`** (jest-axe ships no types; `tsc` fails without it).
- Pattern: render with `loadingDelayMs={0}`, `await screen.findByRole(...)` to flush the 0ms loading effect, then `const results = await axe(container)`, filter `v.impact === "serious" || v.impact === "critical"`, assert `[]`.
- Assertion detail: `expect(seriousOrCritical.map(v => ({id, nodes})).toEqual([]))` so a failure lists the violating rule ids.

## Test pitfalls
- After render with `loadingDelayMs={0}`, the first frame is still `LoadingSkeleton` — use `await findBy*`, never `getBy*`, for the first assertion on the hydrated/error state.
- `getByRole("button", { name: /^Band Name/ })` matches the band button's aria-label (starts with the name). `getByRole("heading", { name })` targets the EvidenceStage `<h2>` (the band name is a `<span>`, not a heading).
- Distinct empty copy: switch mode tab, then `getByText(/no recent activity|no stages scheduled|no collections match your search|no collections found/)`.

## Related indexer note (DI-08)
- `src/lib/indexer/utility-filter.ts` — address-based utility/position suppression wired into `mint-feed.ts` (`queryMintFeed` filters `!isUtilityCollection(chain, collection)`); `partitionUtilityMints(facts)` returns `{ kept, suppressed: [{ fact, rule }] }` as the auditable suppression log. Name-based heuristics stay in `src/lib/intelligence/utility-filter.ts` (enrichment has a display name; the indexer only has the address).
