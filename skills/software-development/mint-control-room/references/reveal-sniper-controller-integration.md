# Reveal Sniper — the control room integration (8/24; GENERIC since 8/25)

The multi-collection reveal auto-sniper lives in
`~/Projects/sniper/clay_sniper.py` (decoupled Python daemon) and is
surfaced inside the control room as a native page + loopback API. Pattern is reusable
for any guarded on-chain auto-buy surfaced through the control room.

## Architecture (decoupled, clean)
- Daemon (`clay_sniper.py --arm`) polls the RH chain every tick, detects reveal,
  ranks tokens from OpenSea `/nfts` traits (~5s/5000), matches top-N rarest
  listed ≤ floor×mult, then per-candidate: skip if over caps → `eth_call`
  dry-run MUST pass → sign + broadcast. Caps are HARD.
- the control room = read/control surface only. `app/sniper/page.tsx` + CSS module,
  `app/api/sniper/status/route.ts` (GET status), `app/api/sniper/params/route.ts`
  (GET/POST params), `lib/server/sniper.ts` (status logic),
  `lib/server/sniper-params.ts` (shared params source of truth),
  `lib/server/sniper-collections.ts` (parses COLLECTIONS from the daemon source).
- daemon runs with `~/.venv/bin/python` (has `eth_account`; system python3 does
  NOT). Instantiate via `importlib.util` for fast probes, or `.venv/bin/python`.

## LIVE-EDITABLE DAEMON PARAMS — do this exactly
User must be able to edit caps (per-buy, daily, reserve, top-N, floor-mult,
poll interval) in the UI and have them apply WITHOUT restarting the daemon.
1. **Params file is the single source of truth**: `~/.hermes/rarity/snipe_params.json`
   (GLOBAL since the 8/25 multi-collection v2 — shared caps across ALL sniped
   collections; the old `testcollection/params.json` path is a v1 relic and pointing
   at it means UI edits silently never reach the armed daemon. PATH-DRIFT RULE:
   derive UI paths from clay_sniper.py's own `PARAMS_FILE` / `STATE_FILE`, never
   hardcode independently).
   Daemon calls `load_params()` fresh at the TOP of every tick and in the sleep
   loop, so edits apply within one poll interval. No restart.
2. **Bounds enforced in TWO places**: the POST API clamps, AND the daemon's
   reader clamps on load. A bad write can never loosen caps — it clamps to a
   sane ceiling instead of silently blowing out (e.g. `0.5`/buy → 0.05).
3. **One shared module for status AND params**: put DEFAULTS + BOUNDS +
   `readParams()`/`clampParams()` in `lib/server/sniper-params.ts`. POINT BOTH
   routes at it. CRITICAL PITFALL: if `/api/sniper/status` hardcodes
   `topRanks:150, perBuy:0.01` in its own config while the editor writes a file,
   the guardrails table shows STALE values forever even though the daemon uses
   the new file. The two routes can never disagree if they read one module.

## Next.js controlled-input PITFALL (user hit this)
`<input type="number">` whose `value` is derived by `Number(e.target.value)`
on every keystroke EATS the leading `0.` while typing: typing `0.015` renders
as `15` because each keystroke round-trips through the number parser. FIX:
- Keep per-field **draft string** state (`Partial<Record<key,string>>`).
- `value={drafts[key] ?? String(params[key])}` — never parse mid-keystroke.
- `onChange` writes the raw string; `onBlur`/`onSave` parses to number.
- `saveParams` merges drafts over stored values, falls back to stored value if
  a draft is empty/NaN.
- Give each field a real `step` (`0.001`/`0.01` for ETH, `1` for counts/int).
  Unset step defaults to `1`, so the spinner jumps whole ETH — wrong for
  fractional caps.

## Avoid literal \uXXXX in JSX text
In plain JSX text (outside `{...}`), `\u00b7` renders as the literal characters
`\u00b7`, not a separator. Use the actual glyph (· — ≤ ≥ × …) directly. Inside
JS string literals inside braces it's fine. grep: `\u00|\\u20`.

## Add-route conventions in the control room
- New API routes: `export const dynamic = "force-dynamic";` +
  `assertLoopback(request)` guard, return 403 on failure.
- Sidebar: add to `NAV_SECTIONS` in `components/AppShell.tsx`.
- TESTS: `tests/app-shell.test.tsx` has a hardcoded `LIVE_HREFS` allowlist.
  Adding a live nav href REQUIRES adding it to that allowlist or
  `npm run check` fails (a SOON item renders as `<span>`, a live one as `<a>`).
