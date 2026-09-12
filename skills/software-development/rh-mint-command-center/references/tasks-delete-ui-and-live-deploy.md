# Tasks page: deletion + advanced-panel styling + group-vs-task clarity (2026-08-24)

Session detail behind the SKILL.md "no dead UI" and launchd-deploy lessons.

## What was wrong (symptoms Emad flagged)

1. Advanced task panel looked like broken placeholders. Root cause:
   `components/AdvancedTaskPanel.tsx` used `className={styles.secondary}` /
   `styles.copy` — neither class exists in `CommandCenter.module.css`.
   Every tab/input/button rendered as an unstyled browser default. The modes
   were actually fully wired (Manual/OpenSea/Merkle/Batch all hit working APIs);
   only the styling was missing. Fix: added `atp*` classes (atpTabs, atpTab,
   atpField, atpInput, atpRow, atpButton, atpCopy, atpMeta, atpResult) to
   CommandCenter.module.css and applied them across all four modes.

2. CreateTaskGroupModal had a decorative "Mint source" rail (Manual, OpenSea,
   Scatter, Rarible, Proof API, Signature API) where only OpenSea works.
   Removed entirely — one flow: paste OpenSea URL → Fetch → Create group.

3. Group vs Add task confusion. Now stated in plain English:
   - Add task = rehearse a mint yourself (saved + simulated, nothing broadcasts)
   - Auto-Mint Group = armed once, fires automatically when wallet becomes eligible

## Tasks DELETE API contract

`app/api/tasks/route.ts`:
- `DELETE /api/tasks?id=<taskId>` — single removal
- `DELETE /api/tasks?ids=<id1,id2,…>` — bulk removal
- Loopback-gated like GET/POST; store-only (edits .runtime/tasks.json,
  never broadcasts). 400 when no id/ids, 404 when nothing matches,
  returns `{ deleted: N }`.

UI: per-row Delete button (`delete-task-${id}` testid), footer
"Delete selected" (`delete-selected`) wired to the existing checkboxes,
error surfacing via `delete-error`.

Tests: `tests/tasks-route.test.ts` DELETE describe block (5 tests);
tasks-view hint text assertion updated to /rehearse a mint yourself/.

## Pitfalls hit

- `next dev` while launchd holds port 3000 → Next silently binds 3001;
  verifying against 127.0.0.1:3000 hits the STALE production build.
  A newly added HTTP method returns 405 from the stale build even though
  the code is correct — rebuild + kickstart first, then re-test.
- `app/api/nft-inventory/route.ts` had a corrupted literal
  `"multi-mist" === "never"` and a missing `listToken` import
  (from `@/lib/server/nft-listing`); both fixed for clean tsc.
- appendOp action union doesn't include "nft-list"; cast via
  `as WalletOp["action"]` until the union is widened deliberately.

## Verification checklist after Mint Room UI/API edits

1. `npx tsc --noEmit` clean.
2. Every `styles.X` referenced in edited TSX exists in the paired .module.css
   (grep the class name in the css file) — this is how the placeholder bug
   survived review.
3. Full suite `npx vitest run` (750+ tests, ~30s).
4. `npm run build` then `launchctl kickstart -k gui/$(id -u)/com.patelai.rh-mint-room`.
5. curl the changed endpoint on 127.0.0.1:3000 to confirm the NEW behavior
   (e.g. DELETE returning 200, not 405) before reporting done.
