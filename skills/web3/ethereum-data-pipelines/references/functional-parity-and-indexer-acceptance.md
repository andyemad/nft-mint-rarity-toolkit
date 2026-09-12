# Functional Parity and Persistent Indexer Acceptance

Use when building an independent alternative to a live NFT/mint intelligence product.

## Separate parity from appearance

Treat parity as a testable feature matrix, never one subjective percentage. Score and verify these surfaces independently:

1. Data-source coverage and provenance
2. Live-mint discovery and event classification
3. Historical/trending windows
4. Runners, marketplace sales, and floor semantics
5. Collection identity and deployer enrichment
6. Upcoming-stage completeness and provenance
7. REST snapshots, streaming, reconnect, replay, and repair
8. Alerts, blocklists, dedupe, and persistence
9. Wallet connection, simulation, confirmation, and receipts
10. Smart-wallet backtests, samples, confidence, and uncertainty
11. Desktop/mobile workflow acceptance

A populated request-time RPC scan can be near-parity for recent discovery while overall product parity remains low because it cannot provide durable trends, replay, alerts, or history. Report deployed and local capabilities separately.

## Anti-clone design gate

A complaint that the reference feels more fluid is not permission to copy its visual composition. Preserve interaction qualities—compact navigation, immediate filters, high viewport utilization, progressive detail, and rapid scanning—while changing the information architecture, component hierarchy, typography, navigation treatment, motion, and product motif.

Run two independent gates:

- **Workflow gate:** representative tasks are fast and legible on desktop and mobile.
- **Originality gate:** the result is structurally distinguishable from the reference, not merely recolored.

Direct user judgment overrides an automated or blind critic's originality pass. If the user says it looks too similar, invalidate that gate and redesign structurally rather than defending the score or changing only colors.

## Canonical event foundation

Persist once and serve snapshots; do not fan out broad RPC scans per visitor.

Minimum entities:

- chain cursor and canonical block hash
- raw log with chain-qualified identity
- normalized mint, sale, and stage facts
- canonical/orphan state
- minute bucket
- materialized rolling snapshot
- append-only stream event and replay cursor
- enrichment job with provenance and retry state

### Reorg acceptance

- Ingestion is idempotent for the same block and fact IDs.
- Chain cursors and facts are isolated by chain.
- A child with a mismatched parent fails closed.
- Recovery walks retained history backward until local and remote hashes agree.
- Invalid remote chain/height data fails closed.
- If no retained common ancestor exists, stop and require a bounded resync.
- **Preflight the entire replacement branch before mutating local state:** verify chain, contiguous heights, parent linkage, fact-to-block provenance, timestamps, and settlement policy. A malformed replacement must leave blocks, facts, and cursor byte-equivalent to their prior state.
- Compute the dirty-minute set from the union of displaced canonical facts and incoming replacement facts. Rollback marks displaced facts noncanonical/orphaned, rewinds the cursor, ingests the preflighted branch, recomputes settlement, and rebuilds only that dirty set before publishing snapshots.
- Keep recovery orchestration independent from storage mechanics: use an in-memory reference implementation to prove transitions, then require persistent-adapter conformance for the same fixture tape.

### Rolling-window acceptance

Materialize 1m, 5m, 10m, 15m, 30m, 1h, 4h, 6h, 12h, and 24h independently per chain. Aggregate canonical facts only. At minimum expose mint quantity, transaction count, unique minters, native volume, and latest observation. Define interval boundaries explicitly and test events exactly at cutoff and snapshot time. Use deterministic tie-breaking so replay produces identical rankings.

### RPC failover acceptance

Use a bounded, ordered source list. Validate it at construction time: at least one endpoint, no duplicates, and HTTP(S) URLs only. For each request:

- try sources in configured order;
- reject JSON-RPC error objects and malformed “success” responses lacking `result`;
- return the selected source, prior failures, and an explicit degraded flag when fallback succeeds;
- if every source fails, return one bounded aggregate error naming the method and source count, **not request parameters**, credentials, provider response bodies, or URLs containing secrets;
- retain per-source reasons internally for status/diagnostics, but redact before public output.

Tests should prove order, malformed-response failover, selected-source evidence, and parameter non-disclosure.

### Persistent SQL/D1 conformance

Use a D1/SQLite-compatible migration as an executable contract, not just documentation. The minimum durable schema should include chain configuration, canonical blocks, raw logs, normalized facts, chain cursors, settlement state, and minute buckets.

Conformance requirements:

- Every identity is chain-qualified; the same height or address may coexist across chains.
- Keep all fork variants by `(chain, block_hash)`, but enforce one canonical block per `(chain, height)` with a partial unique index.
- Keep raw-log and normalized-fact fork variants, but enforce one canonical version per `(chain, tx_hash, log_index)`.
- Cursor rows must foreign-key the exact canonical block identity. Enable `PRAGMA foreign_keys = ON` on **every SQLite connection**, not only inside the migration; SQLite connection settings do not persist across CLI/process connections.
- Advance block, raw logs, normalized facts, buckets, and cursor in one transaction. A forced cursor failure must roll back the inserted block and facts.
- Reorg rollback retains orphaned rows for audit, marks them noncanonical/orphaned, rewinds the cursor, and rebuilds only affected minute buckets before replacement-branch snapshots publish.
- Store wei and other base-unit quantities as validated decimal text when the SQL runtime cannot safely represent 256-bit integers.
- Model `provisional`, `settled`, `finalized`, and `orphaned` explicitly. Reject facts ahead of the canonical head and policies where settlement depth exceeds finality depth.

Test the migration against a fresh temporary SQLite database. Expected constraint violations may print to stderr even when the test correctly catches them; judge the process exit and post-transaction database state, not stderr silence.

## Strict TDD tracer bullets

Implement vertical slices in this order:

1. Idempotent canonical ingestion
2. Parent mismatch detection
3. Orphan rollback and replacement branch
4. Common-ancestor discovery
5. One rolling-window aggregate
6. All supported windows and deterministic ranking
7. Persistent adapter conformance against the in-memory reference

For each slice, run the focused test and confirm the expected RED before production code, then GREEN, then the full suite/lint/build. A boundary-test failure should lead to an explicit interval definition, not an arbitrary assertion change.

## Production honesty

Do not claim 100% parity until the full acceptance matrix passes end to end. HTTP 200, schema validity, a polished interface, or current mint rows are not evidence for historical, streaming, alert, transaction, or wallet parity. Missing enrichment remains missing, and wallet/mint success is not reported before authoritative chain confirmation.
