# Failure/recovery acceptance rows (FR-05/08/09/10/12) — code→test map (verified 2026-08-13)

How "verify and close FR rows" resolves against the failure/recovery modules. The
recurring pattern: the CODE is already correct (fail-closed, degrade, orphan); the
only genuinely-missing thing is usually a regression test. Grep the criterion keyword
in the tests first — most rows are already covered and only need a verdict, not new code.

## FR-05 — all RPC sources unavailable
Behavior: worker must NOT advance the cursor when the head fetch fails; retain the
last-good snapshot; resume from the same block once the source recovers.
Where it lives: both `worker.ts` (`ChainIngestionWorker`) and `persistent-worker.ts`
(`PersistentChainWorker`) call `source.getHead()` FIRST, so a rejection short-circuits
`run()` before any commit. No impl change needed.
Test recipe:
  - `const src = source(blocks)` then `src.getHead.mockRejectedValueOnce(new Error("all N RPC sources failed for eth_blockNumber"))`.
  - Assert `run()` rejects, cursor / `commitBlock` unchanged, then a second `run()`
    (healthy again) resumes and commits exactly the missing block(s).

## FR-08 — partial degradation / stale market
Already covered by `src/app/api/status/route.test.ts` ("reports partial degradation
naming the stale market component, never healthy" + per-component `evaluateChainHealth`).
No change.

## FR-09 — malformed upstream data
The "quarantine a bad record" boundary is the PER-BLOCK ATOMIC D1 batch, NOT a
per-record partition. `D1CanonicalRepository.commitBlock` runs one
`BEGIN IMMEDIATE … COMMIT` (via `SqliteD1TestDatabase.batch`); the
`mint_facts.native_value_wei NOT GLOB '*[^0-9]*'` CHECK rejects a malformed fact,
failing only that block's batch. Prior valid blocks stay committed and the cursor
stays at the last good block. Don't over-engineer a per-record quarantine — it isn't
what the architecture does.
Test recipe (`persistent-worker.mint.integration.test.ts`): real
`D1CanonicalRepository`; source returns 2 valid + 1 malformed
(`nativeValueWei: "not-a-base-unit"`) blocks; assert `run()` rejects with
`/SQLite batch failed|CHECK constraint/`, `listCanonicalFactsAfter(chain, -1)` returns
only the 2 valid facts, and `getCursor` == the last good block. Note `-1` is a legal
lower bound for `listCanonicalFactsAfter`.

## FR-10 — reorg during active UI
Already covered: `store.test.ts` (`rollbackTo` orphans + excludes from
`getCanonicalMints`), `recovery.test.ts` (`recoverCanonicalBranch` orphaned ids +
`dirtyMinuteStarts`), `d1-schema.test.ts` (settlement=`orphaned`). No change.

## FR-12 — enrichment 404 / 429 / timeout
Every adapter already `catch`es provider errors and returns
`field: unavailable(...)` + `error` — never a fabricated value. The gap was only tests
for the SPECIFIC error classes. Added: floor (404/429/timeout), price
(404/429/timeout), identity (rate-limit/timeout) — assert `field.value === null` and
`provenance.status === "unavailable"`.
Gotcha: `FieldStatus` is only `available | unavailable`; "stale" is a value-level state
inside `PriceState`/`FloorState`, not a field status — so "per-field unavailable/stale"
means two different layers and should not be conflated in a single assertion.
