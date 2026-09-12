# MintTerminal — home-page UI (visual/gesture parity with MintGo)

Emad's bar for "parity" is the VISIBLE product, not the functional acceptance gates.
This file records what the reference (MintGo) actually is and how the rebuilt home page matches it.

## Correction #1 (2026-08-13) — parity is visual, not functional
- Agent reported "158/165 parity done" and handed the user a functional DecisionStack wireframe.
- User: "Awful — how is this on parity with the og", then "it's not about the design but the
  gestures the UI shows mainly and of course a sleek beautiful design."
- Lesson: measure/report VISUAL + gesture parity against reference screenshots, not just internal
  test-gate parity. Never hand over a bare wireframe and call it "check out the UI." Get the
  reference screenshots EARLY and build to them.

## Correction #2 (2026-08-14) — desktop ≠ mobile layout
- First rebuild shipped the MOBILE layout (tabbed single column) as the desktop default.
- User (with desktop screenshots): "why would you have the mobile version as the desktop version?
  the desktop version should be like this".
- Desktop = THREE-COLUMN board (Trending | New Mints | Market side-by-side) + a featured mint
  module on top. Mobile (<1024px) = tabbed single column.
- Lesson: capture the reference's DESKTOP and MOBILE layouts SEPARATELY and reproduce both.
  Don't collapse to one layout and ship it everywhere.

## Correction #3 (2026-08-14) — popups rejected; socials + copy must actually work
- The auto-spawning "Mint Live"/"Starting" notification overlays (a `LiveNotifications` toast stack)
  were REMOVED. User: "let's get rid of those annoying popups showing mints... we can use that for
  something else later." Do NOT re-add an auto-toast overlay layer without an explicit ask.
- Social buttons MUST resolve: user "none of these collections have the opensea resolving or the
  twitter". Twitter/OpenSea are now real `<a target="_blank" rel="noopener noreferrer">` links via a
  `collectionLinks(name)` helper (x.com/search + opensea.io/collection/<slug>). Real handles/slugs come
  from the enrichment layer once live data is wired — never ship inert social `<button>`s.
- Copy MUST copy the full address: user "the contract address can not even be copied". Fixtures store
  FULL 42-char addresses; display via `fmtShort` (0x…last4, with `title=` full); the copy button runs
  `navigator.clipboard.writeText(full)` and flips to ✓ for ~1.6s.

## MintGo layout spec (corrected)
- **Desktop (≥1024px):** header (wordmark + icon buttons + Donate) → search + filter row
  ("Upcoming Mints" / ALL·ETH·RH·ARC chain chips / "Tools" / "Connect Wallet") → featured mint
  module → three columns (Trending | New Mints | Market).
- **Mobile (<1024px):** header → search + filters → featured module (stacked) → tabs
  (Trending/New Mints/Market) → one column.
- Header/filter gestures: search "Name, symbol or contract address"; chain chips; "Connect Wallet"
  is rendered but disabled/titled "not enabled in this build" (this product never embeds a browser
  wallet — see repo memory).

## Featured mint module (desktop top)
- avatar (PixelIcon) + name + chain tag + social LINKS (𝕏 Twitter + ⛵ OpenSea, real `<a>` links) +
  "X3" badge + "⚠ Scam N" flag.
- contract address (truncated via `fmtShort`, full in `title`) + verified ✓ + copy button that copies
  the full address and shows a ✓ success state.
- stats: MINT LIVE (progress bar + minted/total), HOLDERS, LATEST (ticking), CREATED, CREATOR.
- mint controls: quantity stepper, multiplier chips x10/x30/x60/x100 (color-coded: mint/blue/grey/purple),
  "Mint Now" button. For non-live rows the button is disabled and reads "Not live".
- Clicking any row in any column re-selects it as the featured project (SelectedView resolves
  featured-mint vs market-row vs trending-row; non-live rows show "—", never fabricated mint data).

## Column specs
- **Trending:** time filters 1m/5m/10m/30m/1h/6h/12h/24h; "≥ 200" tag; rows sorted by momentum
  with a +N counter; top/hot item gets a yellow ring (`hotRow`).
- **New Mints:** live counter "● 500"; rows with ticking relative timestamps (0s/1s/2s),
  ERC721/ERC1155 + "Free"/"Proxy Mint" mini-tags, +N delta.
- **Market:** ranked #1–#10; sortable NAME/VOL/CHG/SALES; USDT↔ETH denomination toggle; "≥ N"
  volume filter; some rows are USDG-denominated (e.g. CatBroker) — a per-row `denom` field, not
  a global switch. `changePct: null` renders "—" (dash), never a fake number. Rank-1 row gets a
  red ring (`hotBorder`).

