# Set-and-forget queue store: atomic-write race + error hygiene (2026-08-24)

Session detail behind the SKILL.md queue lessons (`lib/server/queue-store.ts`,
`lib/server/queue-worker.ts`).

## Symptom the user flagged ("why is this here")

The Tasks page "Set and forget" card rendered a raw ENOENT with full local
paths: `.runtime/queue/.queue-<id>.<pid>.<ts>.tmp -> queue-<id>.json`.
Root cause: `updateQueue` does tmp+rename atomic writes; concurrent writers /
server restarts can lose the race or hit a reaped tmp, and the raw Node error
was persisted verbatim into the queue record's `error` field, which the UI
displays.

Note the card itself was legitimate — the user's own FAB 4200 auto-mint queue,
waiting because FAB's public stage never opens, self-expires 8/31. Before
"fixing" an element, identify whose feature it is and why it exists.

## Fixes applied

1. `updateQueue` retries the write once on failure:
   ```ts
   const write = async () => { /* unique tmp per pid+ms, chmod 600, rename */ };
   try { await write(); } catch { await write(); }
   ```
2. Worker tick errors are sanitized BEFORE persisting so local paths never
   reach the UI: `raw.replace(/\/Users\/[^\s'"]+/g, "<local path>")`.
3. Cleared the stale `error` key from the live queue JSON by hand.

## Pitfall: don't test destructive ops against live runtime files

While verifying the rename fix I ran a python rename test that targeted the
REAL queue file path and clobbered it to `{}`. The worker then loaded `{}`,
threw, and re-persisted a fresh error. Had to restore the queue JSON from the
earlier cat output. Rule: replicate file-system behaviors in a scratch dir, or
read the target bytes first and restore them after. The queue file had no
backup — the recovery source was the transcript.

## Verification pattern for queue changes

1. tsc clean, queue tests green.
2. Rebuild + `launchctl kickstart -k gui/$(id -u)/com.the agent.rh-mint-room`.
3. Watch TWO+ worker ticks (~5-10s apart) after clearing an error field:
   if the error reappears, the failure is live-per-tick, not stale state.
   A single clean read right after restart proves nothing.
