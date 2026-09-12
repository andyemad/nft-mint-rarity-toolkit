---
name: rh-mint-command-center
description: Use when editing Mint Room code or running its mint engines.
---

# Mint Room (rh-mint-command-center) — repo playbook

Local Next.js 16 mint command center at `~/Projects/rh-mint-command-center`:
SeaDrop/custom mint execution via the vendored Rust engine **OSNM-Z** (`engine/osnm-z`,
MIT by zunmax), rarity scanner/gallery, fresh-wallet ops, P&L tracking. Runs under
launchd `com.patelai.rh-mint-room`; loopback-only APIs guarded by
`lib/server/loopback.ts` (`assertLoopback` / `assertSameOriginLoopback`).

Tasks delete/panel styling/live deploy: `references/tasks-delete-ui-and-live-deploy.md`.
See `references/reveal-sniper-mint-room-integration.md` for the in-app
auto-buy sniper (Clay StonKz), live-editable daemon params, the
controlled-input `0.015→15` pitfall, and loopback/route conventions.
Multi-mint path → `references/multi-mint-engine-protocol.md`.
For reconciling newer handoffs with older plans and delegating a no-broadcast completion build, see `references/unified-completion-planning.md`.
Per-collection sniper params v3 (two-tier global/per-col caps, per-col GUI cards,
importlib probe pattern) → `references/per-collection-sniper-params.md`.
Trait filter + rarity API fix + deploy gotchas 8/25 →
`references/session-2026-08-25-trait-filter-and-rarity-fix.md`.
Sold-out pre-flight forensics = §K of multi-mint-engine-protocol ref..
Opening-block SeaDrop receipt forensics, gas-field separation, failed-race diagnosis,
and evidence-based Quasarr/Mint Room settings → `references/opening-block-seadrop-forensics.md`.
Burn-to-mint drops (Pons V2: buy→approve→claim→reveal, e.g. ClawCrabs) don't
fit direct-detect's plain-mint() probe — see references/session-2026-08-25-clawcrabs-burn-to-mint-recon.md.
`.gitignore` excludes `.runtime/` (holds `.env` with secrets), node_modules, .next.
Smart Flip Tools bidding-engine parity (offers/bids/auto-lister/flip-PnL waves)
→ `references/smart-flip-parity-program.md`.

## Architecture map
- `lib/server/engine-runner.ts` — single-wallet (bot key) SeaDrop runs; spawns the
  OSNM-Z binary per run in `.runtime/engine/<run-id>/`, drives its interactive CLI via
  `lib/server/engine-protocol.ts` (feeds "Mint target:" / "Phases:" / "Token ID:" /
  "Quantity:" / "Funding:" / "Answer [y/N]:" prompts). Status transitions come from
  transcript markers ("Transaction submitted:", "Mint confirmed:").
- `lib/server/multi-runner.ts` — multi-wallet variant (see below).
- `lib/server/seadrop.ts` — CANONICAL stage states: `"scheduled" | "live" | "ended" |
  "unconfigured"`. Every UI/API/domain gate must speak THIS vocabulary — a past bug had
  the queue path expecting "future"/"active", which silently killed Queue Mint while all
  tests passed (they injected the same wrong strings). Lesson: when tests inject fake
  state strings, they must match what the producer actually emits.
- `lib/server/pnl-store.ts` + `app/api/pnl/route.ts` — append-only mission P&L records
  (0600 files, `/^\d+$/` wei validation), GET aggregates via BigInt, PATCH sets proceeds
  via parseEther. Hooked in engine-runner where a live session confirms.
- Rarity: `app/api/rarity-gallery/route.ts` is now the GENERIC scanner
  (verified live 2026-08-23): accepts `?collection=<0xCA|OpenSea collection URL>`
  (slug→contract via `lib/server/opensea-resolve.ts`), probes reveal via 8 sample
  tokenURIs, sweeps via OpenSea paged NFT list w/ traits+images primary and
  on-chain tokenURI+IPFS fallback, OpenRarity info-content ranks, disk cache
  `.runtime/rarity/<CA>/{ranked,images}.json`. PRE-REVEAL collections are not an
  error — they return status:"pre-reveal" with live best-listings sorted
  cheapest-first so browsing/sniping works before metadata flips; ranks appear on
  rescan after reveal. `/api/rarity-gallery/saved` lists persisted scans for the
  /rarity switcher; every scanned collection (even pre-reveal) self-registers into
  `.runtime/rarity/collections.json`. Scans persist per-collection on disk and
  SURVIVE restarts; the /rarity page defaults to the legacy ComboX gallery unless a
  `?collection=` param or the "Saved scans" dropdown selects one — user confusion
  ("only shows combox") was a missing-switcher problem, not data loss.
  (`app/api/rarity/route.ts` still exists but is the older hardcoded Clay StonKz
  panel endpoint — don't extend it, extend rarity-gallery.)
- **Rarity-scan verification recipe** (used 2026-08-23, all curl against the live
  loopback service): (1) REGRESSION ANCHOR — ComboX ground truth is rank 1 =
  #4820 at 45.9809 bits; any formula/gateway change must reproduce it exactly.
  (2) Exercise BOTH input forms (raw 0x CA and opensea.io/collection/<slug> URL).
  (3) For pre-reveal collections assert status=="pre-reveal" AND that listings +
  floor come back non-empty. (4) If the running launchd service already serves the
  built code (check pid matches `launchctl list`), verification needs NO rebuild or
  restart — curl directly.

## OSNM-Z multi-wallet self-funded mode (verified against source 2026-08-22)
The engine natively mints from MANY wallets — Mint Room just never wired it up before.
- Config: set `WALLETS_FILE=<manifest.json>` + `SPONSORED=false` +
  `RECIPIENT_ADDRESS=<addr>` (required even when not sponsored). Do NOT also set
  WALLET_KEY_FILE (exactly one of WALLET_KEY / WALLETS_FILE).
- Manifest: `{"version":1,"wallets":[{"private_key":"0x…","quantity":1},…]}`.
- Hard cap: `MAX_SELF_FUNDED_WALLETS = 10` (multi_wallet.rs). Quantities are per-wallet.
- Funding prompt ("Top up … press Enter to recheck; s to skip"): answer `s` to SKIP
  underfunded wallets instead of blocking — protocol passes `multi:true` for this.
- Prompt flow is the same as single-wallet; confirm_multi_mint prints configured phases
  then "Answer [y/N]:".
- Mint Room wiring: `/api/multi-mint` (GET list/id, POST action=mint|cancel) +
  multi-runner writes the manifest from `~/.hermes/secrets/fab_wallets.json`
  (registry entries `{address, keyfile}`), verifying each keyfile derives the registered
  address before it may sign. Keys never leave ~/.hermes/secrets.

## Dev-loop waves 1–3 (2026-08-22/23) — new subsystems

Commit cadence note (2026-08-23): waves now COMMIT on close — 54c6c69 closed wave 3
(market pulse + multi-wallet minting) as a single commit; earlier waves stacked
uncommitted in the tree, which forced "accept, no split possible" dispositions during
review. Commit each wave when its gate closes so reviews see only the wave's delta.

- **Snipe view (/rarity)**: three-tier sort — at/below-floor listings first by
  rank, then unlisted, then above-floor; numeric price compare with epsilon;
  "N at floor (≤ ◇ X, this page)" badge is page-local.
- **Supply watch**: `lib/server/supply-watch.ts` + `/api/supply-watch` —
  totalSupply/maxSupply selectors 0x18160ddd / 0xd5abeb01 (maxTotalSupply
  fallback 0x2ab4d052); persists `.runtime/supply-watch/<CA>.json`; values
  clamped to Number.MAX_SAFE_INTEGER. UI = panel 08 "Rug detector".
- **ERC20-paid activity**: pure decoder `lib/server/erc20-sales.ts`
  (`detectErc20Sales(receipt, {knownNft})`, Detection =
  {txHash,nftContract,tokenId,erc20,amountWei:bigint,kind}) → live layer
  `lib/server/receipt-scan.ts` + `/api/erc20-sales` (getLogs collection-filtered,
  group by txHash, batched receipts ~10/wave, PER-RECEIPT degradation, decimals()
  per ERC20 cached → `erc20Decimals` in payload). UI = panel 09 PaidPanel.
  Payment-token grouping (2026-08-23): `KNOWN_TOKENS` map at bottom of
  erc20-sales.ts maps lowercase token address → display symbol (CHG so far);
  PaidPanel imports it client-side and groups sales case-insensitively by erc20
  address. Contract: group header = `<label> · N sale(s) · ◇ <sum>` with
  `data-testid="group-header"`, sums are EXACT BigInt string adds formatted at the
  group's max known decimals (all-null decimals → honest `<sum> raw`), order =
  descending count then alphabetical label. Rows inside a group drop the
  per-row token suffix (the header carries the token).
- **Market pulse**: `lib/server/sale-buckets.ts` + `/api/sale-buckets` —
  per-minute ETH-sale buckets (receipt.status 0x1 AND tx.value>0), timestamps
  via eth_getBlockByNumber cached per block, ≤6 collections fan-out, wei as
  decimal strings. UI = panel 10 MarketPulsePanel with Sparkline.
- **Pulse store + firehose (wave 4, 2026-08-23)**: `lib/server/pulse-store.ts`
  persists every sale-buckets scan to `.runtime/pulse/<lowered-CA>.json`
  (atomic tmp+rename, history capped at 200, oldest dropped); route response
  gains `firstPaidActivity[]` — a collection is flagged when its new scan has
  sales AND no prior stored entry did (panel 10 renders a ★ badge,
  role=status). Persistence failures surface as `persistWarnings[]` without
  breaking the scan response. `SaleBucketSeries` now carries
  `scannedBlocks/fromBlock/toBlock` so the store can log the window.
  `lib/server/firehose.ts` + `/api/firehose` merges ≤6 series into one
  chronological stream: same-minute buckets from different collections are
  SUMMED into one event (count added, bigint volumes added exactly), totals
  across collections via BigInt reduce. UI = panel 11 FirehosePanel with
  deterministic per-collection color dots (hash of address → palette index).
- **Market watch (2026-08-23)**: `lib/server/market-watch.ts` +
  `/api/market-watch` — per-collection paid-mint observation ledger.
  `recordObservation(collection, {totalSales, hasPaidMint})` →
  `{address, observation, firstPaidMintEver}`; persists
  `.runtime/market-watch/<lowercased-CA>.json` as `{address, registeredAt,
  observations[]}`, capped at MARKET_WATCH_CAP=200 (oldest shifted off);
  best-effort persistence (write failure still returns result).
  `firstPaidMintEver = hasPaidMint && no prior stored observation had one`.
  `listWatched()` → `{watched:[{address,registeredAt,latest}], errors}` —
  corrupt files skipped with error notes, never thrown; missing dir → empty.
  Route: GET returns the list, POST validates collection regex + numeric/
  boolean summary with honest 400s, loopback guard on both verbs.
- **Wave ledgers on disk**: GATES.md / GATES-wave2.md / GATES-wave3.md +
  docs/plans/2026-08-22-devloop-wave{1,2,3}.md record acceptance evidence and
  review dispositions. Reviewer verdicts were FIX-FIRST twice; both MAJORs
  (spec-vs-code ordering mismatch; USDG 18-decimal assumption) were real.

## Wave 4 (2026-08-23) — process change: parent-direct implementation

Wave 4 (pulse-store + firehose) was implemented DIRECTLY by the parent instead
of fanning out subagents, and it was the smoothest wave of the loop: no sibling
edit collisions, no timeout residue to triage, no leaf re-dispatch. When the
wave is small (≤4 new files, one domain), skip delegation entirely — the
fan-out overhead (briefs, collision warnings, timeout triage) exceeds the
parallelism win. Keep fan-out for genuinely independent multi-domain slices.
The wave-3 live-probe lesson was applied as a gate: after `npm run check`
passed, the dev server was started and BOTH new endpoints were curl'd for real
(degraded:false + pulse file verified on disk with correct entry shape) before
closing the wave ledger. Live probe of every RPC-touching path is now part of
wave closure, not optional.

## Waves 5–6 (2026-08-23) — deals, CHG watch, UX overhaul

- **Deal scanner**: `lib/server/deal-scan.ts` + `/api/deals` — pure `findDeals(ranks,
  listings, {topN=50, threshold=0.8})` flags top-N-ranked tokens listed below
  reference-floor × threshold, exact bigint math (`priceWei*1000n < floorWei*cutoff`),
  discountPct sorted desc. `parseRanksFromScores` accepts 4 defensive scores shapes
  ({tokenId:{score,rank?}}, bare number maps, {tokens:…} wrapper, arrays); never
  invents ranks. **Floor semantics matter**: the original "floor = min over ALL
  listings" is mathematically unsatisfiable (no price undercuts a minimum that
  includes itself → deals always []). Correct definition: reference floor =
  cheapest UNRANKED listing (background stock), fallback global min when every
  listing is ranked. A rank-1 token near common-stock price IS the signal.
