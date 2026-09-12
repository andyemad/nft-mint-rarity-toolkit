---
name: mint-field-guide
description: Use when adding/editing code or tests in mint-field-guide.
---

# mint-field-guide — repo conventions

Next.js NFT mint dashboard at `~/Projects/mint-field-guide`. This
skill is the "how to write code in THIS repo" playbook — pure-logic modules with
provider injection, immutable serializable state, and vitest tests. Load it before
touching anything under `src/lib/` or `src/app/api/`.

## ⚠️ This is NOT rh-mint-command-center (Mint Room)
Two different local repos share the "mint" name and get confused:
- **mint-field-guide** = eCalm Suites (Cloudflare Workers + D1 + Next.js, the
  live board + alpha-group webhook). THIS skill.
- **rh-mint-command-center** = the local loopback Mint Room desktop app
  (SeaDrop engine OSNM-Z, rarity sniper, wallets) — a SEPARATE skill. Its
  `launchd`/`/rarity`/multi-wallet rules do not apply here.
If the task is "eCalm Suites alerts / the Discord webhook / mint data":
`skill_view('mint-field-guide')`. If it's "Mint Room UI / mint execution /
fresh-wallet ops": `skill_view('rh-mint-command-center')`. Loading the Mint Room
playbook for a mint-field-guide change wastes a full trace (the two share almost
nothing at the file level). Emad said the eCalm alert is Discord tooling; the
business side (P&L, income) stays on IRC/iMessage, never on servers with members.

