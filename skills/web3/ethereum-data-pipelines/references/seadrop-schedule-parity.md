# SeaDrop upcoming-schedule parity (verified 2026-08-13)

Verified while building the mint-field-guide Upcoming/Schedules acceptance slice (SC-01–SC-09 foundations, plus SC-11/SC-12 schedule alerts + stage lifecycle).

## Event identity (the part that is easy to get wrong)

`PublicDropUpdated(address indexed nftContract, (uint80,uint32,uint32,uint32,uint16,bool) publicDrop)`

- **topic0 (event signature hash)**: `0x8764214b5defe9caa9c5b38b36f0cc5e482a8ab15d78696659e61989e48e6e70`
  - Compute it with `python3 -c "from Crypto.Hash import keccak; k=keccak.new(digest_bits=256); k.update(b'PublicDropUpdated(address,(uint80,uint32,uint32,uint32,uint16,bool))'); print('0x'+k.hexdigest())"` (needs `pip install pycryptodome`). Do NOT hand-invent a placeholder hash — a wrong topic0 silently rejects every real log.
- **topic1** is the NFT contract, left-padded to 64 hex chars: `0x000000000000000000000000<40-hex-address>`. Validate length `^0x[0-9a-fA-F]{64}$` AND the zero-address prefix before slicing the last 40 chars.
- **data** = exactly 6 ABI words (32 bytes each), in order: `mintPrice (uint80)`, `startTime (uint32)`, `endTime (uint32)`, `maxTotalMintableByWallet (uint32)`, `feeBps (uint16)`, `restrictFeeRecipients (bool)`.

## Zeroed-field semantics (protocol defaults, never fabricate)

ABI zeros mean "unset", not a real value:

| Field | 0 maps to | Reason |
|---|---|---|
| mintPrice | `"0"` → price class **free** | zero known price is free |
| startTime / endTime | `null` (unknown) | drop may not be time-boxed |
| maxPerWallet | **unlimited** (distinct state) | 0 = protocol unlimited |
| feeBps | 0 (real value) | fee can legitimately be 0 |
| restrictFeeRecipients | false | bool has no null |

## Derived classifications (three states each, never collapse)

- **Price**: `"0"` → free; positive integer string → paid; `null`/malformed → unknown.
- **Max per wallet**: `0` → unlimited; positive integer → limited (1 is limited, not unlimited); `null` → unknown.
- **Status** (UTC seconds, half-open `[start, end)`): `now < start` → upcoming; `start <= now < end` → live (exact start = live); `now >= end` → ended (exact end = ended); either time missing → unknown.
- **Seven-day horizon**: include only upcoming/live stages whose `end <= now + 7d` AND `end > now`; horizon end boundary is **inclusive**. Unknown times are excluded from horizon (no indefinite display).

## Latest-config projection

Keep the latest update per `(chain, nftContract)` keyed by `(blockNumber, logIndex)` — a newer orphaned update must not win; two updates at the same block resolve by log index. Same hex address on different chains is a separate record (chain prefix keys).

## Cache + route contract

- Ten-minute TTL cache (`+9:59` reuses, `+10:00` refreshes), explicit `invalidate()` for stream patches (`GET /api/seadrop-radar?invalidate=1`).
- Route returns 503 `SCHEDULE_UNAVAILABLE` on source failure; `cache-control: no-store`; provenance per stage (`onchain` vs signed/allowlist) — a signed source must never claim on-chain provenance.
- Keep the shared cache getter in its own module (`schedule-cache.ts`) so route tests can `vi.mock` it — same pattern as `runtime-repository.ts` for bootstrap. A singleton inside the route file is not mockable.

## TypeScript pitfalls hit while building this slice

