# the test collection reveal-sniper daemon (built 2026-08-24)

Standalone guarded auto-buy daemon at
`~/Projects/sniper/clay_sniper.py`. Rehearsed end-to-end in DRY mode;
buy path proven via eth_call against a live testcollection order. ARMED same day
with the user's explicit approval slate (max 3 buys, ≤0.010/buy, ≤0.030/day,
0.050 reserve); runs as a Hermes background process polling every 20s.
Launch interpreter matters: use `~/Projects/sniper/.venv/bin/python`
(system python3 lacks eth_account and the daemon dies instantly with
ModuleNotFoundError while *looking* started).

Live visual companion: `~/Projects/sniper/sniper_status_server.py`
serves a read-only dashboard on http://localhost:8139/ (daemon liveness via
pgrep, chain balance, caps usage from snipe_state.json, 10s meta-refresh).
This was built 8/24 as a quick throwaway. **the user then corrected the delivery:
the control room is the all-in-one suite — integrate the status there, don't run a
separate probe.** See "Integrating a module into the control room" below. The 8139
file stays as a disposable fallback, never the deliverable. Still true: build
the status page as part of arming anything, don't wait to be asked — but build
it IN the control room.

## Architecture (5 phases, single loop, --once for one pass / loop otherwise)

1. **Reveal detection** — eth_call `tokenURI(uint256)` on ~8 spread tokens;
   any divergence from the shared pre-reveal CID = reveal. Same watcher logic
   as `~/.hermes/scripts/testcollection_reveal_watch.py`.
2. **Rank** — FAST PATH first: `GET /api/v2/chain/robinhood/contract/{CA}/nfts?limit=200`
   paginated via `next` → per-token traits. 5000 the rarity-test collection tokens = ~25 pages ≈ 5s.
   Compute OpenRarity info-content (`-log2(count/total)` summed). Fallback if
   <90% traits: on-chain sweep + IPFS metadata (multi-gateway).
   Cache `scores.json` (1h TTL) so the next tick doesn't re-rank.
3. **Match** — `GET /listings/collection/testcollection/best?limit=50` (needs
   opensea_key). Filter to ETH-native listings only (decimals 18), compute
   floor, select rarest TOP_RANKS=150 that are listed ≤ floor × 1.10.
4. **Buy** — per candidate, rarest first: build fulfillment_data → encode
   fulfilled → `eth_call` dry-run MUST pass → then broadcast only if `--arm`.
5. **Hard caps** (consts in file, not CLI-arg overridable): MAX_BUYS=3,
   MAX_PER_BUY_ETH=0.010, DAILY_CAP_ETH=0.030, RESERVE_ETH=0.050, POLL=20s.

## The encoder that works (Seaport 1.6, RH)

- `fulfillment_data` `transaction.input_data.advancedOrder.parameters` +
  `criteriaResolvers` + `fulfillerConduitKey` + `recipient`.
- Function selector: derive from the canonical signature string
  `fulfillAdvancedOrder(((...)),(...)[],bytes32,address)` → keccak → first 4
  bytes. The OpenSea `transaction.function` field IS this full signature, so
  `sel(tx["function"])` works; choose the canonical form when absent.
- dry-run gate: `eth_call` with `{"from": wallet, "to": protocol, "data": calldata, "value": price}`.
  returning `result==0x…1` = would fill.

## Rehearsal results (no spend)

- Pre-reveal tick on testcollection (target): silent, exit 0. ✓
- the rarity-test collection (revealed stand-in): ranked 5000 in seconds; top-5 = the 1/1 mythics
  (score 45.98b). ✓
- Live testcollection #1081 @ 0.0135 ETH: `build_buy_tx` + `dry_run_ok` integrated
  → "SUCCESS (would fill)". ✓
- the rarity-test collection listed entirely on USDG rail → target filter correctly yielded none
  (not a bug — different payment rail).

## Pitfalls hit while building

- Sniper original GATEWAY = nftstorage.link → 0/5000 metadata. Fix: GATEWAYS
  list with fallthrough; probe each runtime, don't trust stale notes.
- `compute_rarity()` crashed with `AttributeError: 'list' has no attribute
  'get'` — it expected dict-wrapped attributes; OpenSea /nfts returns raw
  trait-list. The dict-vs-list shape must be tolerated in one scorer.
- the rarity-test collection slug is `raritytest-nft`, not `raritytest` (raritytest = a different collection) —
  resolve slugs via `/collections/{slug}` probing, never assume.