## Responsive technique (CSS-only — no JS matchMedia, no SSR flash)
- `.board` = grid, `1fr 1fr 1fr` desktop / `1fr` mobile.
- `.tabs` = `display:none` desktop / `inline-flex` mobile (tab styles live INSIDE the mobile media query).
- Per-column visibility: `.colHidden { display: none }` is scoped INSIDE the `@media (max-width:1023px)`
  block, so on desktop it has no rule and all three columns stay visible. The tab state adds
  `.colHidden` to the non-active columns — desktop ignores it, mobile hides them. This is the whole
  trick: one render tree, CSS decides, no `window.matchMedia`/`useState` flash and no hydration mismatch.

## Implementation (`src/components/mint-terminal/`)
- `mint-terminal.tsx` — `"use client"`. `MintTerminal` holds state: tab, chain, windows, volumeMin,
  sortKey/dir, denom, selectedId, search, qty, mult, plus a `now` tick (`setInterval` 1000ms) +
  `mountedAt` driving relative timestamps/countdowns. Sub-components are TOP-LEVEL (module scope) —
  eslint `react-hooks/static-components` rejects a component defined inside another during render
  (extract `SortHeader`/`FeaturedModule` etc. to module scope).
- `market-data.ts` — `MARKET_ROWS` (rank, volume, denom eth|usdt, nullable changePct, sales, hot),
  `TRENDING_ROWS` (momentum, hot), `MINT_EVENTS` (secondsAgo, delta, tags[]), `FEATURED_MINT`
  (The Robinhood: FULL contract/creator/minted 9960/10000/holders 5.0K/created 12h/multipliers/badge X3/scam 11),
  `DETAILS` (per-project mint/creator/market data — FULL contract addresses). `fmtEth` uses a toFixed
  cascade, NOT `toExponential` (scientific notation like `4.430e-4` reads as a bug). `fmtShort(addr)`
  truncates for display; `collectionLinks(name)` returns demo `{twitter, opensea}` URLs.
- `mint-terminal.module.css` — dark tokens: `--bg #0a0b0d`, surface `#14161a`/`#1a1d23`,
  border `#26292f`, text `#e8eaed`/`#9aa0a8`/`#5f6670`, accent mint `#3cec8c`, purple `#8b5cf6`,
  pos/neg `#3cec8c`/`#ff5c5c`. Icons = `PixelIcon` (`pixel-art.tsx`) — crisp per-project pixel-art SVG
  sprites (image-rendering: pixelated) resolved by collection id via `resolveSpriteKey`, with a fallback
  for unknown ids. This replaced the emoji-on-colored-square fast path.
- Wired in `src/app/page.tsx` (`<MintTerminal />`), replacing DecisionStack as the home page.
  DecisionStack + its ~678 tests remain (not deleted) — just no longer the landing view.
- The bottom nav (back/list/domain/refresh/more) was REMOVED in the desktop rebuild; mobile tabs
  replaced it. There is no bottom nav in the current tree.

## Simulated "live" feel (no backend yet)
Fixtures are static, but the UI fakes liveness: a 1s interval ticks `now`; new-mint timestamps and
the featured LATEST render as `secondsAgo + elapsed`. Real on-chain ingestion is still the pending
D1/worker infra approval. API routes return structured `..._UNAVAILABLE` (designed degradation) until
D1 is provisioned.

## Anti-clone review (2026-08-14)
- `research/ANTI-CLONE-REVIEW.md` flags the home page as a COMPOSITION clone of MintGo (it matches the
  repo's own forbidden fingerprint in ORIGINAL-IA-DIRECTIONS.md:48-58), NOT an asset clone (no copied
  logo/name/artwork). Pending Emad's call: keep the MintGo-shaped layout (what his screenshots asked for)
  vs restructure to be clearly original. This is a product decision, not a code fix.
- Known inert gestures (flagged, not all fixed): time-window chips toggle but don't re-filter data,
  search matches name only (placeholder overpromises "symbol/contract"), header buttons (Upcoming
  Mints/Tools/Views/Wallet/Donate) are dead, Market header columns don't align with row stat columns.

## Deploy + QA loop
- Deploy to the existing Vercel project (`mint-field-guide` -> `mint-field-guide.vercel.app`):
  `cd ~/Projects/mint-field-guide && vercel --prod --yes`. Re-deploy the CURRENT tree before handing
  the URL — the previously-live build can be hours stale (this bit us: the 8h-old deploy predated the
  whole parity push).
- Screenshot-verify with Playwright + Brave at BOTH viewports (e.g. 1440×1000 desktop and 390×844
  mobile): launch Brave headless, `goto` the URL, assert zero console errors + mobile tab count,
  `screenshot(full_page=True)`, then vision-review each and fix anything flagged (scientific notation,
  a wrong "Mint Live" pill on an upcoming drop, duplicated empty-state copy, or a mobile layout shown
  at desktop width).
