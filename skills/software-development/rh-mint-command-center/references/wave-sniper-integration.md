# Reveal Sniper — Mint Room integration (2026-08-24)

## What shipped
- Sidebar entry `Reveal Sniper` -> `/sniper` under the Modules section of
  `components/AppShell.tsx` NAV_SECTIONS (next to Rarity).
- Page `app/sniper/page.tsx` + `app/sniper/Sniper.module.css` — live status cards
  (phase / daemon pid / wallet balance / buys fired), a 5-step flow explainer, the
  hard-guardrails table, an EDITABLE parameters panel, and a buy-history table.
  Auto-refreshes status via 10s interval; editable params are loaded ONCE on mount
  (separate fetch) so a status refetch never clobbers in-progress typing.
- API `app/api/sniper/status/route.ts` -> `lib/server/sniper.ts`. Loopback-guarded
  (`assertLoopback`). Reads (a) the armed daemon's GLOBAL state at
  `~/.hermes/rarity/snipe_state.json` (buys so far, spent — wallet-level, shared
  across ALL collections; the old per-collection `claystonkz/` path was a v1 relic),
  (b) daemon liveness via `pgrep -f clay_sniper.py --arm`, (c) live wallet balance via
  `eth_getBalance` on the RH RPC (MUST send `User-Agent: Mozilla/5.0` — headerless
  urllib/fetch gets 403, plain curl works because it sends a UA), (d) per-collection
  `scores.json` presence under `~/.hermes/rarity/<name>/`. Read-only — never writes,
  never broadcasts.
- API `app/api/sniper/params/route.ts` — GET reads + clamps current params JSON,
  POST validates + clamps an inbound body then writes atomically. Same `BOUNDS`
  map as the daemon (kept in sync by design).

## Live-editable parameters pattern (the durable lesson)
The caps moved out of hardcoded constants into
`~/.hermes/rarity/snipe_params.json` (GLOBAL, shared across every collection the
daemon snipes), which the ARMED daemon re-reads fresh at the top of EVERY
`run_snipe()` tick and at each loop sleep
(`time.sleep(load_params()["poll_secs"])`). Result: editing a cap in the Mint
Room panel goes live within one poll interval with NO daemon restart.

- **PATH-DRIFT PITFALL (hit 8/25):** after the daemon went multi-collection
  (v2), its params/state moved from `~/.hermes/rarity/claystonkz/{params,state}.json`
  to the global `snipe_params.json` / `snipe_state.json`. The Mint Room page kept
  reading the OLD per-collection paths — cap edits from the UI silently never
  reached the armed daemon. Rule: the UI's paths MUST be derived from (or verified
  against) clay_sniper.py's own `PARAMS_FILE` / `STATE_FILE` constants, never
  hardcoded independently. When a config file moves, grep both sides.
- `DEFAULT_PARAMS` + `PARAM_BOUNDS` defined in clay_sniper.py; `load_params()`
  clamps every value into bounds and falls back to defaults on any read error,
  so a bad/malformed write can never loosen caps past the ceiling.
- The Mint Room API mirrors the same bounds (belt + suspenders). Example clamps
  verified live: `max_buys:999 -> 10`, `max_per_buy_eth:50 -> 0.05`,
  `poll_secs:1 -> 5`.
- CRITICAL OPERATIONAL PITFALL (hit this session): while verifying the clamp, a
  test POST wrote the CLAMPED TEST VALUES (10 buys / 0.05 per-buy) into the LIVE
  params file that the ARMED daemon reads. Always restore the user's approved
  config immediately after any clamp/probe test, and never assume a clamped
  value on a live armed daemon is harmless — pre-reveal it fired nothing (safe
  this time), but the daemon doesn't distinguish test writes from real ones.
  Better: probe clamps against a THROWAWAY copy of the file, or round-trip
  restore in the same terminal command.

## The RH-chain Seaport buy path FINALLY WORKS (supersedes the old "49/49 reverts")
The long-standing bunker-snipe belief "RH Seaport fulfillAdvancedOrder reverts
49/49, root cause unresolved" was WRONG about the root cause. Session 2026-08-24
proved a working fill against a live Clay StonKz order:
- The 49/49 "reverts" on BUNKER were largely **HTTP 400 from OpenSea's
  `fulfillment_data` endpoint BEFORE any tx** (stale/expired/taken orders), not
  an encoding bug.
