# Tasks page — delete stored tasks (shipped 2026-08-24)

## API
`app/api/tasks/route.ts` exports DELETE alongside GET/POST:
- `DELETE /api/tasks?id=<taskId>` — remove one stored task
- `DELETE /api/tasks?ids=<id1,id2,…>` — bulk remove (checkbox multi-select)
- loopback-gated via `assertLoopback` like every other route; store-only
  (`.runtime/tasks.json`), never broadcasts on-chain — rehearse-only contract intact.
- 400 when neither id nor ids given; 404 when no task matches; 200 with
  `{ deleted: N }`.
- Atomic write via existing tmp+rename `writeTasks`.

## UI (`components/TasksView.tsx`)
- Per-row **Delete** button in the Actions column (`data-testid=delete-task-<id>`),
  replaced the old "no delete route yet" dash.
- **Delete selected** button in the table footer (`data-testid=delete-selected`),
  disabled while deleting or when nothing checked; works off the existing
  checkbox set; clears deleted ids from selection and reloads via existing `load()`.
- Errors surface inline as `data-testid=delete-error` role=alert.
- Note: `deleteTasks` must be declared AFTER `load` (useCallback dependency order).

## Tests
`tests/tasks-route.test.ts` has a DELETE describe block: 403 non-loopback,
400 missing params, 404 unknown id, single delete keeps siblings, bulk delete.
Seeding gotcha: POST validates strictly — a second variant body with bare
`selector: "mint()"` failed validateTask; seed two identical valid bodies
instead (ids are unique anyway).
Full suite at time of ship: 750/750 across 81 files.

## Deploy
See `references/launchd-deploy-flow.md` — build + kickstart required; dev-mode
testing against port 3000 hits stale production code.
