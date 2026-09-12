# D1 read-repository wiring (REST read seams → durable store)

How the six REST read routes are wired to `D1CanonicalRepository`. The durable
store is the canonical event store (`migrations/0001_canonical_event_store.sql`);
`bootstrap_snapshots.snapshot_json` holds the latest versioned `BootstrapSnapshot`.

## The six read seams (exact setter + interface)

| route | setter | interface method | data source |
|---|---|---|---|
| `src/app/api/mints/route.ts` | `setMintsReadRepository` | `getCanonicalMints(): Promise<MintFact[]>` | `mint_facts WHERE canonical=1` |
| `src/app/api/trending/route.ts` | `setTrendingReadRepository` | `getLatestTrending(): Promise<PersistentSnapshotSet \| null>` | `getLatestBootstrap().trending` + `.version`/`.generatedAt` |
| `src/app/api/runners/route.ts` | `setRunnerReadRepository` | `getRunnerSnapshots(): Promise<RunnerSource \| null>` | `minute_buckets` + `minute_bucket_minters`, clocked by bootstrap |
| `src/app/api/market-snapshot/route.ts` | `setMarketSnapshotReadRepository` | `getMarketSnapshot(): Promise<MarketSource \| null>` | `sale_facts WHERE canonical=1`, clocked by bootstrap |
| `src/app/api/status/route.ts` | `setStatusRepository` | `snapshot(): Promise<ChainStatusSnapshot[]>` | cursors + head blocks + `chainFreshness` |
| `src/app/api/search/route.ts` | `setSearchRepository` | `list(): Promise<SearchRecord[]>` | distinct `collection` addresses (mints + sales) |

There are **six** setter seams, not seven. The `bootstrap`, `events`,
`all/stream`, and `all/bootstrap` routes use a *different* mechanism
(`getRuntimeRepository()` + `globalThis.__MINT_FIELD_GUIDE_D1__`, declared in
`runtime-repository.ts`) — out of scope for the setter wiring.

## Wiring entrypoint

`src/lib/indexer/wire-runtime-repositories.ts` exports
`wireRuntimeRepositories(database: D1DatabaseLike, options?: { nowSeconds?: () => number }): D1CanonicalRepository`.
It builds one `D1CanonicalRepository`, maps each interface onto it, calls every
setter, and returns the repository. It imports route modules from `@/app/api/*`
(a lib → app dependency, which is acceptable here and has no cycles).

## Read methods added to `D1CanonicalRepository`

- `getCanonicalMints()` — every canonical fact, both chains (no `chain_id` filter).
- `listCanonicalSales(): Promise<SaleFact[]>`.
- `listMinuteBuckets(): Promise<MinuteBucket[]>`.
- `listMinuteBucketMinters(): Promise<MinuteBucketMinter[]>`.
- Private `mintFactFromRow(chain, row)` shared with `listCanonicalFactsAfter`.
- Reverse chain lookup: `CHAIN_BY_ID: Record<number, DataChain>` + `chainFromId(chainId)`
  (forward is `CHAIN_IDS: Record<DataChain, number> = { ethereum: 1, robinhood: 4663 }`).

`observed_at`/`minute_start`/`rebuilt_at`/`block_time` are stored as epoch
SECONDS — map back with `new Date(Number(row.x) * 1000).toISOString()`.

## Adapter clock/version source (key decision)

`runners` and `market` adapters need `now` (Date) and `version` (string). Derive
BOTH from the latest bootstrap: `now = new Date(snapshot.generatedAt)`,
`version = snapshot.version`. This is deterministic (testable with a fixed clock)
and consistent with what the bootstrap was built from. If there is no bootstrap,
the adapters return `null` → routes 503. Do NOT call `Date.now()` inside these
adapters; the status adapter is the exception (its `snapshot()` takes no clock,
so it accepts `options.nowSeconds` defaulting to wall clock).

## Documented gaps (honest limitations, not bugs)

- **Search**: the canonical store has no enrichment name/slug table. The wired
  `list()` returns `{ chain, address, name: null, slug: null }` per distinct
  collection, so address-prefix search works but name/slug substring matching
  returns nothing.
- **Status**: no persisted stream pause/stop or downstream health. Proxies:
  `streamState = cursor ? "running" : "stopped"`; `enrichmentHealthy` /
  `marketHealthy` derived from `bootstrap.chainFreshness[chain].status`
  (`"healthy"`→both true, `"degraded"`→enrichment true/market false,
  `"unavailable"`→both false). `lastCanonicalBlock = cursor?.blockNumber ?? -1`.
  Missing head block / bootstrap use a `STALE_SECONDS = 1_000_000` sentinel to
  trip the route's own 300s/600s thresholds.

## Testing pattern

Use the local D1-compatible adapter `SqliteD1TestDatabase` (no real D1) — same
setup as `d1-sqlite.integration.test.ts`:
`instance.exec(readFileSync(join(process.cwd(), "migrations/0001_canonical_event_store.sql"), "utf8"))`.

- Seed `mint_facts`/`canonical_blocks`/`chain_cursors` via `repository.commitBlock(...)`.
- Seed `sale_facts`, `minute_buckets`, `minute_bucket_minters` via raw
  `db.exec(SQL)` — **there is no `D1CanonicalRepository` write method for
  sales**, so raw SQL is the only way. `exec()` does NOT enable
  `foreign_keys=ON` (that pragma is per-connection and only the migration file
  sets it), so seed rows need not pre-satisfy FKs — but `batch()` (used by
  `commitBlock`) DOES enable FKs.
- Seed a bootstrap via `repository.saveBootstrap(bootstrap())` with a
  `streamCursor` matching `/^[a-zA-Z0-9_-]+:(0|[1-9][0-9]*)$/` (e.g. `"test-epoch:0"`);
  empty `runners: []` keeps `validateAtomicVersions` happy.
- End-to-end: `wireRuntimeRepositories(db, { nowSeconds: () => sec(NOW) })`, then
  call each route's `GET` (alias the six colliding `GET` imports) and assert 200.

Verify: `npx vitest run src/lib/indexer` · `npx eslint <files>` · `npx tsc --noEmit`.