- Working recipe (all against `api.opensea.io/api/v2` with `X-API-KEY`):
  1. `GET listings/collection/<slug>/best?limit=50` -> active orders with
     `price.current.{value,decimals,currency}`.
  2. `POST listings/fulfillment_data` with
     `{listing:{hash,chain,protocol_address}, fulfiller:{address}}` -> the
     `transaction` object (to/value/input_data).
  3. Encode `fulfillAdvancedOrder` from `input_data` (param order +
     criteriaResolvers + fulfillerConduitKey; can use a keccak selector or
     CanonicalOrder). See `encode_fill`/`ADV_ORDER` in clay_sniper.py.
  4. **eth_call dry-run FIRST** — `{from:wallet, to, value, data}` via
     `eth_call`, treat `result` present AND not `"0x"` as fillable.
  5. Only then sign + `eth_sendRawTransaction`. Gas via `eth_estimateGas`
     + buffer, nonce from `eth_getTransactionCount`, RH uses legacy type-0
     txs (see RH specifics pitfall in SKILL.md).
- **ETH vs USDG listings (decimals matter):** Clay StonKz lists in native ETH
  (`decimals:18`); other collections on RH (e.g. ComboX) list in USDG
  (`decimals:6`). The sniper's floor/target math must filter to ETH-native
  listings only (`_price_wei` non-zero) — price is "at floor" in ETH terms, and
  a USDG rail is a different payment rail to never auto-buy into.

## Decoys / gotchas during this build
- Python server page that embeds literal CSS `{}` blocks cannot use
  `str.format()` — the CSS braces collide. Use token replacement
  (`@@NOW@@` -> `html.replace(k,v)`) instead.
- `os` has no default export under the repo's strict tsconfig — use
  `import { homedir } from "node:os"`.
- The `@/` alias and node_modules `.d.ts` noise shown by write_file's lint are
  the KNOWN false positives — real gate is `npx vitest run <files>` +
  `npx tsc --noEmit` + `npm run build`.
- Adding a nav entry to AppShell: also add the href to `LIVE_HREFS` in
  `tests/app-shell.test.tsx` or the app-shell SOON-item test fails
  ("expected A to be SPAN").
- After `npm run build`, `launchctl kickstart -k gui/$(id -u)/com.patelai.rh-mint-room`,
  then curl the new API + page for 200 (server serves built assets at boot).
- The armed daemon runs under `.venv/bin/python` (has eth_account); system
  `python3` does not — module import error is the tell.

## De-Clay / generic pass (2026-08-25, shipped + live)
Emad: "rarity sniper mentions clay specifically… an option to show what
collections are being sniped." Two durable patterns came out of it:

- **Parse the daemon's config as the UI's source of truth.**
  `lib/server/sniper-collections.ts` extracts the `COLLECTIONS = [...]` literal
  from clay_sniper.py source with a balanced-brace/quote-aware scanner (handles
  nested dicts, escaped quotes, trailing comments). The "Collections being sniped"
  table on /sniper renders that — adding a collection to the daemon needs ZERO
  Mint Room changes and the UI can never drift. Do NOT duplicate a watched-list
  in TS by hand; duplicated lists rot.
- **Cross-component chrome sync via module-level pub-sub, not context.**
  The sidebar brand chain label (AppShell) must follow the Dashboard's chain
  `<select>` (CommandCenter) without remounting anything. `lib/selected-chain.ts`
  is a ~30-line get/set/subscribe store; CommandCenter publishes on select-change
  AND on mount (so deep-links set it), AppShell subscribes via useEffect. React
  context would re-render every page for one label; this keeps the blast radius
  at two components. Test note: the listener's setState is React-batched — wrap
  the publish + assert in `await act(async () => {})` or the label read is stale.
- Tests: tests/sniper-page.test.tsx (incl. an anti-regression "no Clay copy"
  assertion), tests/sniper-collections.test.ts, tests/app-shell-chain.test.tsx.