- **CHG-fill watch**: `lib/server/chg-watch.ts` + route (18 tests).
- **UX overhaul (Emad's screenshot feedback)**: right rail grouped with labeled
  section heads (`.sideHead` CSS class in CommandCenter.module.css) — TRACK /
  MARKET / TOOLS; panels renumbered sequentially in DOM order.
  `components/MultiMintPanel.tsx` mounts COLLAPSED on the main page under the
  queues block inside `<details><summary>Multi-wallet mint (advanced)</summary>`
  so multi-wallet minting never requires deciphering /wallets. Wallets page has a
  plain-language 4-step explainer; live button label says "(spends gas)".
  **2026-08-24 sidebar unification (FINAL):** right `<aside>` DELETED — every
  functional panel (Watchlist, Paid, MarketPulse, Firehose, Rug, Degen) promoted
  to its own Market-section sidebar page; static info cards → Settings "Safety"
  tab. Dashboard keeps only mint flow + queues + multi-wallet + advanced panels.
  Shell owns ALL cross-page nav; CommandCenter contributes no `<nav>`. Don't
  re-add ANY right rail; tests/dashboard-unification.test.tsx guards one left
  nav + rail-free page.
- Wave ledgers: GATES-wave4.md / GATES-wave5.md +
  docs/plans/2026-08-{22,23}-devloop-wave*.md.

## Quasarr parity program (2026-08-23 →)

Emad bought Quasarr Desktop (field-tested NFT mint bot, quasarr.xyz, v1.3.4) and wants
Mint Room at 100% parity-or-better. Consolidated plan:
`docs/plans/2026-08-23_quasarr-parity-consolidation.md` (workspace task #27).
Waves 7–15: task modules (manual ABI / OpenSea slug / merkle allowlist / 1-tx
contract-minter batch), simulation dry-runs, revert decoding, gas strategy, speed-up/spam,
trigger-on-mempool, disperse/collect fund ops, NFT scan, RPC failover/proxies.
Part 0 (close-out of the 8/23 gateway crash): queue-vocab fix VERIFIED (11/11 tests),
mfers watcher armed — remaining step is ONE commit of the ~30-file working tree
(waves 5-6 + prod fixes, gate already green) after an `npm run check` re-run.

Full recon — feature map, live SQLite schema, binary extraction recipe, app state:
`references/quasarr-recon.md`. UI extraction (sidebar/pages/dialogs from decompiled
Avalonia views + the read-only research-leaf pattern): `references/quasarr-ui-extraction.md`.

**Execution behavior spec (2026-08-23, waves 7–15 prerequisite reading):**
`docs/research/quasarr-parity-spec.md` (192 lines) — behavior-only paraphrase from the
decompiled C# v1.3.4 (`/tmp/quasarr-source`), every claim cited to `File.cs#Member`,
clean-room compliant. §1 execution core (fee model, speed-up, nonce recovery, broadcast,
spam rounds, receipts, statuses), §2 modules (OpenSea / GenericSigFlow / merkle claims),
§3 trigger engine config surface, §4 RPC ops + native status-code space, §5 TS-port
gotchas. Headline constants (full detail in the spec): replacement bump
`proposed*1000 >= current*1125` validated on BOTH fee fields (BigInt math, no floats);
sim-path buffer ×112/100 ceil with runtime-signing fallback when buffered >1,500,000,
runtime path buffers ×110/100; unspecified gas defaults 350k; EIP-7825 chains
{1, 17000, 560048, 11155111} hard-cap 16M gas, others 30M; broadcast = up to 3
immediate retries, `"already known"/"already imported"/"known transaction"` ⇒ treated
as SUCCESS with locally computed keccak; after attempt 3 transient failures convert to
success-with-hash UNLESS every endpoint error is definitely-unsubmitted (http 429
variants, too many requests, rate limit, connection refused, network unreachable,
name resolution, dns error); consumed-nonce markers {"nonce too low", "nonce has
already been used", "replacement transaction underpriced"} trigger an exact-hash
presence probe (2 s over failover URLs) BEFORE any re-sign — ambiguous probe result
must REFUSE to re-sign (duplicate-mint guard); receipt tracking polls at 2 s with
600 s deadline; spam round timeout `min(120_000 + (n−1)·normalizedDelayMs, 300_000)`,
pending-age cap 300 s, receipt poll 200 ms, unresolved/dropped beats exhaustion and
never regenerates; auto-gas refresh failure fails the task (NO stale-price fallback);
retryable native codes {-504,-503,-502,-429,-408,-103,-101,-100} ∪ entire 5xx range;
TaskStatus enum = Ready, Preparing, Simulating, Scheduled, Executing, Completed,
Failed, Cancelled, Watching; dry-run skips terminate as Cancelled. Upstream has NO
revert/custom-error selector decoder — revert surface is RPC error text, receipt
RevertReason, or literal "Transaction Reverted"; building one is net-new work here.

- **Clean-room rule:** mirror BEHAVIOR only (schemas/flows from strings + DB + docs);
  never decompile-copy Quasarr code, assets, or branding.
- **Safety invariants override parity pressure:** keys stay in ~/.hermes/secrets (never
  in-app DB), loopback guards stay, per-run max-spend stays, live contract deploys need
  Emad's explicit yes.
- **Workflow lesson:** when Emad drops a large new workstream mid-session, he wants the
  consolidated PLAN first ("let's consolidate all the work into a plan first" → "perfect")
  before any execution — write the plan, get his go, then run waves via dev loop.

## Waves 11–14 (2026-08-24) — trigger/spam, fund ops, nft scan, RPC plumbing, calldata gap

Committed b1d0a4b (W11), 9ea92b9 (W12), 60c84c1 (W13), 0593ad6 (W14), eff5c92 (W14 tail).
- **Wave 11**: `lib/server/trigger-watch.ts` (pure `matchesTrigger`, `selectorBytes` = id(sig).slice(0,10), `watchTrigger` fire-once/dedupe/timeout/kill over injectable `PendingTxSource`; `createHttpFilterSource` = eth_newFilter/eth_getFilterChanges best-effort RH) + `lib/server/spam-runner.ts` (bumpFee ceil(fee×1125/1000) ≥12.5%, validateReplacement exact §1.2 order+messages, planSpamAttempts, roundTimeoutMs min(120000+(n−1)·delay,300000), runSpam stop-safely on unresolved / fresh-nonce regeneration) + `/api/trigger` rehearse-only (register/dry-run/remove, maxSpendWei required, enabled:false). trigger-watch did NOT import from a shared trigger-config — store keeps a local structural `TriggerConfig`.
- **Wave 12**: `lib/server/fund-ops.ts` (buildDispersePlan/buildCollectPlan exact-BigInt, rehearsed:true) + `fund-op-store.ts` (history log) + `/api/fund-ops` rehearse-only. **Real collector takes `totalSourceBalancesWei` as `Record<addr,wei>`, NOT a string.**
- **Wave 13**: `lib/server/nft-scan.ts` (scanNftHoldings 721 via tokenOfOwnerByIndex `0x2f745c59`, 1155 fallback balance-only, address right-aligned in 32-byte word — `"0x"+"00".repeat(12)+addr.slice(2)`) + `mint-history-store.ts` + `/api/nft-scan` (scan + history wired; transfer-plan honest 503).
- **Wave 14**: `lib/server/rpc-failover.ts` (sequential multi-endpoint failover per spec §4.1, per-endpoint min-spacing 1000/rps rate limit, ETH_MINTS_ENDPOINTS=[eth.drpc.org,1rpc.io/eth], RH single) + `proxy-pool.ts` (PROXY_URLS env rotator). L3 Quasarr-app RPC fix left external (diagnosing Quasarr's own endpoint hit Wi-Fi split-proxy 127.0.0.1:8887 — separate, outside repo).
- **Gap fix eff5c92**: tasks POST with module:"merkle" + `moduleParamsJson` (no rawData/selector) used to 400 "task has no calldata source". Now `lib/server/tasks-calldata.ts` `resolveTaskCalldata` derives merkle claim calldata via `buildClaimCalldata` (per-token price = valueWei/qty fallback), names the engine path for opensea, direct/manual unchanged; wired into /api/tasks. `MintTaskModel` gained `moduleParamsJson?: string`.
- Full gate at close: 691 tests, tsc+eslint clean, build ok, launchd restarted, loopback live-probes green on every new route.
- LARGE PITFALL (injected-deps routes built while sibling libs don't exist yet): the parent MUST wire the real modules in as the route's *defaults* at integration (e.g. `deps.scanNftHoldings ?? realScanNftHoldings`), AND then the leaf's stale "not wired -> 503" route test FAILS (the real module now runs instead of 503) — rewrite that test to assert the wired fallback with an input that fails validation BEFORE any network (e.g. an invalid address) so it proves wiring without a live call. Also beware `as` casts hiding arg-shape mismatches (collect's `totalSourceBalancesWei` string-vs-Record) — grep the wired args against the real planner signature.
- MINOR: an append-N-of-bigger-than-cap store test (2005 appends, each serializing a growing array) is O(n²) and times out under full-suite parallel load though passing solo — give that it() an explicit `, 20_000` timeout.

### Waves 15a/b — live-executor core + consumers (2026-08-24, commits 5228664 + e6b1fb7)
- **`lib/server/signer.ts` is THE single live-spend choke point.** `executeLive(params, deps)` enforces in order: kill switch (armKillSwitch, checked before ANY work + pre-broadcast) -> authorization gate FIRST (MINT_ROOM_LIVE=1 OR bounded `armLive({maxTotalWei, ttlMs})`; refuses before ever touching the key when unarmed) -> protected signer (only OPS_WALLET `0x1111…1111`, perms 0o600, address-locked) -> chain-id check -> simulate/estimateGas (gas=est×120/100) -> hard cap `maxTotalWei` -> rehearse-before-live (`markRehearsed`/`isRehearsed`) -> armed cumulative ceiling -> broadcast + receipt (sent:true w/ status -1 on timeout). `loadProtectedSigner` rejects non-file/bad-perms/non-ops key. Network touches are injectable (`SignerClient`) so the whole gate is unit-testable without a live node or real key.
- **Consumers**: `spam-executor.ts` (executeSpam: N gated sends via executeLive, calldata via resolveTaskCalldata incl. merkle, stop on first confirmed receipt), `trigger-executor.ts` (fireTrigger: one gated send per match), `/api/executor` route (arm/disarm/kill/unkill/rehearse-mark/send + status GET; bigint maxTotalWei serialized as decimal string — Response.json can't serialize bigint).
- **Live flow**: rehearse -> markRehearsed(id) -> armLive(maxTotalWei[, ttlMs]) -> send/trigger/spam. Default LOCKED: an unarmed send returns "Live sends are disabled (kill switch engaged)." — verified live (kill persisted, unkill cleared). Keys never leave ~/.hermes/secrets.
- Gates: 47 new tests (signer 15, spam 6, trigger, executor-route 21); full suite 738; tsc/eslint clean; build ok; /api/executor live-probed.
- **Audit loop (38e44a0, closes the executor):** `spam-executor.recordWin` and `trigger-executor.recordWin` append a mint-history `completed` record when `executeLive` returns a CONFIRMED send (`ok && status===1`) — group `${module}:${contract}` (spam) / `trigger:${to}` (trigger), valueWei carried, txHash set. Both take an injectable `appendHistory` dep defaulting to the real mint-history-store and are best-effort (try/catch so a failed audit never breaks the run). PIT: confirmed-send tests MUST inject `appendHistory: vi.fn().mockResolvedValue(undefined)` — otherwise they write REAL records to `~/.hermes/rh-mint/logs/mint-history.json` during the test. If stray records ever appear there, clear them with a `python3` snippet (`records:[]`) before committing.

### Waves 7–9 status (2026-08-23)
- DONE: wave 7 core committed (7362aa7: task-modules, simulate, error decode;
  `.runtime/tasks.json` store + always-rehearse `/api/tasks`). Wave 8 committed
  (50f69fc): `lib/server/modules/opensea.ts` (fetchCollectionPlan / selectStage /
  buildTaskFromStage / assertPriceWithinExpected — 21/21 green),
  `/api/opensea-plan` loopback GET proxy (`?input=` URL|os:slug|bare slug|address →
  `{plan}`, honest 400s carrying the module message verbatim), AdvancedTaskPanel
  dual-mode (Manual | OpenSea: paste input → Fetch → stages list + stage select +
  qty + expected-price → Rehearse). Ledgers/tests: GATES-wave{7,8}.md,
  tests/modules-{opensea,merkle}.test.ts, tests/opensea-plan-route.test.ts,
  tests/advanced-task-panel-opensea.test.tsx.
- DONE wave 9 L1: `lib/server/modules/merkle.ts` — detectClaimConditions (eth_call
  probe ladder across getter shapes, honest nulls + attempted-selector trail incl.
  decoded revert text via error-decode), buildClaimCalldata (Thirdweb drop tuple,
  entry-price sentinel MaxUint256 / empty ⇒ condition-level terms per spec §2.3,
  quantityLimitPerWallet defaults MaxUint256), resolveEffectiveTerms,
  isNativeCurrency (zero addr / EEEE / any all-e-nibble alias, case-insensitive),
  verifyMerkleProof (sorted-pair double hash), WalletNotEligibleError(-70) /
  NoActiveConditionsError(-72) mirrors. 17/17 green; ledger GATES-wave9.md.
- DONE wave 9 L2 (2026-08-23, subagent leaf scope; COMMITTED f646d32):
  `/api/merkle-plan` route + AdvancedTaskPanel Merkle mode + tests. Green: 5
  route + 9 panel tests, opensea/manual panel regression 10/10,
  `npx tsc --noEmit` clean.
  - `app/api/merkle-plan/route.ts` — thin proxy like /api/opensea-plan:
    loopback GET `?contract=0x…`; missing/blank/non-address → 400
    `"contract query parameter required"` (shape check `^0x[0-9a-fA-F]{40}$`);
    success → `{ summary }` from detectClaimConditions(contract) with DEFAULT
    deps (real RPC); module throws → 400 verbatim.
  - Panel third mode (`mode-merkle`, `mk-*` testids): fetch → summary line
    (shortHex root · condition #N · price via NEW BigInt display mirror
    weiToEthStringOrNull · native-vs-ERC20 currency), receiver input (0x-40
    validated), proof JSON textarea with LIVE client-side validation
    (bytes32-per-entry regex, offending entries named; `[]` allowed with
    warning "⚠ no proof — will fail on allowlisted drops"), qty + expected ETH
    prefilled from fetched priceWei. Rehearse POSTs module:"merkle" +
    moduleParamsJson {module_type:"merkle_drop",receiver,quantity,proof} +
    claim selector string for DISPLAY only; valueWei = expected×qty×1e18
    exact BigInt or "0"; NO abiArgs/rawData.
  - Tests: tests/merkle-plan-route.test.ts,
    tests/advanced-task-panel-merkle.test.tsx (queue-based fetch mock routing
    /api/merkle-plan vs /api/tasks).
  - Full contracts + testid map: `references/wave9-merkle-integration.md`.
- **Reveal Sniper module (2026-08-24, live):** `/sniper` page + `/api/sniper/status`
  + `/api/sniper/params` + `lib/server/sniper.ts`. Mirrors the armed Clay StonKz
  reveal-auto-buy daemon (bunker-snipe/clay_sniper.py) — status (pid, balance, buys
  fired), guardrails table, editable params, buy history. READ-ONLY surface:
  reflects the daemon's state file `~/.hermes/rarity/claystonkz/snipe_state.json`,
  never writes/broadcasts. Notable finds: the RH chain Seaport buy path finally
  works (the old 49/49-revert belief was HTTP400s from fulfillment_data, not
  encoding); ETH-vs-USDG decimals gate which listings are auto-buy targets; live-
  editable params read fresh each tick (no restart). Full detail incl. the
  clamp-test-poisoned-live-config pitfall: `references/wave-sniper-integration.md`.
- (OPEN GAP re calldata-source 400s: CLOSED by eff5c92 — see Gap fix above.)
- Detail (contracts, ambiguity dispositions, test skeletons):
  `references/wave8-opensea-integration.md`; merkle contract + app-shell/E2E
  interaction contract: `references/wave9-uiwaveA-integration.md`.
- Wave 9 CLOSED: commit f646d32 (merkle module + route + panel mode + tests +
  GATES-wave9.md ledger), full gate 44 files / 331 tests, tsc+eslint clean,
  build ok, E2E PASS. Wave-9 scoped suites: modules-merkle 17/17,
  merkle-plan-route 5/5, panel-merkle 9/9.
- Wave 10 L1 DONE (2026-08-23): `lib/server/modules/contract-minter.ts` —
  formula-exact port of decompiled ContractMinterBatchPlanner.cs:
  planBatch greedy partitioning (one mint per wallet per outer tx), EIP-150
  gross-up, EIP-7623 floor, memory-expansion model, margin =
  max(safetyReserve, consumptionSum/10), uniform/templated/heterogeneous
  wire-form analysis with verbatim C# exclusion reasons, DEFAULT_OVERHEADS +
  FALLBACK_CAPS exports. 23/23 green (tests/modules-contract-minter.test.ts),
  tsc clean. Impl+tests written by PARENT after the dispatched leaf produced
  zero files (see salvage pitfall). Formula sheet + port status:
 `references/wave10-contract-minter-planner.md`. Wave 10 CLOSED: commit 78042fb —
 `/api/contract-minter-plan` (loopback POST, valueWei as decimal-string → BigInt,
 returns partitions with stringified bigints) + AdvancedTaskPanel fourth mode
 `mode-batch` (jobs-JSON textarea → per-partition lines
 "Partition N: K jobs · gas ≈ <gas> · wire: <mode>", excluded list, hint
 "preview only — execution not wired"; NO rehearse — execution rides the live
 wave). Suites: contract-minter-plan-route 6/6, advanced-task-panel-batch 8/8,
 panel regressions 19/19.
- **Trigger watcher (wave 11, 2026-08-24, COMMITTED b1d0a4b):** `lib/server/trigger-watch.ts`
  + `tests/trigger-watch.test.ts` — Quasarr parity §1.13/§3 pending-tx watch. Pure
  `matchesTrigger(tx, cfg)` (AND of to==contract case-insensitive, input first-4-byte
  selector, optional case-insensitive senderFilter) + `selectorBytes(sigOrRaw)` +
  `parseValueWei`; `watchTrigger(cfg, {source,sleep,now,onMatch,abortSignal})` polls,
  dedupes by hash within a session, returns `{status:'matched|cancelled|timeout',
  matches}` — a source throw = one empty cycle and keeps looping; 3 consecutive
  throws OR max-age (default 300s) elapsed → `{timeout}`; never throws across its
  boundary on source failure. Default `source` is `createHttpFilterSource` (best-effort
  `eth_newFilter{address}` → `eth_getFilterChanges` → per-hash
  `eth_getTransactionByHash`, each call time-bound ~8s, degrades to empty batches on
  filter-unsupported nodes, never throws). Tests drive `watchTrigger` via a scripted
  injected source (arrays + thrown Errors), never real RPC. Method-selector recipe:
 ethers `id(sig).slice(0, 10).toLowerCase()` gives the keccak first-4-bytes —
 `mint(uint256)` → `0xa0712d68`; raw `^0x[0-9a-fA-F]{8}$` passes through lowercased.
 - **Spam/speed-up runner (§1.7 parity leaf, 2026-08-24):**
 `lib/server/spam-runner.ts` + `tests/spam-runner.test.ts` (21/21 green, tsc
 clean). §1.2 replacement policy + §1.7 spam rounds: `bumpFee` = ceil(fee×
 1125/1000) BigInt (0→0, always ≥12.5%); `validateReplacement` returns §1.2
 reason strings, both fee fields must clear `proposed·1000 >= current·1125`
 jointly; `planSpamAttempts` expands task.spam → count escalating fee steps,
 manual overrides verbatim when BOTH set else auto-from-baseFee
 (multiplierBips/10000, priority floored 1 gwei, maxFee≥maxPri re-asserted on
 later steps); `roundTimeoutMs` = min(120000+(n−1)·delay, 300000);
 `runSpam` = one nonce per round (`freshNonce(attempt)`) reused across same-
 nonce fee-step retries (speed-up), poll receipts every 200ms bounded by round
 timeout + 300s pending cap, **stop-safely (no regeneration)** on pending/
 unknown/dropped at deadline, regenerate fresh nonce ONLY on clean all-failed
 rounds, exhausted → "Spam batch exhausted. No transactions sent.". Contract
 reality: `runSpam(task, deps)` signature carries NO live base fee, so it
 requires manual fee overrides (or optional `deps.baseFeeWei`) and throws a
 clear error otherwise — never plans nonsense gas. Fee math is pure BigInt; the
 runner never signs (all IO via injected submit/pollReceipt/freshNonce deps).

 ### UI parity wave A (2026-08-23, commits 78042fb + 0d9c506)
 - App shell LIVE: `components/AppShell.tsx` (+ module css) wraps `app/layout.tsx`.
 Fixed left sidebar (~232px): brand panel "MINT ROOM", sections CORE (Dashboard /,
 Tasks SOON, Activity SOON) / MODULES (Rarity /rarity, OpenSea Checker SOON,
 NFT Manager SOON) / MONEY (Transfers SOON, Contract Minter SOON) / SYSTEM
 (Wallets /wallets, Settings SOON, Tools SOON). SOON items are
 `<span role="link" aria-disabled="true">`; live items are Next <Link> with
 `aria-current="page"` via usePathname. Top bar: page title from pathname map +
 green "local only" loopback indicator. Mobile <900px: sidebar collapses to a
 horizontal scroll strip (pure CSS, same DOM). Tests: tests/app-shell.test.tsx
 (7/7; vi.mock next/navigation usePathname).
 - E2E fix (0d9c506): sticky topbar intercepted Playwright clicks — see pitfalls.
 - Next UI wave: Tasks page (groups + table + status pills per
 references/quasarr-ui-extraction.md), absorbing AdvancedTaskPanel modes into an
 stub routes marked "SOON" until each page wave lands).

 ### UI wave B — Tasks page (2026-08-23, COMMITTED 80d1ead)
 - LIVE: `app/tasks/page.tsx` + `components/TasksView.tsx` (+ module css);
  AppShell `/tasks` flipped SOON→live. The test flip is ONE line — add "/tasks"
  to LIVE_HREFS in tests/app-shell.test.tsx (SOON_HREFS derives by filtering
  LIVE_HREFS, so nothing else moves) plus one link assertion. Full gate at
  close: 49 files / 387 tests green, tsc clean, eslint 0 errors, build ok,
  E2E PASS desktop + mobile.
 - HONEST DERIVATIONS drive the whole view (documented in the component header):
  `.runtime/tasks.json` rows are bare MintTaskModels + id/createdAt — NO
  status/wallet/error/txHash persisted — and the route is GET-list +
  POST-create-rehearse ONLY. Task Groups derive client-side by
  `${module}:${contractAddress}`; display status derives as persisted-`status`
  (§1.10 vocabulary) → else lastError→failed → else future scheduledForMs→
  scheduled → else ready (the rehearse-only default). When executor waves start
  persisting `status`, the pills light up with zero UI change.
 - Parity pressure did NOT invent endpoints: no Rehearse-selected button (rendered
  hint "Rehearsal happens at creation") and no Delete button until /api/tasks
  grows them; Tx-hash column renders "—" until a real hash exists.
 - Add Task toolbar button toggles a collapsible "New task" section mounting the
  existing `<AdvancedTaskPanel />` unchanged (no props; testid
  advanced-task-panel) — the absorption path for all four panel modes.
 - Display semantics: Value column in ETH (exact BigInt weiToEthStringOrNull),
  Gas column fees in GWEI (weiToGweiString) — a wei→ETH fee string like
  0.00000003 is unreadable; gwei-for-fees / ETH-for-values is the convention.
 - Next UI waves: Activity log, Wallets parity pass, Transfers (Disperse/Collect),
  then Settings/Tools.

 ### UI wave C — Tools page (2026-08-24, subagent leaf)
 - LIVE: `app/tools/page.tsx` + `components/ToolsView.tsx` (+ module css);
  AppShell `/tools` flipped SOON→live (+ LIVE_HREFS in tests/app-shell.test.tsx,
  same one-line flip pattern as wave B). Card grid of three ToolDefinitions;
  click swaps grid → tool host ("← All tools" back button, `tool-title` testid).
  OpenSea Checker = read-only schedule lookup over `/api/opensea-plan?input=`
  (NOTE: real param is `input`, NOT `slug`); Gas Calculator =
  `components/GasCalculator.tsx` (4 inputs, live BigInt outputs, no submit);
  Contract Minter = honest POINTER card linking to AdvancedTaskPanel Batch mode
  on /tasks (no duplicated textarea→plan flow, no fake buttons).
 - **Brief-vector trap**: the leaf brief's worked example said 21000 gas ×
  30 gwei → "0.63 ETH". Wrong by 1000×: it is 630000000000000 wei =
  0.00063 ETH (~$1.50 — sanity-check magnitude). The wei figure was right, the
  ETH label wrong; tests assert both the exact wei-derived string AND a scaled
  21M-gas-limit vector for a clean "0.63" display.
 - Gate: tools-view 11/11 + app-shell 7/7, tsc clean, eslint 0 problems.

 ## Pitfalls
- **Live lock:** `startEngineSession`/`startMultiSession` require
  `MINT_ROOM_LIVE=1` env OR `uiAuthorized=true` for live mode. Rehearsals pass
  uiAuthorized freely — rehearsals must never sign (protocol answers "n").
- **Stale launchd server breaks the UI silently (hit 2026-08-24, Emad-visible)**:
  `next start` snapshots the static-asset manifest AT BOOT. Chunks written to
  `.next/static/` by a later build 404 from the still-running server EVEN THOUGH
  the files exist on disk (verified: CSS/JS mix of 200s and 404s correlating with
  boot-vs-build time, not mtime). Symptom: Emad opens Mint Room after a wave
  commit and reports "UI isn't showing up nicely" — unstyled/broken render.
  Protocol: after ANY `npm run build`, run
  `launchctl kickstart -k gui/$(id -u)/com.patelai.rh-mint-room`, then curl one
  fresh asset path for 200 BEFORE telling him anything is visible. His browser
  may also need one hard refresh (Cmd+Shift+R). Restart wipes in-memory state;
  scans/sessions persist to `.runtime/`, so prefer reading disk
  (`loadPersistedScan`) after any launchd kickstart.
- **EMAD HARD RULE — there must be NO right-rail "side" panels (told repeatedly,
  8/24).** Every functional feature lives in the LEFT sidebar as its own page under
  a nav section; \"integrate with the sidebar / not separate\" means PROMOTE the
  panels to pages, then DELETE the rail — never re-label it, never leave panels
  stacked on the Dashboard. When adding any emitter/scanner/monitor, put it behind
  its own route and sidebar entry, not a Dashboard right panel.
- **Promoting a dashboard panel to its own page (pattern, 8/24):** keep the panel
  component, host it in a `"use client"` page with its own active-collection input
  (components/MarketPanels.tsx `useMarketCollection` returns `{collection,
  setCollection, input}`), add a "Market" nav section + LIVE_HREFS, deep-link the
  active contract via `/?collection=0x…` which CommandCenter reads through
  `useSearchParams` on mount (guarded: only accept `/^0x[0-9a-fA-F]{40}$/`), and
  DELETE the rail JSX PLUS the now-dead state/fetch-effects/types it referenced.
  Caution: the fuzzy patch matcher can over-remove ADJACENT unrelated type lines
  (it swallowed the still-used `Stats` type when deleting the dead panel types) —
  re-read the file header after a multi-line removal and restore any over-deleted
  declarations. Keep `type Stats` etc. even if the parser said it matched.
- **`useSearchParams` added to a client component breaks EVERY test that renders
  it** unless that test's `vi.mock("next/navigation")` also exports
  `useSearchParams: () => null` (plus usePathname). Check every
  CommandCenter/AppShell-rendering test file (tests/ui.test.tsx, dashboard-unification,
  app-shell) and add it; a missing export makes CommandCenter throw during render and
  fails unrelated it()s. When adding a nav section, make the app-shell test's
  EXPECTED_HREFS / item-count DERIVE from NAV_SECTIONS
  (`NAV_SECTIONS.flatMap(s => s.items.map(i => i.href))`) instead of hardcoding a
  count, add the new hrefs to LIVE_HREFS, and extend the headings-array assertion.
- **Verify chain before claiming done:** `npm test` (vitest, jsdom) AND
  `npx tsc --noEmit` (vitest is transpile-only) AND `npm run build`, then hit the live
  loopback API with curl (include `-H 'Origin: http://127.0.0.1:3000'` for POST/PATCH —
  otherwise you get SAME_ORIGIN_ONLY, which is itself a good negative test).
- **Pre-existing unrelated failures happen** (e.g. sale-buckets tests from parallel
  waves): scope your vitest run to your own test files first, and check `git status` —
  parallel dev-loop waves drop GATES*.md plans and disjoint features into the tree.
  Never commit files you didn't author; `git add` explicit paths only.
- **Delegated agents time out but may finish their edits first**: before re-dispatching,
  read `~/.hermes/cache/delegation/live/<id>/task-N.log` tail + `git status`. A second
  agent re-implementing completed work causes conflicts. Give children exact file maps
  to avoid exploration burn (600s wall).
- **Testing-library `getByText` does not match across element boundaries**: if a
  rendered string spans nested elements (e.g. `<label> · N sales · <span>sum</span>`
  inside one header), `getByText(/full string/)` fails even though the text is
  visibly there — the DOM dump looks identical to a passing case and burns a cycle.
  Assert on a stable `data-testid` with `getAllByTestId(...).map(el => el.textContent)`
  joined + regex-matched instead, or design components so testid'd containers carry
  the whole assertion surface.
- **Robinhood chain specifics**: RPC `https://rpc.mainnet.chain.robinhood.com`,
  chainId 4663, legacy type-0 txs for exact-balance sweeps (EIP-1559 envelope overhead
  pushed sweeps under intrinsic cost), getLogs ranges ≤1000 blocks.
  The arrowrpc surface is PARTIAL (verified 2026-08-23): `eth_getBlockNumber` does NOT
  exist ("does not exist/is not available") — only `eth_blockNumber` works. Any new
  scan code must use `eth_blockNumber`; a wrong method name surfaces as an honest
  degraded=true + errors[] rather than a crash, so check the errors[] text first when
  a live endpoint returns empty series.
- **`rawRpcCall` returns `payload.result` ALREADY PARSED — objects, not strings.**
  `lib/server/rpc.ts` does `response.json()` and returns `payload.result` directly.
  A helper that does `JSON.parse(raw)` on the return throws "malformed JSON response"
  on every array/object result while tests pass (mocks inject strings). Pattern:
  `parseJson<T>(raw: unknown, ...)` with `if (typeof raw !== "string") return raw as T;`
  — receipt-scan.ts already did this; sale-buckets.ts initially didn't and every live
  call degraded until fixed. When adding a new lib over rawRpcCall, copy receipt-scan's
  tolerant parseJson, and verify against the LIVE loopback endpoint (curl), not just
  vitest — mocked rpcCall deps hide this class of bug entirely.
- ERC-721 reads: totalSupply selector `0x18160ddd`, tokenURI `0xc87b56dd` + padded id;
  decode dynamic string at word offset 32+24 (length) / bytes from word 2.
- **ERC-721/1155 holdings scanner recipe (`lib/server/nft-scan.ts`, wave 13):**
  enumerate via eth_call ONLY (RH arrowrpc surface is partial; no logs needed).
  Per contract: `balanceOf(address)` `0x70a08231` → any positive value → per-token
  `tokenOfOwnerByIndex(address,uint256)` `0x2f745c59` from index 0..balance-1.
  Classification SEAM is which calls you wrap in try/catch: a HARD throw on the
  balance probe propagates to the top-level catch → `{ok:false,error}` (matching
  "a hard rpcCall throw degrades to ok:false, never throws across the boundary");
  but a per-index THROW is a per-token FAILURE — catch it individually and break,
  and if NO id was ever enumerated, a positive-balance non-enumerable contract
  collapses to ONE ERC-1155 row (`tokenId:"0"`, `balanceWei:<aggregate>`).
  A resolved-but-null/unparsable balance = treat as 0 (skip). Address word is
  RIGHT-aligned (last 20 bytes; `0x`+24 zeros+addr); index is LEFT-padded to 64
  hex. bigint-stringify tokenId/balanceWei before the response; sort contract-major
  then tokenId as BigInt asc (NOT lexicographic); cap total rows (500) to bound
  enumeration. **PIT (real, caught by test): if your word-padding helper returns
  `0x`+hex and you concatenate it after an `0x`-prefixed selector, the calldata
  has a doubled inner `0x`. `.slice(2)` the word helper at assembly. This bug is
  invisible to tsc and to a mocked balanceOf that ignores `data` — only an exact
  calldata assertion (10+64 chars, selector + right-aligned word) catches it.**
- **Canned eth_call RPC mocks: the scanner lowercases `contract` and the mock MUST
  match against LOWERCASED constants.** A mock that compares `call.to.toLowerCase()`
  to `const A = "0xAAAA…"` (uppercase) never matches → balanceOf falls through to
  0 → returns `{ok:true, holdings:[]}` and can make "zero-balance contract skipped"
  pass for the wrong reason. Compare against `A.toLowerCase()` literals (as in
  tests/nft-scan.test.ts).
- **Route testability without module mocks**: Next route handlers can take an
  optional trailing deps param (`GET(request, deps = {})`) — vitest imports the
  handler directly and passes an in-memory fs/now via that param, same DI style
  as the lib functions. Extra runtime arg is harmless to Next. This avoids
  `vi.mock` module interception entirely and keeps one deps shape end-to-end.
  market-watch route + tests are the reference implementation.
- **Call injected `now()` ONCE per record** and reuse the value for every
  timestamp in the persisted object (registeredAt AND observation.at). Calling
  it per field silently drifts timestamps when tests use a ticking fake clock,
  and produces confusing "expected …22.000Z got …21.000Z" failures.
- **Test-file shared mutable state (e.g. a module-level `tick` counter) must be
  reset in a FILE-LEVEL `beforeEach`, not inside one describe block** —
  otherwise earlier describes consume ticks and later ones assert stale
  expected timestamps. Symptom: only the tests running after another describe
  fail on timestamps; the first describe passes.
- **Don't trust your own sort expectations in list-order assertions**: when
  asserting `sorted[0]`, verify the actual lexicographic order of the fixture
  addresses — `"0x1234…"` sorts BEFORE `"0xabcdef…"` (digits < letters), so a
  "first store" assertion written by intuition points at the wrong entry and
  looks like an impl bug when it's a test bug.
- **vi.mock of the layer UNDER the unit under test is fine; vi.mock of the
  function under test needs `importOriginal` spread + `vi.mocked(...).mockResolvedValueOnce`.**
  The firehose tests mock `scanSaleBuckets` (the engine) while testing
  `buildFirehose` (the merger) — that's the right seam: pure merge logic gets
  fast deterministic fixtures without any RPC. When you need one test in the
  file to see different mock output, grab the mocked fn via
  `(await import(mod)).fn` and call `.mockResolvedValueOnce` — module-level
  factory alone can't vary per-test.
- **Extending an exported type ripples into every constructor site.** Adding
  `scannedBlocks/fromBlock/toBlock` to `SaleBucketSeries` broke both the fan-out
  `series.push(...)` AND the route that read those fields off the wrong type
  (`CollectionSaleBuckets` vs `SaleBucketSeries`). LSP diagnostics catch this
  immediately — fix all constructor sites in the same pass, and prefer widening
  the base type over duplicating field shapes across variants.
- **Poll-timer leak across unmount (waves 5–6)**: components polling via
  recursive `setTimeout` MUST clear the pending timer in a useEffect unmount
  cleanup (`stoppedRef=true; clearTimeout(timerRef)`). Symptom in tests: an
  EARLIER test's leaked timer fires DURING a later test's fetch mock, inflating
  that test's call counts by exactly one at a ~2s offset — looks like a mystery
  second poll loop, is actually cross-test leakage. Also a real UX bug (fetches
  after the panel is gone).
- **React 18 batching hides terminal UI**: a run-status box keyed on
  `busy && runId` never renders its final state because the terminal poll sets
  `setBusy(false)` in the same batch as `setStatus("rehearsed")` — active flips
  false before the box ever paints. Key persistent output boxes off a separate
  `hasRun` state, not busy.
- **Label-text collisions when mounting a new form into an existing page**:
  MultiMintPanel's "Quantity per wallet" made `getByLabelText(/quantity/i)`
  match multiple elements in ui.test.tsx. Fix in TESTS: scope ambiguous regex
  queries to exact labels (`getByLabelText("Quantity")`) when a shared page
  gains new labeled inputs.
- **Wave 5 additions (2026-08-23)**: pulse-watch registry
  (`lib/server/pulse-watch.ts` + `/api/pulse-watch`, add/remove/list watched
  collections at `.runtime/pulse/watch.json`), first-paid alert core
  (`lib/server/pulse-alert.ts` — alerts only on a collection's FIRST-ever
  paid activity; ledger `.runtime/pulse/alerts.json` prevents re-alerts;
  6 tests), cron-mode watcher `scripts/pulse_watch.mjs` (talks to local
  server, prints JSON alert lines, fail-closed exit 0), 👁 watch toggle in
  MarketPulsePanel. NOTE: the watcher is NOT yet wired into a live Hermes
  cron — approval-gate plumbing failed (see hermes-cron-approvals); script
  runs standalone and is tested.
- **Spec self-contradiction check before implementing floor/threshold math**:
  any rule of the form "compare each price against a statistic computed FROM
  those same prices" can be unsatisfiable (min-including-self). When a spec's
  worked examples and its formula disagree, trust the examples' INTENT and
  redefine the statistic so examples are reachable — then document the chosen
  semantics in code comments AND rewrite fixtures to match.
- **write_file's write-time lint is a false-positive generator for this repo**: it
  runs tsc WITHOUT the project tsconfig, so every new .ts/.tsx write reports
  `Cannot find module '@/…'` plus node_modules noise (esModuleInterop,
  PromiseWithResolvers, …). Do NOT chase these or "fix" imports that resolve fine
  under the real tsconfig paths. The gate is `npx vitest run <my files>` +
  `npx tsc --noEmit` from the repo root (exit 0 = clean; verified in wave 8).
- **Route tests: import the handler directly** (`import { GET } from "@/app/api/x/route"`),
  build requests as `new Request("http://127.0.0.1:3000…", { headers: { host:
  "127.0.0.1:3000" } })` so assertLoopback passes (non-loopback negative test =
  plain host-less Request), and vi.mock the server IO module UNDER the route.
  tests/tasks-route.test.ts and tests/opensea-plan-route.test.ts are the templates.
- **CommandCenter test stubs: stub fetch to REJECT, not return `{}`.** With
  `refreshQueues` doing `setQueues((await response.json()).queues)`, a mock that
  resolves `{ status:200 }` makes `.queues` undefined → `setQueues(undefined)` →
  the render crashes at `queues.length` in the queues block (an unhandled error
  that fails unrelated it() blocks in the same file). The proven offline-safe
  shape (mirrors ui.test.tsx) is
  `fetch: vi.fn(() => Promise.reject(new Error("no network")))` — every panel's
  catch{} swallows it and state stays at initial. Hit 2026-08-24 in
  tests/dashboard-unification.test.tsx.
- **Broad-regex absence assertions match legitimately-kept content**: asserting
  `queryByText(/track/i)` is NOT in the document fails because the retained
  "Degen **track**er" card satisfies it. For "removed this specific label"
  assertions match the exact node text (`queryByText(/^track$/i)`), not a
  substring — otherwise the kept sibling content trips the absence check.
- **Component tests hitting two endpoints: queue-based fetch mock routing on URL**
  (advanced-task-panel-opensea.test.tsx): one `fetchMock.mockImplementation(async
  input => …)` that shifts from SEPARATE response queues per endpoint substring
  (/api/opensea-plan vs /api/tasks) and THROWS on an unexpected extra call —
  order-explicit without brittle call-index assertions, and it doubles as an
  assertion that a failed plan lookup never fell through to POST /api/tasks.
- **Client components can't import lib/server modules** — when a panel needs
  server-only exact math (ethStringToWei etc.), mirror it as a local pure function
  with BigInt string math only near money (no floats) and lock parity by asserting
  exact outputs in tests ("0.04"×2 → "80000000000000000"). Same discipline for
  param shapes: JSON.stringify key ORDER is asserted against the §2.1 spec order
  so the stored moduleParamsJson stays spec-stable.
- **UI parity program (2026-08-23 →)**: Emad wants Quasarr's DESKTOP UI rebuilt as
  Mint Room's browser app — sidebar shell + per-view pages, not just engine parity.
  Extracted structure: `docs/research/quasarr-ui-parity-spec.md` (sidebar sections
  CORE/MODULES/MONEY/SYSTEM; TasksView is the core screen; Transfers =
  Disperse/Collect segments; ContractMinterManager has delegation states;
  LoginWindow NOT ported — loopback local app). Existing /, /rarity, /wallets fold
  INTO the shell; AdvancedTaskPanel modes fold into the future Tasks add-task flow.
  Wave-UI-A shell leaf dispatched (components/AppShell.tsx wrapping layout.tsx +
  stub routes marked "SOON" until each page wave lands).
- **Parallel research fan-out works well for decompiled-source recon** (2026-08-23):
  three read-only leaves (main-window chrome/sidebar, core views Tasks/Wallets/
  ActivityLog/Settings/Tools, money-flow views Disperse/Collect/ContractMinter/
  OpenSea/NFT) each returned a structured ≤160-line spec in ~9 min; parent
  consolidated into one spec file. Leaf contract that worked: read-only session
  contract ("do NOT write/create/modify files — report findings as final message"),
  facts-only with file citations, "unclear" allowed instead of speculation, one ##
  section per view with bullets. Use for source-study phases; keep implementation
  waves single-owner per file.
- **Parallel research fan-out works well for decompiled-source recon** (2026-08-23):
  three read-only leaves (main-window chrome/sidebar, core views, money-flow views)
  each returned a structured ≤160-line spec in ~9 min; parent consolidated into one
  spec file. Contract: read-only session contract ("do NOT write/create/modify files
  — report findings as final message"), facts-only with file citations, "unclear"
  allowed instead of speculation. Use for source-study phases; keep implementation
  waves single-owner. Details in `references/quasarr-ui-extraction.md`.
- When Emad redirects mid-wave ("use multiple agents", "integrate the two"), he is
  changing EXECUTION SHAPE, not the goal — re-plan the fan-out immediately and say
  what's now running in parallel rather than continuing solo.
- **Subagent timeout salvage is now routine — check before re-dispatching.**
  Roughly half of 600s-budget leaves time out, but the residue varies: sometimes
  files are complete-but-failing-tests (wave 8 opensea: parent fixed 3 real bugs +
  test-vector errors), sometimes tests exist but impl doesn't (wave 9 merkle:
  parent wrote impl against the agent-authored suite), and sometimes NOTHING was
  written at all (wave 10 contract-minter: leaf burned the whole budget hand-
  verifying formula math). ALWAYS read
  `~/.hermes/cache/delegation/live/<id>/task-0.log` tail + `ls` the leaf's target
  files + run their vitest file BEFORE deciding re-dispatch vs finish-yourself.
  Finishing in-parent is usually cheaper than a second 10-minute dispatch — and
  when you already hold full understanding of the target from your own source
  study, skip delegation entirely and write it in-parent (wave 10: parent wrote
  impl+tests directly, 23/23 green first try, ~15 min).
- **Hex-return tolerance at RPC seams**: injected rpc stubs and some real RPC
  variants return bare hex WITHOUT the 0x prefix; decoders that unconditionally
  `.slice(2)` corrupt them silently (wave 9: activeIndex decoded null because
  word("01") fixture had no 0x). Normalize at the seam:
  `const hex = s.toLowerCase().startsWith("0x") ? s.slice(2) : s`.
- **ABI address words are RIGHT-aligned** — an address occupies the LAST 20
  bytes of its 32-byte word. Decoding `word.slice(0, 40)` instead of
  `word.slice(24)` yields garbage addresses (wave 9 currency decode bug).
- **Debug-loop discipline for vitest failures**: when a failure makes no sense,
  write a THROWAWAY `tests/zz-debug*.test.ts` reproducing the exact fixture +
  router shape and console.log the intermediate values, then DELETE it before
  commit. Faster than re-reading the impl repeatedly; three debug files solved
  wave 9's merkle probe mystery in minutes.
- **Test-authoring math errors masquerade as impl bugs**: wave 8's price-guard
  failures were fixture constants with the 1e10 tolerance at the wrong digit
  position (50_000_000_010_000_001n vs correct 50_000_010_000_000_001n for
  "0.05 ETH + slack"). Before patching impl over a failing exact-value test,
  recompute the expected constant independently (`node -e` one-liner).
- **Response-stub helpers must pass string bodies through VERBATIM**: a shared
  `jsonResponse(status, body)` test helper that always `JSON.stringify`s turns an
  HTML fixture into a QUOTED JSON string (`"<html>…"`), so `.text()` hands back
  quote-wrapped garbage and scrape/parse paths silently mismatch (wave 8:
  extractContractsFromOpenSeaHtml couldn't find the slug; root cause found only via
  a throwaway debug test). Branch instead:
  `typeof body === "string" ? body : JSON.stringify(body)`.
- **Panel-test mocks of POST /api/tasks must mirror the REAL route response
  shape** (`{task:{id}, rehearsal:{ok,gasEstimate,costWei}}`). A fixture with
  only `{task}` makes the panel render its honest "saved (no rehearsal
  returned)" line, so any `/saved task-<id>/` assertion fails — looks like an
  app bug but is a fixture bug (hit in wave 9; fixed the FIXTURE, not the
  panel). Related: client-side mirrors go BOTH directions — wave 9 added
  weiToEthStringOrNull (wei→ETH display) and isNativeCurrencyClient beside
  ethStringToWeiOrNull; keep each direction parity-tested.
- **Sticky headers break Playwright auto-scroll clicks**: Playwright scrolls a
  target to viewport top, where a sticky topbar sits — click times out with
  "header subtree intercepts pointer events" (hit in UI wave A; e2e.mjs line ~29).
  Fix: `html{scroll-padding-top:<header height + margin>}` in globals.css AND keep
  overlay z-indexes low (grain overlay was z-40 over everything; content needs no
  z at all, topbar z-20 suffices). Diagnose with a throwaway playwright-core script
  using the SAME launch config as e2e.mjs (`executablePath:` Brave) — plain
  `chromium.launch()` fails on missing headless-shell binaries. Also: a long-lived
  `next start` on :3000 from Emad's own dev session serves STALE builds — run
  probes against the e2e port (4186) or verify `AppShell-module` appears in served
  HTML before trusting what you see.
- **write_file path typos fail silently-ish**: a one-character home-dir typo
  produced "Failed to write file … No such file or directory" with bytes_written 0.
  If a write reports failure, re-check the path before assuming tooling issues.
- **When a leaf times out with ZERO files written but you already hold full
  understanding** (source studied, formulas pinned), skip re-dispatch entirely and
  write it in-parent — wave 10 planner went 0-files → 23/23 green first try that
  way. The dispatch brief's pinned formulas were the whole spec; the agent added
  nothing the parent didn't already have.
- **Fake-timer polling tests (UI wave B pattern)**: components polling via
  `setInterval` test cleanly with `vi.useFakeTimers()` + manual flushes — render,
  then `await act(async () => {})` to settle the initial effect fetch (do NOT use
  RTL waitFor here; it stalls waiting on faked timers), then
  `await act(async () => { await vi.advanceTimersByTimeAsync(5000); })` to tick
  the interval, then unmount, advance again, and assert the fetch call count froze.
  Restore real timers in afterEach. Reference: tests/tasks-view.test.tsx.
- **CSS custom properties cross module boundaries**: tokens declared on `.app`
  in AppShell.module.css (--surface/--rule/--paper/…) inherit into ANY module
  rendered inside the shell — new page modules (TasksView etc.) reference them
  directly without redeclaring; add local fallbacks only where standalone render
  matters. Also: vitest runs with css:false, so CSS-module imports return proxies
  keyed by export name (`styles.pillFailed === "pillFailed"`) — class assertions
  like `expect(pill.className).toContain("pillFailed")` / toHaveClass just work,
  no css build config needed. Pair: stable data-testids for text assertions,
  module class names for styling assertions.
- **Fee vs value display units**: wei→ETH formatting is right for VALUE columns
  but unreadable for GAS/fee columns (30000000000 wei → "0.00000003 ETH");
  display fees in gwei via exact BigInt division by 1e9 (weiToGweiString in
  TasksView: "30 / 1.5"). Convention: gwei for fees, ETH for values; both
  helpers parity-tested with exact-string fixtures.
- **Mobile shell click-shield bug (UI wave B E2E failure, fixed 80d1ead)**:
  the <900px collapse changed `.sidebar` to static/row but left `.app` a
  horizontal flex row — the static aside stretched to full document height and
  its `overflow-x:auto` nav became an invisible ~3567px scroll-port swallowing
  every tap below it ("nav from aside subtree intercepts pointer events" while
  nothing visibly overlaps). Fix: under the breakpoint set `.app{flex-direction:
  column}` so the static sidebar is never cross-stretched. Diagnosis recipe in
  frontend-testing-pitfalls §24 (measure container vs child heights with a
  throwaway playwright-core probe on the e2e port, verify the in-page CSS fix
  before editing source). Related: probes must target the e2e port's fresh
  build — Emad's own long-lived `next start` on :3000 serves stale code.
- **Test-fixture async races under full-suite load**: a helper that waits only
  for `fetch` to have been CALLED can race state-commit — the test passes solo
  but fails inside `npx vitest run` (sibling suites load the microtask queue).
  Make render helpers wait for actual DOM evidence (`waitFor(() =>
  document.querySelector('[data-testid=…]'))`) instead of mock-call counts.
- **Cascading-render lint vs fake-timer tests conflict (UI waves B/C)**: eslint's
  react-hooks rule rejects `useEffect(() => { void load(); … })` when load
  synchronously sets state. Deferring with `setTimeout(load, 0)` satisfies lint
  BUT breaks `await act(async () => {})` flushes in polling tests — a zero-timeout
  is a macrotask that plain act() doesn't run. Fix BOTH sides: in tests use
  `await act(async () => { await vi.advanceTimersByTimeAsync(0); })` for the
  initial fetch, keep real-timer suites on waitFor-with-DOM-evidence. Cleanup
  must clear BOTH the initial timeout and the interval.
- **TS stale-signature phantom errors in route tests**: calling an imported route
  handler (`PUT(request)`) with 2 args can report "Expected 1 arguments" even
  though the source shows `(request: Request)` — Next's generated types cache
  under `.next/types/` lags newly added routes until the next build. Runtime
  passes; don't chase the signature. Remedy: run `npm run build` to regenerate
  `.next/types`, or cast the second arg; verify via vitest, not tsc alone.
- **Stores whose deps have NO `logPath` field (mint-history-store) vs those that
  do (wallet-ops):** when `MintHistoryDeps` has no logPath, the module resolves
  the file from `process.env.HOME` at call time, so a test's hardcoded in-memory
  path constant (e.g. `/mem/.hermes/...`) NEVER matches what the store reads —
  the round-trip and corrupt tests pass values onto a path the store ignores.
  Build the test's LOG constant from the same source
  (`const LOG = String(process.env.HOME ?? "") + "/.hermes/..."`) so the injected
  readFile/writeFile stubs see the real keys. Check whether the deps type carries
  logPath before hardcoding a fake path.
- **Do not share one counter between injected `now` and `id` deps in store tests.**
  `appendX` calls both `now()` and `randomHex()` when building EACH record, so a
  single module-level `tick` used by both increments twice per append — timestamp
  and id assertions then land off-by-one and the round-trip / cap tests fail with
  confusing "expected id-2005 got id-2004" style drift. Give them SEPARATE
  counters (`nowTick` vs `idTick`) so id-1/2 and the 1s-spaced timestamps line up
  deterministically.
- **A record builder returning `Omit<Record,'id'|'atMs'>` does NOT work for the
  pure aggregate fn.** `appendX` takes the Omit form, but `summarizeX` takes full
  `Record[]` — feeding the same builder into `summarizeMintHistory` fails tsc with
  "missing id, atMs". Give the shared builder full fields (id/atMs) up front; the
  extra props are harmless on the append side (accepts the Omit), and the summarize
  calls type-check. Related: fields typed `valueWei?: string` (no `null`) mean the
  skip-missing test must express absence by OMITTING the key (`{ ...rec, valueWei:
  undefined }`), not by passing `null` — null fails tsc. Summarize handles the
  undefined case defensively at runtime anyway.
- **Settings/store validation union narrowing**: validators returning
  `{ok:true,…} | {ok:false,error}` make `.error` access on the union a tsc error
  even where runtime-safe. In tests assert `expect(r.ok).toBe(false)` +
  `expect(!r.ok && r.error).toBe(…)` instead of `.error` directly — avoids
  non-null assertions and keeps the discriminated-union contract honest.
- **TypeScript does NOT narrow a compound NEGATIVE `in` guard under real tsc**:
  after `if ("ok" in r && r.ok === false) { continue; }`, accessing `r.hash` in
  the fall-through still errors (`Property 'hash' does not exist …`) — the
  checker won't fold the negation of `A && B` (i.e. `!A || !B`) for an `in`-
  member. Use canonical positive-`in` instead:
  `if ("ok" in r) { …r.error…; continue; } else { …r.hash… }` — the `else`
  branch then narrows to the sibling cleanly. Hit writing spam-runner.ts
  (§1.7 speed-up return union `{hash:string}|{ok:false;error:string}`); vitest
  passes either way — tsc is the only gate that catches it.
- **`vi.fn` mock return types only bite under tsc (strict), not vitest (transpile-only).**
  A mock injected into a typed DI field (e.g. `source: PendingTxSource`) fails
  `npx tsc --noEmit` when its inferred promise type drifts — most often an unwanted
  `| undefined` from `.shift()`/`.at()`/optional indexing (hit in trigger-watch tests).
  Fix: annotate the mock's async arrow explicitly
  (`vi.fn(async (): Promise<RawPendingTx[]> => { … return next ?? []; })`). Vitest
  passes regardless, so this is one more reason the gate is vitest AND tsc, never
  vitest alone.
- **Time-based watch/poll-loop tests: don't let the ticking clock start already above
  the bound.** `watchTrigger` (and any `while` loop with a max-age/window cap) reads
  `now()` at the TOP of each iteration BEFORE calling the source. If your fake `now()`
  is a closure like `let t; () => t += 500` and `start = now()` lands on the first
  already-big reading, `now() - start > maxAge` fires immediately and the source runs
  0 times (I asserted `calls > 1` and got 0 — looked like an impl bug, was a clock
  bug). Robust pattern: pin the clock (`let t = 0; const now = () => t`) and let the
  SOURCE advance time per call (`source = async () => { t += 250; return []; }`), so
  each empty poll advances the clock deterministically and you can assert the exact
  poll count.

 ### UI wave D — remaining pages fan-out (2026-08-24, uncommitted at session end)
 - Seven pages built via parallel leaves + parent fixes: Activity (+ /api/activity,
   load-once + manual Refresh per Quasarr ActivityLogView — NO polling), Transfers
   (+ /api/transfers-plan pure preview API: direction/source/destination/legs,
   BigInt-exact totals, confirmation-card layout, banner "nothing is sent"), Tools
   (see wave C), Contract Minter manager (standalone BatchPlannerPanel), NFT
   Manager (honest sections + shortcuts, no invented endpoints), Settings
   (+ lib/server/settings-store.ts atomic tmp+rename store + GET/PUT /api/settings;
    General/Automation live, OpenSea/Captcha honest placeholder cards).
 - All leaf scopes landed green individually (42+38+15 suite runs); AppShell
   flips are one-line LIVE_HREFS additions each.
 - CLOSED 2026-08-24 (commit 98c0aa9) via parent salvage — the wave-D fixes were
   all post-600s-timeout parent work: settings-view cascading-render lint
   (setTimeout-deferred initial load, wave-B pattern), TransfersView unused
   `formError`, a Settings-route test whose PUT handler signature had drifted to
   two args (restore single `request`), the settings-store test's discriminated
   union `.error` narrowing, AND the build-gate-breaking route-DI fix below. Final
   gate: 60 files / 491 tests, tsc clean, eslint 0, build ok, E2E PASS
   desktop+mobile — then `launchctl kickstart -k …com.patelai.rh-mint-room` and
   curl fresh assets 200 before reporting anything visible.

## Multi-chain SeaDrop support (2026-08-24, committed 98c0aa9)

Emad: "take every single chain OpenSea supports for mints and integrate it… if I
post an OS collection I don't have to do anything, everything just works including
chain change." Whole-chain expansion is a Mint Room architect change:

- **`lib/chains.ts` is the one place every chain lives.** `ChainKey` doubles as
  OpenSea's own `api.opensea.io/api/v2/chain/<key>/…` path segment AND the ethers
  `networkName`. One `CHAINS` record {key, chainId, networkName, label, rpcUrl,
  openseaAssetBase, nativeSymbol}; adding a chain = ONE entry, not grep-and-patch.
  Current set: ethereum(1), base(8453), polygon(137), arbitrum(42161), optimism(10),
  blast(81457), ink(57073), robinhood(4663). DEFAULT_CHAIN stays robinhood.
  RULE: only add chains whose SeaDrop deploy (classic factory
  `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5`) you can cite; never invent an RPC —
  omit a chain rather than ship a broken endpoint.
- **VERIFY every chain RPC with a live `eth_blockNumber` POST before shipping —
  a chosen endpoint can be dead even if it looks canonical (hit 8/24).** publicnode
  URLs were silently broken for several chains: `ethereum-rpc.publicnode.com` →
  HTTP 000 (connection failure), `polygon-bor-rpc.publicnode.com` → HTTP 000,
  `base-rpc.publicnode.com` → HTTP 308 redirect (curl doesn't follow). Robinhood
  + ink loaded only because they weren't publicnode. Symptom: the chain selector
  renders no network/block/balance for a chain even though the entry "looks right."
  Proven working set after a `curl -X POST -H 'content-type: application/json'
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}' <url>`
  probe (all returned 200): eth.drpc.org, base.drpc.org, 1rpc.io/matic,
  arb1.arbitrum.io/rpc, mainnet.optimism.io, rpc.blast.io,
  rpc-gel.inkonchain.com, rpc.mainnet.chain.robinhood.com. When a chain's chosen
  endpoint 000s, DO NOT trust the label/comment — `curl` it and swap to a working
  one (drpc / 1rpc / chain-native). Also keep the CHAINS header comment's endpoint
  list in sync with the actual `rpcUrl` values — they drifted and the comment
  carried a stale endpoint (eth.drpc.org vs 1rpc.io/eth) that wasn't what the code
  used. Note: `api.opensea.io/api/v2`
  headerless returns 401 (needs x-api-key); the module still fetches
  collections/drop endpoints and degrades gracefully, so chain detection leans on
  the resolved contract + slug, not on a keyed API.
- **Execution path must NOT hardcode a chain.** `lib/server/custom-runner.ts` used
  to pin `https://rpc.mainnet.chain.robinhood.com` + chainId 4663. Now it derives
  `getChain(mission.chain ?? DEFAULT_CHAIN).rpcUrl` and validates
  `network.chainId === BigInt(chainConfig.chainId)`. Rule: every module that spawns
  or signs must resolve RPC/chainId from the mission's chain — grep for
  `rpc.mainnet.chain.robinhood` / `4663` / bare robinhood across lib/server + app/api
  after any chain work. (`rawRpcCall(method, params, chainKey=DEFAULT_CHAIN)`,
  `seadrop.ts`/seadrop-stats chain params, preflight/engine-runner/multi-runner
  already thread chain — the gap was custom-runner.)
- **`pickContract(payload, preferredChain?)` in modules/opensea.ts:** now that every
  EVM chain is supported the old "prefer a supported chain" logic collapses to
  first-listed — which regresses a pasted raw address. When the input was a RAW
  ADDRESS and it resolved through the chain-scoped endpoint, that chain is the
  USER'S EXPLICIT INTENT and must WIN. Fix: `resolveSlugForContract` returns
  `{slug, chain}` and `fetchCollectionPlan` threads that chain as `preferredChain`
  into `pickContract` (exact-match wins first, then first-supported, then
  entries[0]). Regression anchor in tests/modules-opensea.test.ts: bare slug
  `bakemono-crayons` now resolves to ethereum (first-listed); raw address `0x4FF6…`
  stays robinhood.
- **Route-handler build-gate fix (an anti-pattern documented EARLIER got REVERSED
  by the build gate):** the Activity route came in as `GET(request, deps = {})`,
  which `npm run check`'s build rejects at `.next/types/validator.ts` TS2344
  (`'RouteHandlerConfig<"/api/activity">'`) even though vitest + per-file tsc pass.
  (This repo's older "extra trailing deps param is harmless to Next" claim was WRONG
  for a handler the build actually validates — the safest pattern now is a thin
  shim.) The clean fix that keeps DI: split into a testable core
  `export async function getActivityEntries(deps)` + a THIN
  `export async function GET(request)` shim that loopback-guards then calls the
  core with defaults. Tests import the core for DI. Do this for every new route —
  NEVER put a deps param on the Next handler itself.

## UX polish wave E (2026-08-24, committed 791a365) — dead RPCs, OpenSea soon, multi-mint clarity

Emad feedback after wave D: ethereum/polygon chain selectors didn't load; why is
there a coming soon on opensea; why is multi wallet mint so confusing — everything
needs to be smoother and more intuitive.

- **The OpenSea coming-soon was a MISSING PAGE, not a stub.** NAV_SECTIONS had
  `{ label: OpenSea Checker, href: /opensea-checker, soon: true }` because
  app/opensea-checker/ (the page) had never been built — only the Tools-embedded
  lookup existed. Sidebar soon flags must be checked against actual route files:
  an item is soon either (a) a real future feature or (b) a forgotten page for an
  already-designed feature. Here it was (b). Fix pattern: extract the working tool
  (OpenSeaChecker) into shared components/OpenSeaChecker.tsx + own module css, reuse
  it in BOTH the Tools host AND new app/opensea-checker/page.tsx (a `heading` prop
  toggles page vs in-tool framing), flip soon:true to false, add /opensea-checker to
  LIVE_HREFS in tests/app-shell.test.tsx (SOON_HREFS derives by filter, so nothing
  else moves). Shared component = no forked UI. New suite: tests/opensea-checker-page.test.tsx.
- **Multi-wallet mint clarity (Emad: too confusing).** The original panel used
  ad-hoc inline style labels and a neutral mode select. Brought to house standard:
  labeled grouped fields (fieldLabelText + styled qtyInput/modeSelect), a
  plain-language explainer line, and — most important — mode-aware DANGER
  affordance: choosing LIVE renders a red liveWarn alert + a red liveButton so the
  gas-spending path is unmistakable. Rehearse stays the default. Add the classes to
  CommandCenter.module.css (one minified line; the patch-wrapped multi-line block
  stays valid — verify with a build, and fieldLabelText should appear once).
- **Turbopack CSS build breaker:** `font-family: var(\"--font-mono\", mono)` —
  QUOTING the custom-property name inside var() is a CSS parse error and next build
  fails with Parsing CSS source code failed pointing at the var(. Use var(--font-mono)
  unquoted. (Write-time lint flags the new .tsx @/ alias as missing — that's the
  known false positive; the real signal is npm run check.)
- **Test-regex double-escape when patching a regex literal:** editing
  /wallet\\. Rehearse/ via patch can double it to /wallet\\\\./ (literal backslash +
  wildcard). After patching any test regex, read the line back before running.
- Gate: 61 files / 494 tests, tsc clean, eslint 0, E2E PASS desktop+mobile →
  launchd kickstart + curl an asset 200. Shipped in-parent (no delegation) — right
  call, files were shared with prior/parallel leaves.

## Multi-wallet simplification + OpenSea-URL input (2026-08-24, commit 51c4394)

Emad again, the durable UX bar for Mint Room's PRIMARY mint flow: "I am not technical… when I
want to multi wallet mint I can't understand all this. I want it as easy as just putting in an
opensea URL and choosing an option to multi wallet mint." Fear-of-jargon overrides correctness:
a technically-correct but wall-of-technology UI reads as "you need to be technical," and Emad
will say so (twice, if needed).

- **The main "Enter collection" input must ACCEPT a pasted OpenSea URL, not just a 0x
  address.** `/api/plan` ALREADY resolves URLs/slugs via `parseCollectionInput` +
  `resolveOpenSeaSlug` (lib/server/opensea-resolve.ts), so the wiring is purely client-side:
  label/placeholder become "OpenSea link or contract address
  (https://opensea.io/collection/… or 0x…)". No separate resolution field, no "which chain?"
  — URL resolution + chain stay automatic server-side.
- **On a successful inspect, write the resolved contract back into the input** so the user
  sees what got found: `if (data.collection && data.collection !== collection)
  setCollection(data.collection)` — and pass the resolved address downstream:
  `<MultiMintPanel collection={plan?.collection ?? collection} …/>`. This matters because the
  panel validates `/^0x[0-9a-fA-F]{40}$/` on its collection prop — passing the raw URL would
  fail the panel's local regex even though inspect succeeded.
- **Power-user plumbing NEVER lives on the Dashboard.** The raw ABI "Custom mint task
  (rehearse)" card (`<AdvancedTaskPanel/>`) was REMOVED from CommandCenter entirely — it
  already lives on the Tasks page (TasksView mounts it under its own "New task" section). The
  Manual calldata / selector / ABI fields Emad screenshotted as "I can't understand all this"
  are exactly what he reacted to; keep them off every primary mint path.
- **Multi-wallet is ONE always-visible plain section**, not a collapsed
  `<details>"Multi-wallet mint (advanced)"</summary>` and not "burner wallet / rehearse"
  vocabulary. Collapsing behind "advanced" + jargon reads as "this is for technical people."
  Render `<MultiMintPanel/>` directly (it starts disabled until a valid collection is set),
  titled "Mint from all wallets," controls = quantity-per-wallet + a mode select whose labels
  are plain: "Dry run (doesn't spend)" (default) / "LIVE — spends network fee"; buttons
  "Dry run all wallets" / "⚡ Mint from all wallets"; live mode shows the red liveWarn
  "⚠ Minting on the network spends a little ETH as the fee from every funded wallet. Dry run
  first…".
- **Test churn from relabeling:** every user-facing string change ripples into tests.
  multi-mint-panel.test.tsx asserts the explainer sentence, `modeSelect.selectedOptions[0]`
  text, the options array, AND the start-button regex (`{ name: /rehearse all wallets/i }`
  → `/dry run all wallets/i` in four spots); dashboard-unification asserted
  "Multi-wallet mint (advanced)" → now "Mint from all wallets" (and — unrelated to labels —
  needs `useSearchParams: () => null` in its next/navigation mock after any hook addition).
  grep the old labels (`Rehearse`, `burner wallet`, `Multi-wallet mint (advanced)`) across
  tests before finalizing copy.
- Gate = every wave gate: full vitest + `npx tsc --noEmit` + build, then
  `launchctl kickstart -k gui/$(id -u)/com.patelai.rh-mint-room` and curl "/" 200 before
  telling Emad it's live.

## Live-run error hardening (2026-08-24, commit 16f38d1) — three Emad-visible failures

Emad ran the app for real and hit three failures; all fixed. When Emad reports "several
errors / this needs to work smoothly," he means the RUN-TIME surfaces, not the 
build/tests — audit the executed paths (live arm, engine funding gate, OpenSea auth,
waitFor terminal handling), not the green suite (those all passed; the failures were
integration realities the mocks hid).

1. **"Live execution is server-locked. Restart Mint Room with MINT_ROOM_LIVE=1"
   on a LIVE button click.** `engine-runner.startEngineSession` and
   `multi-runner.startMultiSession` ONLY checked `MINT_ROOM_LIVE==="1" || uiAuthorized`
   — they BYPASSED the in-app bounded `armLive()` window, so the safety arm built in
   wave 15a had no effect on the engine paths. **Fix: add `&& !liveArmedState().active`**
   to both gates (`import { liveArmedState } from "./signer"` — NOT rpc; engine-runner
   imports `BOT_WALLET` from "./rpc", anchor the signer import on that line), and change
   the error copy to "Arm live execution in Mint Room (Settings → Safety)". **The UI then
   auto-arms a bounded window on the LIVE click itself (the click IS the approval):**
   in MultiMintPanel.start() for live mode, before POST /api/multi-mint, call
   `/api/executor {action:"arm", maxTotalWei:"20000000000000000", ttlMs:15*60_000}`
   (~0.02 ETH fee ceiling, 15 min). Emad is non-technical: NEVER deliver a fix that
   requires him to run `MINT_ROOM_LIVE=1` or edit an env — arm from the button.

2. **Funding shortfall → terminal "[INPUT] Top up … press Enter; s to skip" →
   "no wallet remains eligible and valid for the selected stage".** The mint is FREE
   (price 0) but every tx still pays a NETWORK FEE from the minting wallet; Emad's
   burner wallets were a hair under the fee line. The engine asks an interactive
   [INPUT] question a browser can't answer (multi protocol auto-answers "s" once for
   the funding prompt, but with ALL wallets short there's nothing left). **Fix:
   pre-flight before LIVE.** In MultiMintPanel.start() for live mode, GET /api/wallets
   first; if any wallet < MIN_WEI fee buffer (0.0002 ETH — superseded, see the
   "Penny-scale fee floor" section below: the engine's real worst case is
   gasLimit×maxFeePerGas, and pinning manual fees drops it to ~0.00004), set `topUp`
   `{short, neededEth}` and return WITHOUT minting; render a plain line
   "N wallets are below the fee buffer (~X ETH each)" + a **"Top up & mint"** button
   that POST `/api/wallets {action:"distribute", amountEth}` then re-runs start().
   Plain-error translation (`plainError(raw, log)`): `/no wallet remains eligible|funding
   shortfall/` → "The wallets were low on ETH for the network fee…", and Surface it via
   `onTerminal(status, logs, "")` on the poll's terminal branch.

3. **Single mint died at "OpenSea SIWE authentication failed with HTTP status 429"**
   and the button stuck on "Minting…". Two causes. (a) **The engine's OpenSea retry
   timing was self-inflicted rate limiting**: `OPENSEA_RETRY_INTERVAL_MS=250` with
 `OPENSEA_MAX_ATTEMPTS=3` hammers OpenSea. Bump to **3000ms + 8 attempts** in BOTH
 `buildMultiRuntimeConfig` AND engine-runner's config builder. (Wallet ops
 receipts/batching/defaults → `references/wallet-ops-receipts-rpc-batching.md`.)
   press Mint again — it auto-retries now.").

4. **Empty "status:" run box after a failed start.** `active = hasRun` rendered the
   box even when no session ever started. **Fix: `active = hasRun && runId !== ""`.**
   Also: gating the poll's terminal branch on CLOSED-OVER `status`/`logs` state is a
   stale-read bug — parse `nextStatus`/`nextLogs` from the payload once and pass those
   to onTerminal; and keep the poll's try/catch structure intact (a mid-edit refactor
   briefly duplicated the payload parse and dropped the retry catch — re-read the whole
   fn after editing).

5. **Emad comprehension bar (recurring, strongest-yet signal 8/24):** when he says
   "I am not technical, you are making this way too complicated" he means the copy, the
   error text, and the number of steps — not the tech. On a direct question ("don't all
   the wallets have enough eth to mint for free?") answer with ONE plain, correct
   sentence first (free mint ≠ free network fee) before any plan. Do not dump a wall of
   diagnostics or offer two "option" branches; give the one-click path.

- Gate / verify: full vitest + `npx tsc --noEmit` + build, then launchd kickstart +
  curl "/" 200. When adding an env-independent live path, live-probe BOTH the arm
  route and a shell-out path (the mocks will not catch a missed liveArmedState gate).

## Penny-scale fee floor (2026-08-24, commit 58ae37a)

Emad: "0.0002 per wallet is too much. I should be able to mint with a penny in my
wallet." Free mint ≠ free gas — the mint engine's upfront funding check was making
every burner pay roughly the same hard floor regardless of the real cost. Root cause
and fix:

- **The engine requires each wallet to AFFORD worst case `gasLimit × maxFeePerGas`
  upfront, not the actual per-tx spend** (`multi_wallet.rs`
  `FundingRequirement.maximum_native_cost`, reached from `ensure_single_wallet_funding`:
  300000 gas × maxFee + the mint value). With `FEE_AUTOMATIC=true` the engine derives
  maxFee from an RPC estimate (`baseFee×2 + priorityFee`, chain.rs `SubmissionInputs`),
  which on Robinhood chain round up to ~1 gwei → 300k × 1e9 = **0.0003 ETH**. That
  worst-case number — not the real few-wei fee — is what drives the top-up. Emad saw the
  ~0.0002-0.0003 figure and said "too much."
- **Fix: pin a tiny MANUAL fee** in `buildMultiRuntimeConfig` (multi-runner.ts):
  `FEE_AUTOMATIC=false`, `MAX_FEE_PER_GAS_GWEI=0.1`, `MAX_PRIORITY_FEE_PER_GAS_GWEI=0.01`.
  `parse_gwei` accepts up to 9 decimal places (0.1 gwei is fine). RH gas is ~0.001 gwei
  so 0.1 is ~100× headroom; requirement drops to 300k × 0.1e9 = 3e13 wei ≈ 0.00004 ETH.
  `FEE_AUTOMATIC=false` REQUIRES both manual keys (the parser errors if automatic AND
  manual fee config coexist).
- **Align the UI preflight to the REAL engine requirement but slightly ABOVE it**, so
  short wallets are caught BEFORE the run. The 16f38d1 preflight used `MIN_WEI=0.0002`,
  which sat BELOW the old engine's ~0.0003 — a 0.00025 wallet passed preflight then died
  mid-run inside the engine ("Top them up with the button above" → nothing was above).
  After the fee pin, set `MIN_WEI = 100_000_000_000_000n` (0.0001 ETH) in
  MultiMintPanel.start(). Keep `neededEth` a literal string ("0.0001"), not a derived
  toFixed, so the distribute amount is stable.
- Emad comprehension bar: when he challenges a fee/cost ("should be a penny"), inspect
  the ENGINE's worst-case funding requirement (gas × maxFee + value), fix it with a
  `.env` config knob in the runtime config, then align any matching UI threshold —
  don't just relabel the copy.

## Wave F — Wallets ops cards + persistent history log (2026-08-24, committed a3b17c5)

Emad on the wallets page: \"none of this makes sense… i need a history log on fresh
wallet ops wallet distributer/consolidater.\" The distribute/consolidate BACKEND
already existed (`/api/wallets POST action=create|distribute|consolidate`) — the
page just buried it under a cramped unlabeled control strip and had NO record of
what ran. UX principle that generalizes: Emad reads pages as walls of numbered
technical panels unless each real action is its own plain-language card with ONE
obvious button, and any irreversible/money-moving op needs a durable operation
history he can scroll.

- **Wallet-ops store pattern (`lib/server/wallet-ops-store.ts`)**: append-only
  on-disk op log `~/.hermes/rh-mint/logs/wallet-ops.json`, newest-first prepend,
  atomic tmp+rename (mkdir/chmod discipline like the registry), capped MAX_OPS=200,
  per-op `detail` bounded to 8 lines. Record shape: `{id, action, atMs, chain,
  chainId, summary, ok, total, detail}` where summary is a HUMAN sentence
  (\"created 4 wallets (fabw_1, fabw_2)\", \"swept 2/4 wallets back to ops wallet
  (~1.000000 ETH)\") and ok/total drive a status progress bar. `/api/wallets POST`
  calls `appendOp` after EACH action resolves (counts computed from the results
  array); `/api/wallet-ops GET` reads it newsest-first, loopback-guarded. Route
  needs NO injected fs — calls `readOpsLog()` with defaults (real disk) — so the
  route is thin and its test just `vi.mock`s the store module.
- **Deps-type trap (new): reading a support FS via `typeof readFile` is unmockable
  in BOTH directions.** The node fs/promises signatures are overloaded unions that
  neither a simple test stub NOR a bare real `readFile` reference satisfies
  structurally under the strict build tsconfig. For a store whose deps are
  production `readFile`/`writeFile`/etc, define NARROW structural types on the
  deps (e.g. `WriteFileLike = (path: string, data: string, options?: {encoding?,
  mode?}) => Promise<void>`), use them on `WalletOpsDeps`, and let the real fn
  satisfy them at the call site. Simple test stubs then type-check too. Same for
  the route: if it doesn't actually need injection, drop the deps injection entirely.
- **`vi.mock` with `importOriginal` partial-spread breaks NEW test files under this
  repo's moduleResolution** (Cannot find module '@/…'). The proven route-test shape
  is the settings-route template: full `vi.mock(\"@/lib/server/x-store\", () =>
  ({ …each fn: vi.fn() }))` — NO importOriginal — then `vi.mocked(loadX)` for
  assertions. Avoid `Parameters<typeof import(...)>[0]` gymnastics in stubs; the
  narrow deps above make plain `(path: string) => …` stubs type-clean.
- **Route-DI correction strengthened (see also wave-D pitfall):** after the
  Activity-route reversal, the pattern is unambiguous — a Next handler the build
  validates must be a THIN `(request)` shim; put deps on a separately-exported
  testable core. Never reintroduce trailing-deps params on the handler itself.
- UI: three cards (Create fresh wallets / Distribute ETH / Consolidate ETH) each
  `opCard` with h3 + one-line `opDesc` + single `opField` (one button), then a
  stat strip (ops wallet + fresh-wallet total) then the history section (badge +
  summary + `ok/total · chain · UTC-time` meta + progress bar; a run with
  `ok !== total` renders the row `failed`). Multi-mint flow moved BELOW unchanged.
  Add classes to Wallets.module.css (`opGrid`/`opCard`/`opDesc`/`opField`,
  `statStrip`, `opsHead`/`opsList`/`opRow`/`opBadge`/`opBar`); badge color keyed by
  action (create green / distribute blue / consolidate amber / other purple) via
  `styles[OP_CLASS[op.action]]` map. Regression tests: tests/wallet-ops-store.test.ts
  (in-memory fs), tests/wallet-ops-route.test.ts (looopback 403 + empty state),
  tests/wallets-page.test.tsx (cards + history order + create POST). NOTE: build
  types `??` vs `||` and CSS-module badge classes — use explicit `.opBadge.create`
  classes, NOT `opBadge[\"multi-mint\"]` (object-bracket key is a CSS attribute-sel
  parse hazard).
- Gate: 64 files / 505 tests, tsc clean, eslint 0, E2E PASS desktop+mobile → launchd
  kickstart + curl /wallets and /api/wallet-ops both 200. Done in-parent (shared
  files, small scope).

## Waves 11–12 closed (2026-08-24, commits b1d0a4b + 9ea92b9)

Emad armed the dev loop LIVE this day ("arm live, do everything without asking me,
keep working" + "use multiple agents + unlazy"). Both waves shipped via 3-leaf
multi-agent fan-out on DISJOINT files + an unlazy `GATES-waveN.md` CHECK/EXPECT
ledger; the parent then wired each route's injected deps to the real sibling modules
and ran the FULL gate itself (scoped+full vitest, tsc, eslint, build, launchd
kickstart + live loopback curl). Emad wants THIS fan-out + unlazy pattern for the
remaining engine waves, NOT solo in-parent — that overrides the earlier wave-4 "skip
delegation for small waves" guidance for these multi-file engine+route waves. Report
one line per wave; never pause for confirmation on local work. IMPORTANT: arming live
changed the WORKFLOW only — real engine spending still waits for the executor-wiring
wave, so do NOT broadcast money from these rehearse-only endpoints.

- **Wave 11 (b1d0a4b):** trigger-watch.ts (25/25) + spam-runner.ts (21/21) +
  `lib/server/trigger-store.ts` + `app/api/trigger/route.ts` (16/16). Full gate
  67 files/567 tests. `/api/trigger` is REHEARSE-ONLY: register requires maxSpendWei
  and forces `enabled:false`; the `dry-run` action is a no-op (live arming is a later
  wave). No keys touched — watcher + runner are sign-free (all IO injected).
- **Wave 12 (9ea92b9):** `lib/server/fund-ops.ts` pure planners (26/26;
  buildDispersePlan / buildCollectPlan / sumWei, exact BigInt, zero floats, plans
  stamped `rehearsed:true`) + `lib/server/fund-op-store.ts` (6/6; append log mirrored
  from wallet-ops-store, cap 200) + `app/api/fund-ops/route.ts` (16/16; thin handlers
  + DI cores; POST disperse/collect/ops; loopback). Full gate 70 files/615. Live probe:
  disperse 1 ETH → totalWei exact; collect fixed 0.5×2 → 1.0 ETH; headerless curl → 500
  (SAME_ORIGIN_ONLY guard). Rehearse-only — nothing signed, sent, or appended.
- **Wave 13 (committed; mint-history-store DONE, nft-scan still open):** the
  mint-history leaf landed green (6/6 + tsc). `lib/server/mint-history-store.ts`
  is the THIRD member of the append-log store family (wallet-ops → fund-op-store
  → mint-history), same narrow-Wei-suffix/atomic-tmp+rename/cap-2000 shape, but
  deps have NO `logPath` field (path derives from `process.env.HOME` inside the
  module). Adds the pure `summarizeMintHistory(data)` aggregate — per-status
  counts + per-group totals all-exact BigInt, skipping MISSING (undefined)
  value/gas fields. `loadMintHistory` DEGRADES like the rest (missing file →
  empty) but unlike wallet-ops surfaces CORRUPT files as `{ok:false,error}`
  (mint history is source-of-truth; don't silently drop it).
- **Wave 13 nft-scan CLOSED (commit 60c84c1, `lib/server/nft-scan.ts` + tests
  10/10 green):** read-only ERC-721/1155 holdings enumeration via eth_call
  (recipe in Pitfalls below). Route `app/api/nft-scan` (thin-shim pattern, deps
  on a testable core) was WIRED to the real scanner + mint-history store by the
  parent; the rehearse transfer-plan stays injected-only (no live transfer module
  yet) so its live POST honestly returns the "not wired" 503. Full gate 651 tests,
  eslint 0/0, build ok, launchd restart + live probe: GET history -> {ok:true,
  history:[]} (wired store); POST scan invalid contract -> real scanner
  "invalid address: 0xBAD" (proves wiring WITHOUT network); headerless GET -> 500.
- **Wave 14 in-flight (2026-08-24):** `lib/server/rpc-failover.ts` (sequential
  multi-endpoint failover + per-endpoint rate limit, spec §4.1, RH + ETH presets)
  + `lib/server/proxy-pool.ts` (env-driven round-robin rotator) dispatched as 2
  leaves. Integrate, full gate, commit. THEN (in-parent, touches execution core):
  fix the `/api/tasks` rawData-derivation gap so module:"opensea" / "merkle" tasks
  posted WITHOUT selector/rawData (calldata lives in moduleParamsJson) reach
  simulate/store instead of 400ing with "task has no calldata source".

### Wave 15a — live-executor core (commit 5228664): lib/server/signer.ts
The SINGLE live-spend choke point. Every future real-money executor (trigger fire, spam send, fund-op broadcast, NFT transfer) MUST route through `executeLive(params, deps)` — the pattern to reuse for ANY new live path. Replaces the old duplicated live-gating in custom-runner.ts (which still has its own `protectedWallet`).

- **Gate order matters — authorization runs FIRST, before loading the key.** `executeLive` checks: (1) kill switch (`armKillSwitch`, checked again immediately pre-broadcast), (2) authorization = `env.MINT_ROOM_LIVE==="1"` OR bounded `armLive()`, (3) THEN load signer. Never touch the key when unarmed. Chain-id check → simulate (`provider.call` + `estimateGas`, gas = est×120/100 or an override) → hard cap `value + gas·maxFee <= maxTotalWei` → rehearse-required (`isRehearsed(id)`, enforced even when MINT_ROOM_LIVE=1, mirroring custom-runner) → armed-ceiling → kill re-check → broadcast → receipt poll (120s; a receipt timeout returns `{ok:true, sent:true, status:-1}` — sent-but-unconfirmed is NOT a failure, never report it as failed).
- **Bounded expiring `armLive({maxTotalWei, ttlMs})`** is the UI's "approve live, bounded" gesture: a cumulative ceiling + TTL, distinct from the permanent env lock; `liveArmedState(now)` clears it when the window lapses. `executeLive` refuses when `params.maxTotalWei > armed ceiling`.
- **Key isolation:** `loadProtectedSigner` accepts ONLY the ops wallet `~/.hermes/secrets/bot_wallet_key` — rejects non-regular-file, any perms with a group/other bit (`(info.mode & 0o077) !== 0`), and any key whose derived address isn't `0x1111…1111`. Keys never enter app state. Use NARROW structural deps (`KeyReadFile = (path, encoding) => Promise<string>`; `KeyStat`) — node fs/promises overload unions don't type-match plain test stubs; cast the real defaults `as unknown as KeyReadFile` (same trap as wallet-ops WriteFileLike).
- **Test seams:** `deps.signer` is an INJECTED ethers Wallet that is TRUSTED (do NOT apply the ops-address lock to injected fakes — only to the real `loadProtectedSigner` path); `deps.client` is a `SignerClient` interface (getNetwork/call/estimateGas/getFeeData/sendTransaction) so tests never hit a live node or a real key. `makeEthersClient` must NORMALIZE ethers `wait`: its `TransactionReceipt.status` is `number|null` and the method has overload unions — wrap it as `async (confirms?) => { const r = await w.wait(confirms); return r ? {status: r.status ?? -1} : null; }` or tsc rejects the assignment.
- Consumers wire as thin adapters that CALL executeLive (spam-executor, trigger-executor); each live send is an independent gated send — do NOT hand-manage nonces (executeLive owns signing+broadcast). Live control route pattern: `/api/executor` thin GET/POST shims + DI cores (arm/disarm/kill/unkill/rehearse-mark/send + status). Loopback guard on both verbs.
- Pitfall when testing the gate: `executeLive`'s receipt-timeout branch needs an ADVANCING `deps.now` (a constant clock → infinite loop → test hang): `let t=0; now: () => (t += 5000)`; keep `receiptTimeoutMs` tiny (1). And `armLive` grant-vs-refuse distinguish by ceiling vs `params.maxTotalWei` — for "grants" the ceiling must be ABOVE the request's maxTotalWei.

### Pitfall — `as` casts hide real DI signature mismatches at integration time
When wave leaves ship a route that takes INJECTED planner/scanner fns (so it builds
standalone before the sibling libs exist), the parent's wiring step is where the REAL
module signatures meet the route's DI contract. If the route does
`const build = deps.fn ?? realFn; const out = await (build as Fn)(args)`, the cast
suppresses tsc, yet at runtime the real fn receives the wrong arg shape. Confirmed
8/24: the fund-ops route passed `totalSourceBalancesWei` as a STRING (stale
CollectPlanArgs type) but the real `buildCollectPlan` required `Record<addr,wei>` for
all-with-gas-reserve; `as BuildCollectPlanFn` hid it entirely. Parent fix: after
wiring, re-read the REAL module signature and type the DI contract against it (not the
leaf's invented shapes), pass objects through (400 on non-object), and add a
live-mismatch test. ALSO: any test asserting a behavior wiring DELETE (e.g. the old
"planner not wired → 503" branch) must be REWRITTEN, not left failing — parent replaced
it with a "wired fall-through calls the real planner" test. Verify every wave endpoint
Verify every wave endpoint with a real loopback curl (GET + POST with Origin/Host headers), never just vitest
mocks — cast-hidden and optimistic-transient bugs never surface in mocked tests.

- **O(n²) store-cap tests time out under FULL-suite load but pass solo.** A "cap at
  N" test that appends N+5 records (each serializes a growing N-item array on every
  append) is O(N²). Solo it finished ~2s; under `npm test` parallel load it hit
  `Error: Test timed out in 5000ms` at ~6.2s (wave 13 mint-history-store cap test).
  A scoped `vitest run <file>` will NOT catch it — only the full suite does. Fix:
  give that one `it(...)` an explicit `, 20_000` timeout (it's a legitimately heavy
  test, not a leak). Add the timeout BEFORE closing the wave's full-suite gate.
- **Headerless curl GET is 500 = the LOOPBACK GUARD, not a routing bug.**
  `assertSameOriginLoopback` throws SAME_ORIGIN_ONLY on GET too when there's no
  `Origin` header (not just POST/PATCH). A bare `curl http://127.0.0.1:3000/api/x`
  returns 500 / empty body — that's the guard working. Always probe with
  `-H "Origin: http://127.0.0.1:3000"` (GET and POST) and treat the headerless 500
  as the expected negative test rather than chasing a "broken route".
