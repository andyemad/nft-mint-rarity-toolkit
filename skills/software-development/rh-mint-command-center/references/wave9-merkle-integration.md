# Wave 9 — merkle allowlist integration (2026-08-23)

Leaf-scope delivery: `/api/merkle-plan` route + AdvancedTaskPanel "Merkle"
mode + both test files. All green at close: 14 new tests, 10 regression panel
tests (opensea + manual panels untouched behaviorally), `npx tsc --noEmit`
clean. Uncommitted at write time — commit with the wave-9 gate.

## Route contract — app/api/merkle-plan/route.ts
GET `?contract=0x…` (trimmed, then shape-checked against `^0x[0-9a-fA-F]{40}$`)

| case | response |
|---|---|
| non-loopback host | 403 `{error:"Local access only."}` |
| missing / blank / malformed contract | 400 `{error:"contract query parameter required"}` |
| success | 200 `{summary}` — ClaimConditionSummary `{root, activeIndex, priceWei, currency, raw}` (raw = attempted-selector trail) |
| detectClaimConditions throws | 400 `{error:<message>}` verbatim |

Deps: DEFAULT (real RPC) — the route passes no injected rpcCall, so route
tests vi.mock `@/lib/server/modules/merkle` and assert
`toHaveBeenCalledWith(contract)` proves single-arg default-deps call.

## Panel — AdvancedTaskPanel Merkle mode
Testids: `mode-merkle`, `mk-contract-input`, `mk-fetch`, `mk-summary`,
`mk-receiver`, `mk-proof`, `mk-proof-note`, `mk-qty`, `mk-expected`,
`mk-rehearse`. State pairs: `mkContractInput` (what you typed) vs
`mkContract` (fetched, used as POST contractAddress); `mkProofText` defaults
to `"[]"`.

Client-side mirrors (client can't import lib/server; parity locked by tests):
- `weiToEthStringOrNull("40000000000000000") === "0.04"` — BigInt string math,
  frac padded to 18 then trailing zeros stripped.
- `isNativeCurrencyClient`: null / empty / zero address / all-e sentinel ⇒ native.
- `parseProof`: JSON array of `/^0x[0-9a-fA-F]{64}$/` strings; non-conforming
  entries named in the note (first 3); `[]` ⇒ ok:true with note
  `"⚠ no proof — will fail on allowlisted drops"`. Note renders live under
  the textarea AND blocks rehearse.

## Rehearse body (POST /api/tasks) — Quasarr §2.3-shaped intent
```json
{
  "module": "merkle",
  "contractAddress": "<fetched drop contract>",
  "valueWei": "<expected×qty×1e18 exact BigInt decimal string, or \"0\">",
  "executionStrategy": "runtime-signing",
  "simulationMode": true,
  "selector": "claim(address,uint256,address,uint256,(bytes32[],uint256,uint256,address),bytes)",
  "moduleParamsJson": "{\"module_type\":\"merkle_drop\",\"receiver\":\"0x…\",\"quantity\":2,\"proof\":[\"0x…\"]}"
}
```
Selector is for display only; no abiArgs, no rawData — calldata binds
downstream from moduleParamsJson (executor will call buildClaimCalldata).

## Test-fixture gotcha
Mocked `/api/tasks` responses MUST include a `rehearsal` field or the panel
renders "saved (no rehearsal returned)" and `/saved task-<id>/` assertions
fail. Fixture bug, not an app bug.

## Known gap (inherited from wave 8)
`/api/tasks` calls `buildCalldata(model)` unconditionally, so REAL rehearsals
for module:"merkle" (and module:"opensea") posted without selector/rawData
400 with "task has no calldata source". Wiring rawData derivation from
`moduleParamsJson` into the tasks route or executor is the next parent leaf;
until then the panel renders that error honestly.
