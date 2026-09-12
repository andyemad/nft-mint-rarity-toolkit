# Wave 9 + UI wave A integration contracts (2026-08-23)

Condensed from the session; complements wave8/wave10 reference files.

## Merkle mode (AdvancedTaskPanel, `mode-merkle`, mk-* testids)
- Fetch: GET /api/merkle-plan?contract=0x… → `{ summary }` =
  { root, activeIndex, priceWei, currency, raw } (raw = attempted-selector trail).
- Summary line: shortHex(root) · condition #N · price via weiToEthStringOrNull ·
  native-vs-ERC20 currency tag.
- Inputs: receiver (0x-40 validated), proof JSON textarea with LIVE per-entry
  bytes32 validation (offending entries named by index), qty, expected ETH
  prefilled from priceWei. Empty proof allowed + warning
  "⚠ no proof — will fail on allowlisted drops".
- Rehearse POST /api/tasks body: module:"merkle", moduleParamsJson
  {module_type:"merkle_drop", receiver, quantity, proof}, claim selector string
  for DISPLAY only, valueWei = expected×qty×1e18 exact BigInt or "0".
  NO abiArgs/rawData.

## Known open gap (unchanged)
/api/tasks route calls buildCalldata unconditionally → module tasks posted
without selector/rawData 400 "task has no calldata source". Wiring rawData
derivation from moduleParamsJson (buildClaimCalldata for merkle) into the route/
executor is what makes rehearsals reach simulate for module tasks.

## App shell (components/AppShell.tsx)
- Wraps app/layout.tsx children. Sidebar sections/items:
  CORE: Dashboard /, Tasks SOON, Activity SOON.
  MODULES: Rarity /rarity, OpenSea Checker SOON, NFT Manager SOON.
  MONEY: Transfers SOON, Contract Minter SOON.
  SYSTEM: Wallets /wallets, Settings SOON, Tools SOON.
- SOON = span role=link aria-disabled=true title="Coming soon". Live items are
  <Link> with aria-current="page" (usePathname). Page-title map in the same file.
- Mobile <900px: CSS-only collapse to horizontal scroll strip.
- Tests: tests/app-shell.test.tsx mocks next/navigation usePathname via vi.mock;
  asserts brand, all hrefs, aria-current on active, aria-disabled on SOON,
  loopback indicator. 7/7.

## E2E interaction contract with the shell
- Sticky topbar (62px) intercepts auto-scrolled clicks → globals.css has
  `html{scroll-padding-top:76px}`; topbar z-index 20; grain overlay z 5 (was 40).
- e2e.mjs launches playwright-core with Brave executablePath; any probe script
  must reuse that launch config. Emad's own long-lived next start may hold :3000
  with a STALE build — verify served HTML contains your new CSS class before
  trusting a manual probe; prefer the e2e port 4186.
