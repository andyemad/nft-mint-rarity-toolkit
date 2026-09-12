# Queue store / worker concurrency lessons (2026-08-24)

Session detail behind "Set and forget" fixes: raw FS errors leaking into the
UI, a cancel that silently got undone, and stale finished cards lingering.

## Symptom chain the user flagged

1. **Raw ENOENT blob in the UI.** The Set-and-forget card showed
   `ENOENT: no such file or directory, rename '~/...'`.
   Two causes stacked: `updateQueue` did a single-shot tmp+rename that raced
   during launchd restarts, AND the worker persisted raw `error.message`
   into the queue JSON verbatim.
   - Fix A: retry the atomic write once (`try{await write()}catch{await write()}`).
   - Fix B: worker sanitizes persisted error text:
     `raw.replace(/\/Users\/[^\s'"]+/g,"<local path>")`.
     Lesson: never persist raw Node error messages to files a UI reads;
     they carry local paths.

2. **Cancel returned 200 but the queue flipped back to waiting.** Classic
   read-modify-write race: DELETE set `state:"canceled"`, but an in-flight
   worker tick had loaded the file BEFORE the cancel and wrote its stale
   "waiting" over it afterwards. For an authorize-and-walk-away feature this
   is dangerous (imagine canceling after it armed).
   - Fix: `updateQueue` re-reads the on-disk record before writing and
     DISCARDS the stale write when the disk state went terminal
     (`isQueueTerminal(current.state) && current.state !== queue.state`).
     Cancel always wins. The worker surfaces the discard as a benign
     "Temporary worker error; retrying", so also clean that cosmetic error
     field off the canceled record once.

3. **Finished cards lingered forever.** Canceled/expired/failed cards kept
   rendering in "Set and forget" with their expiry dates, contradicting the
   "0 ACTIVE" badge. Fix: CommandCenter filters the queues list to non-terminal
   states only; the whole section disappears when nothing is active.
   Rule the user stated: finished = redundant information = don't render it.

## Verification pattern for state-changing queue/API calls

After any cancel/state change on a worker-managed store:
1. curl the mutation → expect 200 and correct response body.
2. WAIT ≥2 worker tick intervals (~10–25s), then re-read BOTH via the API
   and directly from `.runtime/**` on disk. A 200 alone proves nothing —
   the first cancel "succeeded" and was undone within seconds.
3. Confirm no `error` field leaked onto the record.

## Store files involved

- `lib/server/queue-store.ts` — saveQueue/updateQueue/loadQueue/cancelQueue;
  atomic tmp+rename writes, terminal-state guard in updateQueue.
- `lib/server/queue-worker.ts` — ensureQueueWorker tick loop (5–10s),
  processQueueTick state machine, sanitized error persistence,
  caffeinate wake lock while queues are active.
- `components/CommandCenter.tsx` — Set-and-forget section renders ACTIVE
  queues only (`!["confirmed","blocked","expired","canceled","failed"]`).
