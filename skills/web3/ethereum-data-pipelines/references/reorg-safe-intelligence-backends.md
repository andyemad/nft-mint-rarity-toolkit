# Reorg-safe NFT intelligence backend patterns

Use this note when a mint/NFT dashboard needs durable indexing, rolling rankings, replayable streams, or marketplace sales.

## Canonical persistence

- Key event identity by `(chain, transaction hash, log index)` but retain versions by block hash. A reorg can replace an event at the same logical identity; orphan and replacement versions must coexist for audit.
- Enforce only one **canonical** version with a partial unique index. Never delete orphaned facts.
- Keep canonical blocks, raw logs, normalized mint facts, normalized sale facts, chain cursors, settlement state, buckets, and affected membership rows in one transactional recovery path.
- Advance a cursor only after all block/fact/bucket writes in the same checked D1 batch. Validate every D1 batch result; do not assume `batch()` success from transport alone.
- SQLite foreign keys are connection-local: enable `PRAGMA foreign_keys = ON` for every test/runtime connection.
- Store exact base-unit quantities as decimal text with a strict non-empty unsigned-integer constraint. SQLite `NOT GLOB '*[^0-9]*'` alone accepts the empty string; combine it with `length(value) > 0`. Test `''`, signed values, decimals, and alphabetic input at the migration boundary.

## Recovery and restart safety

1. Fetch bounded, contiguous ranges starting at stored cursor + 1.
2. Before declaring a worker caught up, fetch the remote block at the durable cursor height and compare its hash. A same-height tip replacement otherwise produces an empty ingestion loop and silently preserves an orphaned local tip.
3. If the remote head is behind the durable cursor, fail closed and report source lag; never rewind canonical state from a lagging provider.
4. Stop on gaps; never skip a missing height.
5. On parent or cursor-hash mismatch, find the actual retained common ancestor from durable canonical history.
6. Preflight the entire replacement branch—including block continuity, raw-log ownership, fact ownership, timestamps, settlement inputs, and dirty-minute materialization—before mutation.
7. In one durable transaction: orphan displaced blocks, raw logs, and facts; insert replacement blocks/logs/facts; replace dirty buckets and minter membership; then advance the cursor. Raw logs and normalized facts must share the transaction so no committed fact lacks reproducible provenance.
8. Recompute canonical settlement only after successful ingestion/recovery. Settlement promotion must exclude orphan audit rows and must not run after a failed block transaction.
9. Replaying after interruption must be idempotent.

### Repository boundary

Use one asynchronous repository contract for in-memory tests and D1/runtime implementations. It should expose durable cursor reads, bounded canonical-block history for ancestor lookup, canonical facts after a lower bound, atomic block commits, atomic recovery commits, and settlement promotion. The worker must not maintain a second authoritative cursor outside this repository.

For D1-style batches, validate every result and its result count. A transport-level success is not proof that every statement succeeded. Integration tests should inject failures after block, raw-log, fact, bucket, and cursor stages and prove full rollback plus restart-safe replay.

## Rolling windows

- Use start-exclusive/current-time-inclusive boundaries: `observedAt > start && observedAt <= now`.
- Supported windows: 1, 5, 10, 15, 30, 60, 240, 360, 720, and 1440 minutes.
- Do not sum minute-level `uniqueMinters`; retain normalized `(chain, minute, collection, minter)` membership and count distinct wallets across the requested window.
- Rebuild only minutes affected by a reorg.
- Give every all-window snapshot one version, generated time, formula/schema version, and source-through-block metadata. Reject mixed versions.
- Runner change compares adjacent equal-duration windows. If prior history is unavailable or zero, return an explicit unavailable baseline rather than fabricated percentage growth.

## Snapshot and stream contracts

- Bootstrap atomically returns both chains, bounded recent mints, selected trend/runner windows, per-chain freshness, schema version, and the exact stream cursor.
- Cursor pagination must be stable and version-bound. Reject stale-version cursors rather than mixing snapshots.
- Replay IDs are monotonic within an epoch. Retain idempotency keys, chain identity, snapshot version, and emitted time.
- When a requested cursor predates retained replay history or uses another epoch, require snapshot repair.
- SSE protocol fields must reject CR/LF/NUL injection. Encode payload as one JSON data line.
- Patch application is idempotent by patch ID and requires an exact base version; otherwise repair from an authoritative snapshot.
- Maintain an exhaustive typed event union so unknown server event classes fail closed.

## Enrichment and marketplace boundaries

- Enrichment patches may change identity/risk evidence only; canonical counts and rank inputs must be structurally immutable.
- Any non-null enriched field requires source and observation time.
- Never infer a sale from an NFT transfer. Normalize only verified marketplace fills.
- Store sale amounts in exact base units with token address and decimals. Never sum unlike tokens without timestamped FX provenance.
- Sale facts need the same block-hash versioning, canonical uniqueness, settlement states, and orphan retention as mint facts.
- For Seaport-style fills, normalize buyer, seller, NFT, quantity, consideration token, gross amount, fees, transaction/log provenance. Reject mixed-payment fills instead of inventing a single volume.

## Verification discipline

Use strict TDD for each contract: focused failing test, minimal implementation, focused pass, then full test/lint/production-build gate. A focused pass does not override a failed TypeScript production build. Avoid BigInt literal syntax when the project target is below ES2020; use `BigInt(0)`/`BigInt(1)` or raise the target deliberately.