- A fixed retry loop reusing one nonce after a confirmed-landed check-in caused
  endless 400s (anti-replay). Any retry of a signed stateful write must mint a
  FRESH nonce per attempt, and verify by reading back the authoritative state,
  not by grepping a success string.

## Arming + status-page session notes (2026-08-24, later same day)

- **RPC 403 without User-Agent**: python `urllib` calls to the RH RPC get HTTP
  403 unless a `User-Agent` header is present (curl works by default, which
  masks it). Every RPC helper in every script must send UA; symptom is the
  status page showing balance "?" while curl from the shell shows fine.
- **HTML templating with Python `.format()` breaks on CSS braces** — a page of
  inline `<style>` has `{}` everywhere; `.format()` throws KeyError/ValueError.
  Use unique token replacement (`@@TOKEN@@` → str.replace) for HTML-in-Python.
- **Status-page liveness check**: `pgrep -f "clay_sniper.py --arm"` returns
  PIDs; treat ≥1 as RUNNING. Read caps usage from snipe_state.json
  (`buys[]`, each entry has eth/token/tx) — never recompute from logs.
- **Concierge cron.update delivery-change kept refusing even with an approved,
  unconsumed approval_id** ("does not match the exact approved cron action"),
  across three attempts with matching payloads. Don't burn more attempts —
  the workaround that mattered here: the armed daemon itself pings per buy,
  making the watcher-delivery change redundant. If a delivery channel truly
  matters, prefer building the ping into your own daemon over fighting
  cron.update.
- **Approval flow that worked for arming real spends**: workspace_propose one
  slate naming recipient wallet, hard caps, kill terms, max spend →
  workspace_decide("yes") → execute. the user answers "yes" once and expects both
  items in a multi-item message to be covered — but each *distinct*
  consequence (spend vs cron change) still needs its own slate.

## Integrating a module into the control room (proven 8/24 — the sniper)

the control room = `~/Projects/mint-control-room` (Next.js App Router, prod
`next start` via launchd service `com.the agent.rh-mint-room`, live on
http://localhost:3000). To add a module, match its existing conventions:

1. **lib/server/<mod>.ts** — pure logic, read-only reflection of whatever the
   daemon/script writes. Read `~/.hermes/rarity/testcollection/snipe_state.json`
   + `scores.json` via `node:fs`; daemon liveness via
   `execSync("pgrep -f clay_sniper.py --arm")`; chain balance via
   `fetch(RPC, {headers:{...User-Agent}})` (RH RPC 403s python w/o UA — same
   class of bug as urllib). Use `homedir()` from `node:os`, not `os.homedir()`
   (TS: `import os from "node:os"` fails — no default export).
2. **app/api/<mod>/route.ts** — `assertLoopback(request)` then
   `NextResponse.json(await getXStatus())`, `export const dynamic="force-dynamic"`.
   Path `@/lib/server/<mod>` resolves (tsconfig maps `@/*`→`./*`).
3. **app/<mod>/page.tsx** + `<mod>.module.css** — `"use client"`, poll the
   route every ~10s (`setInterval` + fetch no-store). Copy the card/panel/css
   classes from an existing page (e.g. app/rarity/RarityGallery.module.css)
   so it looks native.
4. **components/AppShell.tsx** — add `{ label, href }` to the right
   `NAV_SECTIONS` heading.
5. **tests/app-shell.test.tsx** — append the new href to the hardcoded
   `LIVE_HREFS` allowlist or the nav test fails (SOON items must render as
   spans). This one you CAN edit; it's the test for the nav.
6. **Build + restart**: `npm run build` (must succeed — the new route/page
   only compiles if it's valid), then
   `launchctl kickstart -k gui/$(id -u)/com.the agent.rh-mint-room` to serve the
   new build. Verify `curl localhost:3000/api/<mod>/status` + `curl -o /dev/null
   -w "%{http_code}" localhost:3000/<mod>` (200).
7. **`npm run check`** for the 738-test gate before declaring done.

Pitfalls hit:
- **TS156 couldn't be the deciding signal** — the repo's node_modules/.d.ts are
  stale (react-server-dom-webpack etc. all "cannot find module"); the REAL proof
  is `npm run build` + `npm run check`, not the editor's tsc view.
- **Sibling overhaul agents edit this repo in parallel** (a `_warning` appears
  if a subagent touched the same file). Keep each module to NEW files (page,
  route, lib, one nav line, one test line). Never rewrite an existing page.
- **Python `/tmp`-style standalone status pages get rejected** for anything
  the control room should host — always integrate.