- Rebuild + restart: `npm run build` then
  `launchctl kickstart -k gui/$(id -u)/com.the agent.rh-mint-room`.
  Verify with `curl localhost:3000/<route>`.
- The repo is under parallel overhaul (sibling agents). Keep new work in NEW
  files + one or two minimal edits; never rewrite shared/overhauled files whole.

## Rehearsal before spending
Prove the buy path with a live order BEFORE arming: `fulfillment_data` 200 →
encode → `eth_call` dry-run returning `0x…1` (true) = would fill. NO broadcast
in rehearsal. Then verify caps clamp via the API (send 999 buys → returns 10).
RESTORE approved caps after clamp tests — a clamp test writes clamped values
into the LIVE daemon file; the armed daemon will enforce whatever is in it.

## RH-chain Seaport fill root cause (old 49/49 reverts vs this working path)
The inherited BUNKER `fulfillAdvancedOrder` history ("reverts 49/49") was
misread as an ENCODING bug — it was not. Two real causes, both environmental
to the ORDER not to the calldata:
1. OpenSea `POST /listings/fulfillment_data` returned HTTP 400 for
   expired/taken orders — the failure happened BEFORE any tx existed.
2. Orders that broadcasted were stale (already filled) by send time.
Evidence of the working path: on a LIVE clay listing, `eth_call` of the exact
`fulfillAdvancedOrder` calldata returned `0x…1` (true) — a clean fill.
Lesson: for OpenSea fulfillments, re-fetch `fulfillment_data` fresh-right-before
each broadcast and dry-run `eth_call` per candidate; skip ephemeral 400s / stale
order hashes rather than "debugging the encoder". A clean dry-run on a live
order is sufficient proof the buy path works.

## Reveal-day latency upgrades (8/24, rehearsed vs the rarity-test collection)
Detection itself stays POLLING on Robinhood chain — it is a sequencer chain
with no public mempool to sniff and a plain `setBaseURI` flip emits no event,
so even pro tools poll here. The competitive edge is the post-detection
pipeline. Three upgrades, all inside `clay_sniper.py`:

1. **Dual-source rank RACE.** On reveal, run OpenSea `/nfts` trait fetch AND
   the on-chain URI sweep + IPFS metadata path in PARALLEL threads; first
   source to reach ≥90% coverage wins and its ranking is used. Measured:
   OpenSea wins at ~4.2s for 5000 tokens; IPFS path alone was still grinding
   minutes later.
   - SPEED PITFALL: naive `t1.join(timeout=180); t2.join(timeout=180)` waits
     for BOTH threads — the loser keeps the tick alive (measured 151s!). FIX:
     loop `t.join(timeout=1.0)` slices, return the moment the done-flag Event
     is set; let the losing thread die with the long-lived daemon. A one-shot
     test script may print "cannot schedule new futures after interpreter
     shutdown" from the abandoned loser — harmless there, never seen in the
     daemon.
2. **Warm listing cache.** Pre-reveal ticks call `get_listings_warm()` (25s
   TTL) so the best-listings fetch is always hot; post-reveal target matching
   reads it instantly (cached 0.000s vs 0.19s cold). One less HTTP round-trip
   between detection and buy broadcast.
3. **Tighter cadence via params, not code.** `poll_secs` is already a live
   param — drop it through the the control room panel for reveal day instead of
   editing the daemon. Floor clamp was lowered 8/24 from 5s to 2s in
   `PARAM_BOUNDS` (clay_sniper.py); live value 3s. Real tick period = sleep +
   sampling time (~1–2s of RPC calls), so poll_secs=3 yields an effective
   ~4–5s cadence — that's the physical floor, don't promise faster.
   NOTE: changing PARAM_BOUNDS requires a daemon restart; changing only
   params.json does NOT (load_params() is re-read every tick).

## "Artist said it revealed" ≠ revealed (8/24 verification pattern)
When the artist announces a reveal but the sniper still logs pre-reveal,
verify on-chain before touching anything: sample `tokenURI(uint256)`
(selector `0xc87b56dd`) for ~300 tokens spread across the supply
(start/middle/end) via direct eth_call on the RH RPC and compare against the
known pre-reveal CID. All-identical = not revealed; announcements routinely
precede the actual `setBaseURI` flip. The armed sniper needs no action — it
fires when URIs actually change.
- GOTCHA: the RH RPC (`rpc.mainnet.chain.robinhood.com`) returns HTTP 403 to
  plain urllib calls — send `User-Agent: Mozilla/5.0` header (the sniper's own
  rpc() helper already does this).
