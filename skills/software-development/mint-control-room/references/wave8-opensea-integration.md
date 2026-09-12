# Wave 8 — OpenSea module integration (2026-08-23)

Session detail for the a Windows minting app-parity wave 8 integration: OpenSea mode in
AdvancedTaskPanel + `/api/opensea-plan` route. Module data layer
(`lib/server/modules/opensea.ts`) was pre-existing and untouched.

## What exists now (contracts)

- `GET /api/opensea-plan?input=<URL|os:slug|bare-slug|0x address>` → `{ plan }`
  where plan = `{ slug, contract, chain, stages: [{index,label,isPublic,startMs,endMs,priceEth}] }`.
  Guards/copy mirror the tasks route: `assertLoopback` → 403 "Local access only.";
  missing/blank `input` → 400; module throw → 400 with the message VERBATIM
  (honest errors — never reworded, tests assert on exact text).
- AdvancedTaskPanel (`components/AdvancedTaskPanel.tsx`) is dual-mode:
  `mode-manual` / `mode-opensea` buttons with `aria-pressed`, default Manual.
  Manual markup/behavior is byte-identical to wave 7 (its 4 original tests pass
  unmodified) — when adding modes to an existing panel, keep the legacy mode's
  DOM untouched so its test file needs zero edits.
- OpenSea Rehearse POST body (the §2.1 shape):
  ```
  { module:"opensea", contractAddress:<plan.contract>, valueWei:<string>,
    executionStrategy:"runtime-signing", simulationMode:true,
    moduleParamsJson: JSON.stringify({ mint_type, quantity, slug, chain,
      stage_index, stage_label, price_eth }) }
  ```
  NO selector/rawData/abiArgs fields at all (JSON.stringify of a literal that
  omits them). `valueWei` = expectedPrice×qty×1e18 via BigInt string math
  ("0" when price null/"0"); e.g. "0.04"×2 → "80000000000000000".
  `moduleParamsJson` key ORDER matches buildTaskFromStage exactly and is
  asserted with toEqual in tests.
- Shared result-line helper `showTaskResponse(response)` renders /api/tasks
  responses identically for both modes (✓ saved · gas ≈ · cost ≈ / revert line /
  ✗ error). One `data-testid="task-result"` element for everything including
  fetch failures.

## Ambiguity dispositions made in this session

- Brief said "contractAddress = plan.contract ?? zero-address placeholder IF null
  then show error" — contradictory. Chosen reading: contract null ⇒ show
  "✗ no contract on this chain yet" and DO NOT post (no zero-address rehearsal).
  Dedicated test asserts fetch was called exactly once (plan lookup only).
- Rehearse button renders always in OpenSea mode but disabled until a plan
  exists (`disabled={busy || osPlan === null}`) rather than appearing only after
  Fetch — first render had it inside the plan-guarded block and the
  "disabled until plan" assertion failed because the element didn't exist.
  Prefer always-rendered + disabled for state-gated actions so tests can assert
  the gate itself.
- Stage dropdown defaults to FIRST listed stage (client cannot reuse server-only
  selectStage windowing logic); expected-price input auto-prefills from the
  freshly picked stage and stays user-editable afterwards.

## KNOWN OPEN GAP (next parent leaf)

`app/api/tasks/route.ts` calls `buildCalldata(model)` unconditionally before
storing. A correct §2.1-shaped opensea task has no selector/rawData, so today
those POSTs return 400 `"task has no calldata source"` and are NOT stored.
The panel surfaces this honestly through the normal result line; tests mock a
201 rehearsal payload to exercise the success rendering. Fix belongs in the
tasks route or executor: derive rawData from `task.moduleParamsJson`
(stage-bound calldata), which is also where the stage-binding scheduler waits
on `stage_index` windows before executing. Until wired, OpenSea rehearsals
never reach simulate/store.

## Test skeletons worth copying

Route handler test (tests/opensea-plan-route.test.ts):

```ts
vi.mock("@/lib/server/modules/opensea", () => ({ fetchCollectionPlan: vi.fn() }));
const mockedPlan = vi.mocked(fetchCollectionPlan);
const localRequest = (url: string) =>
  new Request(`http://127.0.0.1:3000${url}`, { headers: { host: "127.0.0.1:3000" } });
// non-loopback negative: plain Request WITHOUT the host header → expect 403
```

Panel fetch-mock queue (tests/advanced-task-panel-opensea.test.tsx):

```ts
function queueFetch(planResponses: Array<Response | Error>, taskResponses: Response[]) {
  fetchMock.mockImplementation(async (input: unknown) => {
    const url = String(input instanceof Request ? input.url : input);
    if (url.includes("/api/opensea-plan")) { /* shift or throw "unexpected extra call" */ }
    /* else shift taskResponses */
  });
}
```

beforeEach resets the mock, calls cleanup(), sets `global.fetch = fetchMock as typeof fetch`.

## Verification gate used

`npx vitest run <my three files>` (14/14 incl. the 4 pre-existing manual panel
tests) then `npx tsc --noEmit` from repo root → exit 0. The write-time lint
errors emitted by write_file on these files were all single-file-checker
artifacts (wrong tsconfig settings); ignore them, trust the project toolchain.