- **BigInt literals (`0n`) fail when `tsconfig` targets < ES2020**: use `BigInt(0)` / `BigInt(n)` constructor everywhere, including tests. This repo targets below ES2020; the error is `TS2737: BigInt literals are not available when targeting lower than ES2020`.
- **`interface X extends Y {}` (empty body) trips `@typescript-eslint/no-empty-object-type`**: use `type X = Y` instead.
- Address literals in fixtures must be exactly 40 hex chars; a 38-char "abcdef…" fixture fails the `{64}$` topic regex with a confusing "malformed" error. Generate/verify with `node -e "const a='abcdef'.repeat(6)+'abcd'; console.log(a.length)"`.

## TDD slice shape

Red phase: decoder unit tests (exact topic hash, zeroed fields, wrong-topic rejection), classifier tests (three-state price/cap), boundary tests (status at exact start/end, horizon inclusive end), projection test (latest per chain/contract), cache TTL fake-clock test, route contract test with mocked cache getter. Then implement `seadrop.ts` → `stage-schedule.ts` → `schedule-cache.ts` → route. Full gate: `npm run test:run`, `npm run lint`, `npm run build`, `git diff --check`.

## Schedule alerts + stage lifecycle (SC-11/SC-12, verified 2026-08-13)

Built as a pure transition engine (`schedule-alerts.ts`) on top of the SC-01–SC-09 slice.

### Deterministic-clock transition-engine pattern

For every time-based state machine in this project (threshold transitions, schedule alerts, future alert rules), use the SAME shape:

- Pure `advanceX({ state, nowSeconds, ...inputs }) → { result, state }` — no `vi.useFakeTimers()`, no `Date.now()` inside. Pass `nowSeconds` explicitly so tests advance a fake clock deterministically and the engine stays restart-safe and pure.
- `state` is immutable and JSON-serializable (`Record`/arrays, no Maps/Sets/class instances) so it can be persisted to D1/SQLite and replayed after restart.
- Reject non-monotonic clocks: store `lastAdvancedAtSeconds` in state and throw if `nowSeconds < lastAdvancedAtSeconds`.
- Emit-once dedupe: track already-fired kinds per identity in state; never re-emit on a later observation of the same version.
- Append-only history: lifecycle transitions are appended, never mutated or deleted (SC-12 requires audit history to survive removal).

### Alert kinds + eligibility (SC-11)

Three kinds per stage/version: `new-stage` (first observation), `ten-minutes-before` (`start - 600`), `live` (`start`). A transition is ELIGIBLE only if the version was first observed at/before its fire time, so a stage learned 3 min before start emits `new-stage` + `live` but skips `ten-minutes-before` (the moment already passed). Start unknown (`null`) → only `new-stage` fires.

An edited start time = a new version under the same `chain:contract` key. The new version supersedes the old: old pending timers are cancelled (they never fire) and fresh `ten-minutes-before`/`live` are scheduled against the new start.

### Stage lifecycle (SC-12)

- Same key + new version → old version marked `superseded` (`reason: "superseded"`, `supersededByVersion` = new version), removed from the active set.
- Key disappears from the active set → `cancelled` (`reason: "cancelled"`) if `now < endsAtSeconds`, else `ended` (`reason: "ended"`). Use `endsAtSeconds` to discriminate natural expiry from withdrawal.
- History retains every version with reason/version; the active schedule only exposes `lifecycle === "active"`.

### Key/version derivation glue

`toScheduleAlertStage(StageRecord)` maps `chain:nftContract` → key and `StageRecord.id` → version. `id` MUST be unique per config revision (a later config for the same contract needs a distinct id), otherwise an edit collides instead of superseding the prior version.

### Pitfall: error message must match the test regex

When a test asserts `.toThrow(/monotonic/i)`, the implementation's thrown message must actually contain that word — `"schedule alert clock cannot advance backwards"` does NOT match, `"…(non-monotonic)"` does. Write the error string to satisfy the test's regex (or the regex to match the intended wording) in the same pass — otherwise the full gate fails on a wording mismatch, not a logic bug, and it looks like a real failure.