## Parity is VISUAL, not just functional — the #1 lesson
The 165-gate acceptance matrix measures FUNCTIONAL behavior only. When Emad says "parity
with the og" he means the VISIBLE product — its interaction gestures plus a sleek design —
not passing test gates. A green functional audit (158/165) is NOT "done" if the home page is
still a bare wireframe; he rejected exactly that ("Awful — how is this on parity with the og",
2026-08-13). His words: "it's not about the design but the gestures the UI shows mainly and of
course a sleek beautiful design." Before claiming parity: (1) get reference screenshots of the
target, (2) reproduce its gestures (tabs, sortable tables, time/chain/volume filters, live feeds,
notification overlays — but the auto-toast overlay stack was REJECTED 2026-08-14 as "annoying popups",
don't re-add it), (3) match the visual bar (dark theme, accent palette, polished spacing). Also
reproduce the reference's DESKTOP and MOBILE layouts SEPARATELY — the desktop is a three-column board +
featured mint module, tabs are mobile-only; shipping the tabbed single column as the desktop default
drew the "why would you have the mobile version as the desktop version" rebuke (2026-08-14).
The home page is `src/components/mint-terminal/` (NOT the DecisionStack). After the eCalm Suites rebrand (2026-08-14) the live layout is the **dark pastel 3-column terminal** — Trending / New Mints / Market all visible side-by-side (desktop; single column ≤900px), a FeaturedModule spotlight strip on top, eCalm branding in the header (real collection logo, Caveat script wordmark, Fraunces small-caps tagline, health chip), thin cool→warm banner strip, pastel accent tokens on dark surfaces (sage=success, mauve=warning, sky=info, peach=hot; no neon, no toasts).

HISTORY (don't re-litigate): the "Calm Board" master–detail restructure (left suite rail + ranked bands + right spotlight stage, light paper theme) was built and deployed the same day, then **reverted** after Emad's rejection: "design is okay but this shit is not working. no mints from robinhood, nothing seems sleek or intuitive like the previous design" — he wanted the proven 3-column composition back WITH the branding layered on. LESSON (a real preference, corrected 8/14): on a working product Emad likes, **rebrand = layer the visual identity (palette, type, logo, header) on the PROVEN layout/IA; never restructure composition in the same pass.** When he says the redesign lost the feel of the previous version, revert the composition and keep the branding — don't argue for the new IA.

The `FEATURED_MINT` fixture is only the pre-live default; once live data lands the spotlight shows the #1 trending row via a DERIVED `effectiveSelectedId` (useMemo — never setState in an effect; `react-hooks/set-state-in-effect` is a hard lint error here). The dark three-column terminal it replaced is historical.

## Stack (verify against package.json before assuming)
- Next **16.3** (breaking changes vs training data — read `node_modules/next/dist/docs/` per `AGENTS.md` before writing Next code).
- React 19, zod 4, vitest 4 (`environment: "jsdom"`, setup `./src/test/setup.ts`).
- eslint-config-next (`core-web-vitals` + `typescript`). Path alias `@/* -> src/*`.

## Core conventions (observed across `src/lib/indexer`, `enrichment`, and new `monitor`/`alerts`)
1. **Pure functions over closures.** Modules export pure functions that take state and return `{ result, state }` (or `{ ...outcome, state }`) with a NEW state object — never mutate in place. Thin closure wrappers (e.g. `createMonitorRepository`, `createStageCache`) are the exception, built ON TOP of the pure functions.
2. **Explicit clock params.** Every function that cares about time takes `nowSeconds`/`nowMs`/`observedAt` as a param. Pure logic never calls `Date.now()` / `new Date()` except as an optional default for non-deterministic convenience paths. This makes tests use a fake clock with zero mocks.
3. **Money is integer base-unit strings** (wei), validated with `/^\d+$/` (rejects negative/NaN/decimal). Never floats.
4. **`DataChain = "ethereum" | "robinhood"`** from `@/lib/indexer/types` (also re-exported via `@/lib/enrichment/types`). Chains are a closed union.
5. **Address helpers** live in `@/lib/enrichment/address`: `isValidAddress`, `normalizeAddress` (lowercase-or-null), `isZeroAddress`, `ZERO_ADDRESS`. Normalize then compare; identity keyed by `(chain, address)`.
6. **Validation split — the key rule:**
   - **Throw `Error`** for programming errors / malformed input *inside* a pure function (matches `threshold-transitions.ts`, `schedule-alerts.ts`).
   - **Return discriminated-union result codes** for *domain* outcomes the caller must branch on: `{ ok: true, ... } | { ok: false, code: "limit-reached" | "duplicate" | "not-found" | "invalid" | "forbidden", message }`. Stable string codes, not booleans.
7. **Provider injection for anything crypto/network.** Inject `recoverAddress(message, signature)`, a `play(preset, volume)` fn, or a `fetch`/provider fn. Modules stay free of crypto and network imports so tests use deterministic mocks. Document the real wiring (e.g. secp256k1 `ecrecover`) in a doc-comment on the injected type.
8. **`import type` for all type-only imports** (isolatedModules is on; esbuild/vitest will otherwise keep runtime imports of erased types).
9. **Vitest (esbuild) is transpile-only — it will NOT catch a type error.** A test file that imports a type from a module that only `import`s (not `re-export`s) it still RUNS and PASSES; only `npx tsc --noEmit` flags `Module declares 'X' locally, but it is not exported [2459]`. If a test imports a type (e.g. `AlphaGroupAlert`) from a delivery module that pulls it in from a sibling, add `export type { X } from "./sibling"` to the module — keep `tsc` clean, don't rely on the green vitest run alone.

## Test conventions
- Vitest `describe/it/expect`, sibling `*.test.ts` next to the module. House style: dense scenario tests using fixed ISO timestamps via a local `T(minute)` helper (`new Date(Date.UTC(2026, 7, 13, 15, minute)).toISOString()`).
- Use `vi.fn()` spies for injected providers (e.g. assert exactly-one audio call).
- To pass an invalid literal into a closed-union typed param in a test, cast `"solana" as never`.
- Accessibility (UX-19): `jest-axe` + `@types/jest-axe` are dev deps. Render the component, `const results = await axe(container)`, assert `serious`/`critical` violations are `[]` (jsdom axe is structural/ARIA only — no color contrast). `jest-axe` ships no types, so `@types/jest-axe` is required or `tsc` flags the import as implicitly `any`.

## Verify before reporting done
```
npx vitest run src/lib/<dir>          # scoped run
npx eslint src/lib/<dir>              # must be 0 errors AND 0 warnings
```

## Pitfalls
- **Roadmap decisions must be PLAIN ENGLISH, not labeled jargon.** When presenting multi-option
  choices (the D1–D4 roadmap decisions, anything from ROADMAP.md), never lead with the option
  labels/acronyms. Emad's correction (2026-08-17): "bro i am too retarded to understand half of
  this shit, simplify it." Translate each option into its concrete outcome in one plain line
  (e.g. "watch another collection — you send me a link, no code"), keep it short, state a
  recommendation, and offer `clarify`/AskUserQuestion buttons — he prefers buttons. If a handoff
  prompt says "nothing is assigned", ask which decision he wants to move on; do NOT invent work.
- **"Don't build anything" + product direction = update the docs in place, nothing else.**
  When Emad gives UI/feature direction but says don't build (2026-08-17: alpha-groups panel to
  the center board slot, smart-wallet cluster buying, publish scoring rules on the site, eCalm
  gallery), record it in ROADMAP.md (e.g. a dated §10) plus a one-line header entry in
  START-HERE.md — no code, no deploy, no migration. The handoff protocol (pp.rtf continuation
  prompts) demands START-HERE.md be updated IN PLACE, never a new handoff doc.
- **Outbound alert webhooks: verify identity read-only before wiring.** Before any recurring
  Discord/webhook delivery, GET the webhook URL first (read name/channel_id/guild_id) to confirm
  which channel it targets — never post blind. Recurring outbound messages need an approval slate
  naming the exact channel and cancellation terms before the first test post.
- **Stay mechanical, not strategic.** When asked to build features or fix bugs, do NOT strategize about distribution, users, or business viability. The user corrected this explicitly (2026-08-15): "nix the distro strategy, work on all the mechanical parts that you were supposed to do. you aren't supposed to focus on any business stuff." Build what's asked; leave the "should we even build this?" conversation for IRC/iMessage, not the coding session.
- **Don't trust handoff docs on "dead code" claims.** The 2026-08-15 handoff flagged `avgPrice` in `live-data.ts`, `fmtEth` in `mint-terminal.tsx`, and the Next.js `/api/mints` route as dead. Investigation showed all three are actively used (avgPrice is computed and returned by `toLiveTrendingRow`; fmtEth is used at line 529 for smart-collections cost display and by fmtFloor/fmtVol/fmtIn; the Next.js route serves the frontend during SSR). Before deleting "dead" code, grep for its usage — the handoff's assessment can be wrong.
- `@typescript-eslint/no-unused-vars` uses `args: "after-used"`, so a trailing unused
  param is flagged EVEN with a `_` prefix. Fix by omitting the param entirely — a
  function with fewer params is assignable to the wider signature.
- Don't leave unused interfaces/imports; clean them before the final lint run.
- Next 16 APIs differ from older Next — don't hand-write route handlers from memory.
- `normalizeAddress`/`isValidAddress` require the literal lowercase `0x` prefix — `addr.toUpperCase()`
  yields `0X…` which fails the regex and returns null. To test case-insensitive matching, uppercase
  only the hex body: `` `0x${addr.slice(2).toUpperCase()}` ``.
- In provider-injected crypto/credential modules, a mock cipher that merely prefixes/suffixes the
  plaintext (e.g. `enc:${plaintext}`) embeds the secret as a substring of the ciphertext, so
  `expect(JSON.stringify(x)).not.toContain(secret)` still fails. Use a non-leaking reversible
  transform (reverse the string, or base64) so the "never exposes the secret" assertion is meaningful.
- Closed-union type guard idiom (used by `isReportModeration`): `typeof value === "string" &&
  (CONST as readonly string[]).includes(value)`. The `typeof` narrows `unknown` to `string` FIRST, so
  `.includes(value)` type-checks against `readonly string[]` without an extra `as T` cast.
- Secret non-exposure WITHOUT a cipher: for reports/credential views, make the secret an INTERFACE
  field that the pure fn never copies (`reporterSecret`). Interface fields don't trip `no-unused-vars`,
  and `JSON.stringify` of the result/state structurally cannot leak it. Prefer this over a mock cipher
  when the module only needs to "accept but discard".
- Transparent exclusions: when a value is rejected for being malformed, record the RAW input
  (`deployment.address || null` — empty->null, garbage->garbage) rather than collapsing to null, so the
  exclusion list stays auditable.
- State-CRUD test indexing: `state.reports`/`reports` ACCUMULATES across calls — after a second
  `submit`, `state.reports[0]` is still the FIRST record. Assert on `state.reports[1]` (or
  `result.report.id`) for the Nth item, not `[0]`.
- `prefer-const` fires on a single-assignment `let` (e.g. `let state = moderateReport(...).state;`
  that is never reassigned). Use `const` unless the variable is genuinely reassigned.
- `0n` BigInt literals fail under this repo's TS target (`< ES2020`): TS2737. Use the `BigInt(0)` /
  `BigInt(value)` constructor form — `mint-decode.ts`, `mint-group.ts`, and `windows.ts` all do.
- viem message recovery is async and lives at top-level `viem`: `recoverMessageAddress`/`verifyMessage`
  return `Promise` (they're utilities, not client actions); `privateKeyToAccount` is from `viem/accounts`.
  The injected `RecoverAddress` seam in `challenge.ts` is therefore async
  (`(message, signature) => string | Promise<string>`) and `verifyChallenge` returns
  `Promise<VerifyChallengeResult>`; the real provider is `src/lib/monitor/recover.ts`. A sync mock fn
  stays assignable, so existing mock tests only need `await` added — they remain deterministic.
- Indexer feed modules coalesce (DI-12 batching groups by chain+collection+block+standard+price class),
  so an ordering/dedup test that reuses one collection will silently collapse multiple facts into a
  single batch item and hide the assertion. Give each fact in an ordering/tie-break test a DISTINCT
  collection (or blockNumber) so they stay separate items.
- `D1CanonicalRepository` has NO write method for `sale_facts` (only a read: `listCanonicalSales()`).
  To seed sales in a durable-store test, use raw `db.exec(SQL)` on `SqliteD1TestDatabase` — `exec()` does
  not enable `foreign_keys=ON`, so seed rows need not pre-satisfy FKs (but `commitBlock`'s `batch()` DOES).
- The REST read seams are wired by `src/lib/indexer/wire-runtime-repositories.ts` (six setters, not seven —
  `bootstrap`/`events`/`all/stream` use `getRuntimeRepository()` + `globalThis.__MINT_FIELD_GUIDE_D1__`).
  For `runners`/`market` adapters, derive `now`/`version` from `getLatestBootstrap().generatedAt`/`.version`
  (deterministic, testable), never `Date.now()`. See `references/d1-read-wiring.md`.
- Parallel-subagent verification (this repo is driven by parallel `delegate_task` pushes): a child that
  reports `timeout` may have finished its edits before the 600s wall — `tail` its transcript
  (`~/.hermes/cache/delegation/live/<delegation_id>/task-N.log`) and check `git status` before
  re-dispatching. Always run the full gate yourself and trust the tree, not the self-report. Tell every
  child: never `git commit`/`add`/`clean`/`checkout`, and own a DISJOINT file set. See `references/integration-wiring.md`.
- **Git is GitHub-backed since 2026-08-15** (`andyemad/mint-field-guide`, private). The DRIVING
  session (you, after verification) may now `git add`/`commit`/`push` normally — that is the expected
  flow per START-HERE §2.1. Still NEVER `git clean`, `git reset --hard`, or force-push without real
  need. Children in parallel subagent pushes still never touch git (disjoint files; the parent commits).
  Note: the "never commit" rule you may remember applies only to the pre-GitHub zero-backup era.

- Full `vitest run` can fail NON-DETERMINISTICALLY (UNIQUE/FK/CHECK constraint errors in
  `d1-schema.test.ts`, `wire-runtime-repositories.test.ts`, `d1-sqlite.integration.test.ts`)
  because those tests drive the `sqlite3` CLI via synchronous `spawnSync`/`execFileSync` subprocesses
  that race under vitest's default parallel file execution. `vitest.config.mts` sets
  `fileParallelism: false` to serialize file execution — do NOT remove it, and expect the full
  suite to take ~70s rather than ~25s.

- Re-audit "partial" acceptance rows against the CURRENT code+tests before writing new tests: the
  matrix's partial list goes stale as later waves cover criteria (TR-07 reverted-volume exclusion was
  already covered by `if (!fact.canonical) continue` in buckets/windows; DS-15/16/17 and RS-09/10/13 were
  already passing). Grep the criterion keyword in the tests first, then write only the genuinely-missing test.
- Failure/recovery FR rows (FR-05/08/09/10/12) are usually already-correct-but-untested: the code
  fails closed / degrades / orphans, so the only work is adding the regression test — not changing impl.
  FR-09's "quarantine" is the per-block ATOMIC D1 batch (`native_value_wei NOT GLOB '*[^0-9]*'` CHECK),
  not a per-record partition. `mockRejectedValueOnce` on `getHead` is the idiomatic way to test
  all-RPCs-down cursor-freeze + resume. See `references/failure-recovery-fr-map.md`.
- Utility-NFT suppression (DI-08) is TWO layers: `src/lib/indexer/utility-filter.ts` (address-based
  `isUtilityCollection` + `partitionUtilityMints` audit-log partition, wired into `mint-feed.ts`) vs
  `src/lib/intelligence/utility-filter.ts` (name heuristics SBT/LP/vote-escrow/credential) — the indexer
  has no display name at decode time, so it is address-only.
- `DecisionStack` renders `LoadingSkeleton` on its first frame (a `useEffect` clears `loading` after
  `loadingDelayMs`). The first assertion after `render(<DecisionStack ... loadingDelayMs={0}>)` must use
  `await findBy*`, not `getBy*`, or it races the loading effect and throws. Same applies to the `error`
  prop path (loading → skeleton → error, in that order).
- Early-return null guards (`if (!view) return <Empty/>`) narrow a function PARAMETER for direct code
  but NOT into a nested closure declared inside the same component (e.g. an `async function copyContract()`).
  TS reports `'view' is possibly 'null'` INSIDE the closure only. Fix: capture the value into a `const`
  AFTER the guard (`const contract = view.contract;`) and reference that const in the closure — `const`
  bindings flow narrowing into closures, parameters do not.
- **Stray `>` after `.all() as { results: ... }`** — twice in one session (d1-repository.ts edits)
  the type assertion was written `} >;` / `} >;` and the LSP immediately flagged `Expression expected
  [1109]` + `Property 'results' does not exist on type 'boolean'`. It's a fat-finger on the closing
  `}>`; the fix is deleting the extra `>`. If you see those two diagnostics together after a repository
  edit, check the `as { results: ... }` line before anything else.
- **Don't create a test file whose name may already exist.** `src/lib/wallets/scoring.test.ts` ALREADY
  existed (3 tests, tracked in git) when a session overwrote it with new content, then deleted it —
  losing the originals until `git checkout -- src/lib/wallets/scoring.test.ts`. Before writing any new
  test/module file, check `git ls-files <path>` (or search_files target=files) first.
- **Emad's rule for this repo: don't modify test files.** When changing repo APIs, keep the old
  function names and make new params optional with defaults (`minTrackRecordSeconds = 0`) rather than
  editing the existing test suite. The full 854-test suite is expected to pass unchanged.

## Smart-wallet scoring (v2, shipped 2026-08-16)
Full detail in `references/smart-wallet-scoring-v2.md`. The headline facts:

- **Score = winRate × √matchedSells × sign(profit) × log2(1+|profit|)**, computed in
  JS after fetching 4× the page (`ORDER BY realized_native DESC LIMIT limit*4`), then
  re-sorted by score. Migration `0012` added `wins`/`losses` to `wallet_ledger`,
  counted per sell EVENT (a multi-unit sell in one tx = one win/loss; break-even counts
  as neither).
- **Qualification tightened**: `SMART_WALLET_MIN_MATCHED_UNITS` 4 → 10 AND
  `SMART_WALLET_MIN_TRACK_RECORD_SECONDS = 3600` (first_seen→last_seen span). Both
  routes (`/wallets`, `/smart-collections`) accept `minTrack` override; the response
  carries `minTrackRecordSeconds` so consumers can see the bar.
- **Cold-start trap (the important design lesson)**: wins/losses only accumulate from
  the moment migration 0012 ships, so historical sells have no win/loss split. Until
  evidence arrives, winRate falls back to neutral `0.5` and matchedSells uses the
  already-known `sell_units - unmatched_sell_units` — otherwise the leaderboard
  renders all-zero scores for weeks and looks dead. As counters fill, consistency
  takes over.
- **Backward compatibility**: all repo signatures kept the OLD names
  (`getTopWalletsByRealized`, not `getTopWalletsByScore`) and new params default
  (`minTrackRecordSeconds = 0`), because Emad's standing rule for this repo is
  **don't modify test files** — make the code change backward-compatible instead.
  The existing 854-test suite must pass untouched.

## Worker ingestion / D1 (go-big aggregate-forward, 8/14)
Full architecture + cost model + verification in the repo's `GO-BIG-HANDOFF.md` and
`research/FULL-COVERAGE-DESIGN.md`; the reusable pitfalls (all hit live this session):

- **Per-chain feed wipe (the "no mints from robinhood" bug).** `commitRecentFeed` must
  scope its DELETE by chain: `DELETE FROM mint_facts WHERE canonical=1 AND chain_id=?`.
  A delete-all-then-insert feed, run per chain, lets the LAST chain wipe the others —
  Ethereum ran after Robinhood and erased the whole feed (site showed only ~26 ETH
  mints). Also order the feed by `observed_at` (NOT `block_number` — chain block
  numbers are incomparable: Robinhood ~36M vs Ethereum ~25M, so block order is not
  recency).
- **`eth_getLogs` block-range caps are per-provider**: Robinhood/arrowrpc rejects
  ranges > 1000 (`-32005: block range N exceeds max 1000`); Alchemy FREE tier caps at
  **10 blocks**. `GETLOGS_CHUNK` is a per-chain record `{ robinhood: 1000, ethereum: 10 }`.
- **D1 `batch()` = max 100 statements** → chunk with an `executeInChunks(statements)`
  helper (slice 100, await each).
- **D1 STRICT tables**: TEXT columns with `NOT GLOB '*[^0-9]*'` CHECK reject INTEGER
  sums — wrap as `CAST(CAST(a AS INTEGER) + CAST(b AS INTEGER) AS TEXT)`.
- **D1 hard cap of 100 bound variables per statement** (verified live 8/23): an
  `IN (?,...)` chunk of 100 addresses PLUS a `chain_id=?` bind = 101 vars →
  `D1_ERROR: too many SQL variables`. Chunk address lists at **99**, not 100,
  wherever one extra scalar bind rides along (`filterKnownCollections` hit this).
- **Binding a JS number into a digits-only TEXT column stores REAL text**
  (verified live 8/23): a raw number bound into `native_volume_wei` landed as
  `"1e+21"`-style REAL text and tripped the `NOT GLOB '*[^0-9]*'` CHECK on
  every commit. Fix: `BigInt(value).toString()` coercion at BOTH write sites
  (`bucketStatement` + `upsertBucketStatement`). Never trust callers to hand
  you a string — coerce at the bind.
- **arrowrpc 429s come in multi-second burst windows** (verified live 8/23):
  sub-second backoff (800ms×4 attempts) burned every retry inside the same
  window and failed whole chains. Working tuning now in `FetchJsonRpcClient.requestBatch`:
  **6 attempts, `sleep(1500 * (attempt + 1))`** — post-fix cycles ran clean
  (831 facts / 0 rpc failures) where the old tuning 429'd.
- **Flaky full-suite runs still happen even with `fileParallelism: false`**
  (seen again 8/23): one run showed 5 files / 16 tests failing with UNIQUE/FK/
  CHECK constraint errors; the immediate rerun of the SAME suite passed
  everything, and each "failed" file passed in isolation. Before debugging,
  rerun once — if the failures are constraint-stepping errors in the sqlite-
  subprocess integration tests and a rerun is green, it was the known flake.
- **`minute_buckets.mint_count` counts EVENTS** (`+= 1` per fact), not summed quantity —
  ERC1155 mega-batches inflated momentum to +964,803,852. If you ever change the
  aggregation semantics, DELETE existing `minute_buckets` + `minute_bucket_minters`
  once (otherwise old quantity-sums mix with new event counts).
- **Block-time estimation** (measure cadence from head + one anchor block ~500 back,
  timestamp every mint without a per-block `getBlock`) is what makes full-chain coverage
  viable: per-block getBlock blows the ~30s wall-clock and 1000-subrequest budgets at
  ~610 blocks/min. Verified accuracy <0.5s.
- **D1 cost model (honest numbers)**: Workers Paid includes 50M rows written/mo
  ($1/M after); **DELETES count as writes**, so a retention trim doubles the bill
  (~$34/mo overage on top of $5); full raw coverage of Robinhood is ~2–5M mints/day
  (measured 2.5–6.5/block, not the old "1.6") — storing every row is NOT "$5/mo".
  Aggregate-forward (minute_buckets + bounded 1000-row feed, facts-only, no
  canonical_blocks FK) is the cheap shape. The `mint_facts`→`canonical_blocks` FK was
  dropped in migration 0002 to make that possible.

## Related
- `references/monitor-alerts-modules.md` — the established `src/lib/monitor` + `src/lib/alerts` architecture and the AP-xx acceptance-point map.
- `references/enrichment-risk-modules.md` — the `src/lib/enrichment` collection-risk layer (EN-07/09/10: reports, honeypot, deployer-projects) with exact interfaces and invariants.
- `references/mint-feed-module.md` — the `src/lib/indexer/mint-feed.ts` New Mints feed (DI-09..14) + `src/app/api/mints` route: pipeline, DI map, and test pitfalls.
- `references/d1-read-wiring.md` — how the six REST read seams (mints/trending/runners/market-snapshot/status/search) wire to `D1CanonicalRepository` via `wireRuntimeRepositories()`: exact setters, read methods, adapter clock/version source, and the search/status limitations.
- `references/integration-wiring.md` — the WRITE side (raw logs → decoders → `persistent-worker.ts` → facts; three-way `MintClassification`) + parallel-subagent verification rules (timeout ≠ failed, disjoint file ownership, never commit/clean).
- `references/decision-stack-component.md` — the DecisionStack UI (`src/components/decision-stack/`): shell structure, exported pure helpers, state/persistence, fixture windows, jest-axe + empty/error state patterns, and the DI-08 utility-filter note.
- `references/failure-recovery-fr-map.md` — FR-05/08/09/10/12 failure/recovery acceptance rows mapped to code + test, with test recipes (mockRejectedValueOnce cursor-freeze, D1 CHECK quarantine, per-field unavailable).
- `references/mint-terminal-ui.md` — the home-page UI (`src/components/mint-terminal/`): MintGo gesture spec (desktop three-column board + featured mint module; mobile tabs), sortable ranked market table, time/chain/volume filters, live feed, dark-theme tokens, fixture data + simulated live tick, and both "parity = visual" corrections.
- `references/next16-metadata-font-conventions.md` — VERIFIED Next 16.3 facts for this repo: the `favicon` file convention is `.ico`-ONLY (a `src/app/favicon.png` is silently ignored → rename to `icon.png`; delete the default `favicon.ico` or it wins the `<link>` order), non-convention files in `src/app/` are NOT served (`public/` only), and `next/font/google` `weight: "variable"` is build-safe even for multi-axis fonts. Includes the exact node_modules files to re-check when the Next version bumps.
- `references/aggregate-forward-worker.md` — the go-big worker ingestion (`ingestChainCatchup`: cursor + per-chain getLogs chunking + block-time estimation + minute_bucket aggregation + bounded per-chain feed), the feed-wipe bug + fix, D1 cost reality (50M writes/mo, deletes-as-writes, FK drop), and the verified deploy/verify sequence. Repo specs: `GO-BIG-HANDOFF.md`, `research/FULL-COVERAGE-DESIGN.md`.
- `references/smart-wallet-scoring-v2.md` — the composite smart-wallet score (winRate × √matched × sign × log2(1+|profit|)), the v1 weaknesses that drove it, migration 0012 wins/losses, the cold-start neutral-winRate design, qualification constants, and the verified deploy sequence.
- eCalm Suites rebrand (2026-08-14): the design-system spec lives at `research/ECALM-BRAND-SYSTEM.md` in the repo — brand tokens (success sage #B5C99A, warning mauve #D4A5A5, info sky #9FD9EC, hot peach #FFCBA9, cool→warm banner gradient), header lockup (logo + Caveat script wordmark + Fraunces small-caps tagline), favicon fix steps, and the class keep/rename plan for `mint-terminal.module.css`. Status semantics: success=green, warning=pink, info=blue — no neon accents, no toast overlays. Before writing any frontend spec/doc, run `git status`: parallel waves may have already landed UNTRACKED brand assets (public/ecalm-logo.png, src/app/ecalm-banner.svg, src/app/favicon.png) that your spec must stay consistent with instead of re-specifying from scratch.
- `references/alpha-group-webhook-delivery.md` — server-side Discord webhook delivery of alpha-group alerts (SHIPPED 2026-08-17): migration 0014 snapshot table, `alpha-group-delivery.ts`, `DISCORD_WEBHOOK_URL` secret, cron wiring, deploy+verify sequence, webhook-channel-check pitfall.
- `references/alpha-group-acquisition-source.md` — split the alpha-group "buying" count by acquisition SOURCE (mint paid/free vs secondary buy): migration 0018 per-source timestamps, `stampAcquisitionSource`, source-aware headline `funkari minting (2/2) · buying on secondary (1/2)`, Emad's headline-format decision, and the staged-then-deploy path.
- `references/` is also the right home for any future module-spec notes for this repo.
- `references/sale-sided-discovery.md` — the sale-side ERC721 discovery leg
  (`getTransferContractAddresses` + `filterKnownCollections` +
  `discoverSaleSidedCollections`): why unfiltered sweeps are needed, the three
  guards (interval throttle / per-chain scan blocks / resolve cap), and verified
  live numbers. `scripts/live-rpc-smoke.mjs` is the runnable live probe.

## Interrupted-subagent recovery (gateway died mid-build)
When a session (or gateway) dies while a subagent build is in flight, do NOT
re-dispatch blindly — the work may be nearly or fully done:
1. `git status --short` + `git diff --stat` in the repo: staged/untracked files
   show exactly which tasks landed (e.g. T3's rpc-source.ts + worker/index.ts edits).
2. Grep the diff for the task's key symbols to confirm completeness, not just presence.
3. Run the full gate yourself (tests → lint → build) — trust the tree, never the
   dead agent's last progress message.
4. For RPC-touching engines add a LIVE smoke probe of the real call shape against
   the real provider (`scripts/live-rpc-smoke.mjs`) — mocked tests passing proves
   nothing about provider acceptance. Verified 2026-08-23: 1,000-block unfiltered
   sweep on Robinhood = 12,832 logs / 261 contracts, no -32005.
5. Report what was already done vs what remains; don't rebuild landed work.
Also: this repo has NO `npm run check` script — the gate is
`npm run test:run` + `npm run lint` + `npm run build` (~306s full suite).

## Production verification (deploy is not done)
The gate proves the build; the DEPLOY proves the engine. After every
`npx wrangler deploy`:
1. Wait ≥2 cron ticks (~4 min), then `curl .../health` and parse `lastCron`.
   `ok:false` with per-leg summaries is normal diagnostics — read each leg.
2. Known-good steady state: robinhood facts in the hundreds, rpcFailures low,
   discovery either runs clean or `{skipped:true,reason:"interval"}` (it
   throttles to one sweep per 30 min), max-supply reports checked/resolved,
   ethereum clean. Any leg error persisting across 2+ cycles = real bug.
3. The billing blocker ("Workers Paid required") was STALE as of 2026-08-23 —
   deploys succeed on the free account (<operator-email-redacted>). Don't cite it;
   verify with an actual `wrangler deploy --dry-run` before treating anything
   as blocked on billing.