- Pre-reveal collections also 404 on OpenSea nft-by-id endpoints; don't read
  that as "collection gone".

Rehearsal pattern for race code without spending: point module constants at a
revealed collection (the rarity-test collection) via importlib override, run `race_rank_sources()`,
time it. Verify the winner-timeout fix by checking elapsed time (~4s), not
just success.

## Post-reveal rank pipeline in the control room API routes (8/25, live-verified on testcollection)
The "Reveal seen but metadata not fetchable yet" 503 from `/api/rarity` and
`/api/rarity-gallery` had TWO independent causes — both fixed:
1. **IPFS-only trait sourcing is a dead end post-reveal.** `/api/rarity`
   fetched traits ONLY via tokenURI sweep + one hardcoded gateway. Gateways
   rot: `nftstorage.link` now 403s from this Mac, `ipfs.io`/`dweb.link` 403,
   pinata 429s under parallel hammer. FIX (both routes): OpenSea paged
   `/chain/<key>/contract/<addr>/nfts?limit=200&next=` is PRIMARY — traits are
   indexed there within seconds of reveal (~35 pages ≈ 4s for 6969 tokens).
   On-chain URI sweep + IPFS stays as fallback for unindexed stragglers.
   Gateway choice: `gateway.pinata.cloud` works but needs per-request 429
   retry-with-backoff when hammered (added to clay_sniper.py `ipfs_json`,
   which required a daemon restart — code changes do, param changes don't).
2. **Key lookup divergence.** `rarity-gallery`'s osPage read ONLY
   `process.env.OPENSEA_API_KEY` while the rest of the app uses
   `lib/server/opensea-listings.ts apiKey()` (env var → falls back to
   `~/.hermes/secrets/opensea_key`). No env var ⇒ OpenSea silently disabled.
   FIX: always import the shared `apiKey` helper; never inline key loading.

### the control room server lifecycle PITFALLS (cost an hour)
- launchd `com.the agent.rh-mint-room` runs **`next start` (production build)**,
  NOT dev. Editing `app/**` source does NOTHING on port 3000 until
  `npx next build` + `launchctl kickstart -k gui/$(id -u)/com.the agent.rh-mint-room`.
  A running `next dev` elsewhere compiles fresh code but that's a different server.
- **Orphaned next-server processes squat on port 3000** serving stale compiled
  bundles — symptom: edits verified by tsc but endpoint behavior never changes.
  Check `lsof -nP -iTCP:3000 -sTCP:LISTEN` vs the launchd PID; kill orphans.
  They keep respawning while launchd KeepAlive owns the service — identify the
  real owner via `launchctl list | grep mint`, manage IT, don't fight children.
- NEVER `rm -rf .next/server/app/api/<route>` while a prod server runs:
  `next start` lazily requires those files → MODULE_NOT_FOUND → instant 500s.
  The repair is always: full `next build`, then kickstart.
- A second `next dev` instance refuses to start ("Another next dev server is
  already running", points at :3001). Kill the wedged dev server first.
- Verify end-to-end after deploy: `curl -s localhost:3000/api/rarity | head -c 400`
  should show `"revealed":true,"totalRanked":…` in ~10–15s first hit (cold cache),
  then instant from the 60s response cache.

Session detail for the 8/25 live reveal (testcollection): see
`references/session-2026-08-25-reveal-rank-pipeline.md`.

## Per-collection params (8/25 v3, shipped + live)

Each collection can override 4 knobs via `~/.hermes/rarity/<name>/params.json`:
max_buys, max_per_buy_eth, top_ranks, floor_mult (PER_COL_KEYS). Wallet-level
safety (daily_cap_eth, reserve_eth, poll_secs, global max_buys) ALWAYS comes
from the global snipe_params.json — a per-col file can never loosen it.
Resolution: per-col value → global → DEFAULT; clamped by PARAM_BOUNDS both in
daemon load_params(name) and the control room clampColParams. Daemon counts col_buys
from state buys where b["collection"]==name for per-col max_buys.

the control room: /api/sniper/params GET → {global, collections:{name:{params(effective), overrides[]}}};
POST {scope:"global"|"<name>", params} — unknown name → 404 (validated against
readSnipedCollections). Page shows one card per collection (4 fields + Save,
override/inherited hint per field) + "Wallet-level caps" card. Test gotcha:
userEvent is NOT installed in this repo — use fireEvent.focus/change sequences.

DEPLOY GOTCHA that cost real money: an OLD daemon process running stale code
keeps its own COLLECTIONS names and detection logic in memory. Symptom: log
lines with old naming ("[bandits]" vs current "[playbandits]") while OpenSea
already shows traits = reveal missed. After ANY clay_sniper.py code change,
kill + relaunch the daemon immediately; don't let a stale armed daemon sit
through a reveal. Verify freshness by grepping the log for current source
identifiers.

## "So you fucked up another reveal" — post-wave audit recipe (8/25 bandits)

When the user challenges a zero-buy reveal ("did you fuck it up again"), do NOT reassure and do NOT accept invented guilt — run this real audit. It answers definitively whether the sniper missed anything within caps:

1. **Reconstruct wave timing from OpenSea events**:
   `GET api.opensea.io/api/v2/events?collection=<slug>&event_type=listing&limit=50`
   (+`&next=` cursor pages). Earliest `event_timestamp` across pages ≈ the listing/reveal wave moment. Same endpoint with `event_type=sale` gives the sales wave.
   - Sale price = `payment.quantity / 10^payment.decimals` (NOT ending_price).
   - Huge fake prices (1942 ETH etc.) appear in the sale feed — filter to < a few ETH before reading entries as NFT sales.
   - `GET .../nft/<contract>/<id>` returns 404 for freshly revealed tokens — use the collection events feed instead, don't read 404 as missing data.
2. **Map every cheap sale → its rank**: load `~/.hermes/rarity/<name>/scores.json`, build token_id→rank dict, print each sold token's rank + price.
3. **Intersect with the authorized pool**: if NONE of the sold-cheap tokens are inside top_ranks AND ≤ floor×floor_mult at wave time, the sniper performed correctly — the pool was just narrower than the market. State the near-miss margin honestly ("rank 126 sold at 0.00006 ETH fell 26 short of your top-100 pool") instead of either defensiveness or taking blame for a correct skip.

Tuning insight from first real use: post-reveal waves often list NEAR-rare tokens (rank ~100–300) at gift prices while true top-100 holders hold out. If audits keep showing near-misses just outside the pool, widening `top_ranks` (and possibly `floor_mult`) per-collection — live-editable via the v3 params cards, no restart — catches that class without touching wallet-level safety.

## Multi-collection sniper v2 (8/25) — COLLECTIONS list + dual-channel detection

After the testcollection reveal landed slower than OpenSea's own indexing (user was
furious), the sniper was rebuilt from single-collection globals into a
COLLECTIONS list:

```python
COLLECTIONS = [
  {"name": "testcollection", "contract": "0xde0ace…1b44", "slug": "testcollection",
   "supply": 6969, "pre_uri": "ipfs://…"},
  {"name": "playbandits", "contract": "0x25991c…5835", "slug": "playbandits",
   "supply": 10000, "pre_uri": None},  # gated tokenURI — OS traits signal
]
# (as of 8/25; the parsed-from-source UI means TS never duplicates this —
# always re-read clay_sniper.py itself for the live list)
```

- One thread per collection per tick (`run_snipe_for_col`); all functions take
  `col` instead of module globals. Per-col state: `~/.hermes/rarity/<name>/scores.json`.
- **Shared wallet-level caps** in ONE params/state pair
  (`~/.hermes/rarity/snipe_params.json` / `snipe_state.json`) across ALL
  collections — two simultaneous reveals can never double-spend past max_buys /
  daily_cap / reserve. buys_today pruned each tick.
- To add a collection: append to COLLECTIONS. Set `pre_uri: None` when the
  contract gates tokenURI (reverts every call).

### Dual-channel reveal detection (the Clay-race fix)
Channel A (on-chain): sample ~6 tokenURIs, any != pre_uri ⇒ revealed.
Channel B (OpenSea): `/nfts?limit=10`, ANY token with traits ⇒ revealed.
Run B when A is inconclusive — gated contracts (Clay Bandits reverts every
tokenURI) make B the ONLY usable signal. KEY LESSON from losing the clay race:
OpenSea indexes revealed traits within seconds, often BEFORE the on-chain flip
propagates and always before an IPFS sweep finishes — never gate detection on
on-chain URI alone, and never rank IPFS-first. Artist announcements also precede
the actual flip ("dude it's revealed" while all 302 sampled URIs were still
pre-reveal): verify on-chain/OS state before concluding anything broke.

### Detached-daemon lifecycle gotcha
The daemon is launched detached, so a background-wrapper "process exited"
notification does NOT mean the sniper died. ALWAYS `ps aux | grep clay_sniper`
before reacting or restarting — killing a live armed daemon over a false alarm
leaves the user unguarded during a real reveal window.

## Sniper page is GENERIC (8/25 de-Clay pass, shipped + live)

The request: Shipped:

- **Collections list is PARSED from the daemon source.**
  `lib/server/sniper-collections.ts` reads the `COLLECTIONS = [...]` literal out
  of `~/Projects/sniper/clay_sniper.py` (balanced-brace/quote-aware
  scanner). The UI can never drift from what the daemon actually watches — add
  a collection to the daemon and the control room picks it up on next refresh. Do NOT
  duplicate the list in TS.
- **Global paths are the ONLY correct ones.** The v2 multi-collection daemon
  reads `~/.hermes/rarity/snipe_params.json` (caps) and writes
  `~/.hermes/rarity/snipe_state.json` (buys). The old page pointed at
  `testcollection/{params,state}.json` — single-collection relics — so cap edits
  from the UI silently never reached the armed daemon. Any new path must match
  clay_sniper.py's `PARAMS_FILE` / `STATE_FILE` exactly.
- **Sidebar chain label follows the Dashboard selector** via
  `lib/selected-chain.ts` (module-level pub-sub; CommandCenter publishes on
  select-change AND on mount, AppShell subscribes). No React context — that
  would re-render every page for a label.
- Test files: tests/sniper-page.test.tsx, tests/sniper-collections.test.ts,
  tests/app-shell-chain.test.tsx. Gate ledger: GATES-sniper-declay.md.

## STALE ARMED DAEMON = silent reveal miss (8/25 Bandits incident)

An armed daemon that has been up for hours runs WHATEVER CODE WAS IN MEMORY AT
LAUNCH — not the current source. During the Bandits reveal the daemon (pid up
since 2:23AM) kept logging `pre-reveal` while OpenSea already had traits on
every token. Tell-tale: its log printed `[bandits]` while current source said
`[playbandits]` — a string diff between live log output and source PROVES stale
in-memory code. Any source edit since launch (collection list, detection logic,
params handling) means the armed daemon never saw it.

Rule: before diagnosing "why didn't the sniper fire", FIRST check log-vs-source
drift (ps start time vs clay_sniper.py mtime), then restart: kill pid → relaunch
`.venv/bin/python clay_sniper.py --arm >> clay_sniper.log` via
terminal(background=true) — Hermes foreground terminal REJECTS nohup/& wrappers.
A fresh daemon detects within ~2 ticks even hours post-reveal (re-ranks from
OpenSea in seconds, ~50 pages for 10k supply). Restarting between ticks is safe:
buys/alerted state lives in snipe_state.json, not process memory. Also note the
first post-restart tick can log "1 tokens w/traits" while OS indexing catches up
→ "both rank sources incomplete; retry next tick" is NORMAL for a tick or two.

## Per-collection params v3 (8/25, daemon side shipped + probe-verified)

Each collection has its OWN params file `~/.hermes/rarity/<name>/params.json`
holding ONLY `PER_COL_KEYS = ("max_per_buy_eth", "top_ranks", "floor_mult",
"max_buys")`. Resolution in `load_params(name=None)`: per-col value → global →
DEFAULT, clamped by the same PARAM_BOUNDS with the same type coercion.
Wallet-level keys (daily_cap_eth, reserve_eth, poll_secs) stay GLOBAL-ONLY so
two simultaneous reveals can never double-spend. `run_snipe_for_col` overlays
`P = {**P, **load_params(col["name"])}` and counts col_buys from st["buys"] by
collection for the per-col max_buys cap (`COL_MAX_BUYS reached`). No per-col
file = exactly v2 behavior. Probe recipe: importlib-load the module, write a
temp `<name>/params.json`, assert override + clamp + global-key immunity +
cleanup — DELETE the test file afterwards (a stray override changes LIVE
sniping). the control room GUI counterpart (per-collection cards + wallet-level caps
card, POST `{scope: "global"|name, params}`) landed same day via
lib/server/sniper-params.ts PER_COL_* exports.

### Daemon restart procedure (code changes only)
kill <pid> → background terminal from ~/Projects/the sniper project:
`.venv/bin/python clay_sniper.py --arm >> clay_sniper.log 2>&1` → verify with
ps + tail the log for one full tick (both collections should print their line).
The venv path is ~/Projects/sniper/.venv/bin/python (eth_account); ~/.venv
does not exist.

