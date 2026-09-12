# Deploying Mint Room code changes — launchd production service

Session-verified 2026-08-24 while adding `DELETE /api/tasks`.

## The setup
Port 3000 is owned by launchd label `com.patelai.rh-mint-room`:
- plist: `~/Library/LaunchAgents/com.patelai.rh-mint-room.plist`
- KeepAlive=true, RunAtLoad=true, ThrottleInterval=10
- runs PRODUCTION: `node .../next/dist/bin/next start -H 127.0.0.1 -p 3000`
  (NODE_ENV=production), workdir `~/Projects/rh-mint-command-center`
- logs: `.runtime/logs/launchd.{out,err}.log`

## Pitfalls (each one actually bit)
1. **Killing the server PID is futile.** `next-server` shows ppid=1; launchd
   respawns it within seconds. Do not chase PIDs.
2. **`npm run dev` silently binds port 3001** when launchd holds 3000
   ("⚠ Port 3000 is in use by process N, using available port 3001").
3. **Testing against 3000 after starting dev = testing STALE production code.**
   Symptom seen: brand-new route returns HTTP 405 Method Not Allowed, which
   looks like "Next.js didn't pick up my route" but is really the old process.
4. Dev-mode hot reload never reaches the launchd server — only a fresh
   production build + service restart does.

## Dev-mode stale-code trap (bit again 2026-08-24, ~30 min lost)
When a bare `next-server` (ppid 1, orphaned from a dead nohup subshell) holds
port 3000 WITHOUT launchd or a file watcher, source edits NEVER appear in
responses, even after kill + restart attempts — the worker serves its last
compiled chunks. Detection: add a unique marker constant to the changed
source file, then `grep -rl MARKER .next/*/chunks/` — absent marker = stale.
Fix: `kill -9` the server, wipe `.next`, and start dev via a TRACKED
background terminal (`terminal(background=true)`), not a nohup subshell
(subshells die and orphan the worker). Expect HTTP 500s during Turbopack's
cold rebuild; wait and re-probe. Better: for verification against "real"
behavior, prefer the launchd sequence below over fighting a stray dev server.

## Correct deploy sequence for ANY app-code change
1. Verify offline first: `npx tsc --noEmit`, then targeted vitest files,
   then full `npx vitest run`.
2. `npm run build` (must pass).
3. Restart the managed service:
   `launchctl kickstart -k gui/$(id -u)/com.patelai.rh-mint-room`
4. Verify END-TO-END against `http://127.0.0.1:3000` (never 3001) with a real
   request that exercises the new code path — e.g. for tasks DELETE:
   POST a throwaway task → DELETE it → GET and confirm absent.

## Related
Tasks-page delete surface (route + UI): see SKILL.md Tasks section and
`references/task-groups-eligibility-mints.md` for the live-group delete flow
(`DELETE /api/task-groups?id=…`, which cancels the backing queue-mint first).
