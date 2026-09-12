# enrichment risk-layer modules (established 2026-08-13)

Three pure-logic, provider-injected modules added under `src/lib/enrichment/` as the
collection-risk layer (EN-07/EN-09/EN-10). Same house conventions as the rest of the
dir: `Field` + provenance via `available`/`unavailable`, injectable providers (no
crypto/network imports), `import type`, immutable `{ result, state }` for state modules.

## reports.ts — EN-09 (community reports)
- Pure state module (no `Field` wrapper; provenance is the per-report `createdAt` ISO).
- `CommunityReport { id, category, subject, createdAt, moderation, idempotencyKey }`.
  `id` is monotonic `r1`, `r2`, ... (NOT derived from input). `moderation` is the closed
  union `"pending" | "approved" | "rejected"` (`REPORT_MODERATIONS` as const).
- `submitReport(state, input)` -> `{ result, state }`. Rejects empty
  category/subject/idempotencyKey as `{ ok:false, code:"invalid" }`; a reused idempotency
  key -> `code:"duplicate"` and does NOT add a second report (no double-count). New report
  starts `moderation:"pending"`.
- `moderateReport(state, reportId, moderation)` -> `{ ok:true, report } | { ok:false,
  code:"not-found" }`. Unknown id is `"not-found"`; moderation is a typed union so there is
  no "invalid" branch inside — use the exported `isReportModeration(value: unknown)` type
  guard at the boundary for untrusted input.
- `publicReports(state)` / `publicReportCounts(state)` expose APPROVED reports only.
  Pending and rejected are absent; each approved report appears exactly once.
- **Secret non-exposure:** `SubmitReportInput.reporterSecret` is accepted on the call but
  never copied onto the report or into state. Because it is an interface field (not a
  function param) it does not trip `no-unused-vars`, and `JSON.stringify` of any result
  structurally cannot contain it.

## honeypot.ts — EN-10 (listing-honeypot warning)
- Inject `SellSimulation { simulate(params) => Promise<SimulationOutcome> }`, where
  `SimulationOutcome = "sellable" | "blocked" | "rpc-failure"`.
- `classifySimulation(outcome)` -> `HoneypotVerdict = "pass" | "warn" | "inconclusive"`.
  Mapping: sellable->pass, blocked->warn, rpc-failure->inconclusive. There is deliberately
  NO "safe" verdict; **RPC failure never maps to "pass"**.
- `evaluateHoneypot(options)` -> `AdapterResult<HoneypotVerdict>`. A returned
  `"rpc-failure"` is `available` with value `"inconclusive"` (an explicit state, not null);
  a THROWN `simulate()` is `unavailable` (could not run at all). Invalid address -> unavailable.

## deployer-projects.ts — EN-07 (deployer NFT project count)
- Inject `DeployerProjectsProvider { listDeployments(deployer, chain) => Promise<RawDeployment[]> }`.
  `RawDeployment { address, kind: "nft"|"token"|"other"|"unknown", isProxy, isFactory }`.
- `countDeployerProjects(deployments)` -> `DeployerProjectCount { state, count, directQualifying,
  excluded, ambiguity }`. `state: "qualified" | "unknown"`.
- **Transparent exclusions:** every deployment lands in `directQualifying` OR `excluded`
  (with `reason: "invalid-address"|"duplicate-address"|"not-nft"|"proxy"|"factory"`).
  For invalid-address, record the RAW string (`deployment.address || null` — empty->null,
  garbage->garbage) so the exclusion stays transparent, don't collapse to null.
- **Proxy/factory ambiguity -> "unknown", `count: null` (never a fabricated number).**
  Track both kinds independently in a `Set`; `ambiguity` is the sorted-kind array (empty when
  qualified). `directQualifying` still lists the non-excluded NFTs, but `count` is authoritative
  and null while unknown.
- `enrichDeployerProjectCount(options)` wraps in `Field` with provenance; invalid deployer ->
  unavailable; thrown provider -> unavailable.

## EN acceptance-point map (risk layer)
| EN | File | Concern |
|----|------|---------|
| 07 | enrichment/deployer-projects.ts | deployer NFT project count w/ transparent exclusions + proxy/factory "unknown" (never fabricated) |
| 09 | enrichment/reports.ts | community reports (moderation states, approved-only aggregate, idempotent submit, secret non-exposure) |
| 10 | enrichment/honeypot.ts | listing-honeypot warning from injectable sell simulation (rpc-failure -> inconclusive, never "pass") |
