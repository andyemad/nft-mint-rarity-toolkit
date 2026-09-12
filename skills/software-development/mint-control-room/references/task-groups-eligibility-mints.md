# Task groups — eligibility-triggered mints (no schedules)

Shipped 2026-08-24. the user's core ask, verbatim intent: "if you put an opensea
url or contract address, as soon as your wallet is eligible, it mints. like
instantly. you don't put time" — trigger = eligibility (public/FCFS stage
open), never a clock time.

## Architecture (who does what)

- `lib/server/task-group-store.ts` — one JSON per group under
  `.runtime/task-groups/`. Group = {name, slug, contract, chain, queueId,
  createdBy}. Create is idempotent by (contract+name) so re-creating never
  stacks duplicate mints.
- `app/api/task-groups/route.ts` — POST resolves input via the existing
  OpenSea planner (`fetchCollectionPlan`), then launches a REAL
  `createQueueAuthorization` queue-mint and calls `ensureQueueWorker()`.
  GET joins groups with their live queue state from `listQueues()`.
  DELETE cancels the backing queue + removes the file.
- `components/CreateTaskGroupModal.tsx` + `.module.css` — a Windows minting app-style
  create modal: Mint-source rail (OpenSea selected), URL field → **Fetch**
  (uses `/api/opensea-plan`, prefills contract/name/max-price from public
  stage), quantity + max unit price editable, footer Cancel/Create.
- `components/TasksView.tsx` — "＋ New Group" button in rail head; live
  groups render above derived groups with an `elig` badge and
  `queueBadge(state)`; selecting one shows `LiveGroupDetail` (key prefix
  `live:<id>`). Polls `/api/task-groups` every 5s alongside `/api/tasks`.

## The key insight

The queue-worker ALREADY implemented eligibility-triggered minting
(`decideQueueAction`: wait until stageState==="live", price ≤ ceiling,
balance covers max → rehearse → arm → broadcast automatically). Task groups
are a thin identity+UI layer over it. Don't rebuild execution.

## Guardrails that fired for real

- the test collection create was REFUSED: "Allowlist or restricted stages cannot be
  auto-minted without a proof." Correct behavior — restricted stages need a
  merkle proof the queue path doesn't have.
- Non-SeaDrop collections refused ("supports public SeaDrop only").
- Price ceiling + 7-day expiry enforced by `createQueueAuthorization`.

## Testing pattern (curl against launchd instance)

POSTs need Origin+Referer headers (assertSameOriginLoopback):
```
curl -X POST localhost:3000/api/task-groups -H 'content-type: application/json' \
  -H 'Origin: http://localhost:3000' -H 'Referer: http://localhost:3000/tasks' \
  -d '{"input":"https://opensea.io/collection/fab-4200","quantity":1}'
```
Verified flow: fab-4200 → resolved 0xef08…d758 (robinhood) → worker picked
it up ≤5s → state `waiting`/"Public mint is not active" (its window was
closed) = eligibility gate proven without spending.

## Pitfalls hit this session

- Test contract drift: tasks-view poll test asserted exactly 1 fetch on
  mount; adding the second endpoint made it 2 (then 4 after one interval).
  Update counts, keep the no-post-unmount-poll assertion.
- Bare `npx tsc --noEmit` without `-p tsconfig.json` drowns real errors in
  module-resolution noise; the repo's `npm run build` / `npm run check`
  are the authoritative gates.
- CSS-module class must exist for every className referenced in TSX or the
  build fails on missing style exports — append new classes to
  TasksView.module.css when extending the view.

## Known gaps

- ~~No delete button in UI yet~~ — RESOLVED 8/24: DELETE /api/tasks ships with
  per-row + bulk-delete UI; group delete (cancels backing queue first) is in
  the live-group detail pane.
- ~~Modal's source rail lists other marketplaces as inert labels~~ — RESOLVED
  8/24: rail removed entirely after the user flagged the dead options as broken
  placeholders. Lesson: decorative options that aren't wired read as bugs to
  users; show only what works.
- Group-vs-task confusion: resolved by renaming to "Auto-Mint Groups" /
  "New Auto-Mint" with a plain-English toolbar hint. the user could not tell what
  a "task group" was from the label alone — name features by what they DO.

## Related session detail

- Cancel-undone-by-worker race + ENOENT error hygiene:
  `references/queue-store-worker-concurrency.md` (supersedes/complements
  `references/queue-store-atomic-writes.md`).
- Stale finished cards lingering in Set-and-forget: fixed by filtering to
  active states only; the user's rule — finished = redundant = don't render it.
