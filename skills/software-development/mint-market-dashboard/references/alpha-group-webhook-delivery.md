# Alpha-group alerts — Discord webhook delivery (SHIPPED 2026-08-17)

Verified live: worker `bf6863df-dbe6-44fe-9d2d-1f122b5d7909`, migration `0014`,
897 tests, test post returned HTTP 204. Webhook "the case-study collection Suites" → Calm #🦄alpha.

## Why server-side at all
The alpha-group crossing rule lived ONLY in the browser (Next.js frontend compares
successive `/alpha-groups` snapshots in `src/components/mint-terminal/mint-terminal.tsx`).
With the tab closed, nothing alerted. Moving the SAME derivation into the worker
cron made delivery work with the tab closed. ROADMAP §6-B is the design note;
§6-B is now SHIPPED for alpha-group alerts (the three per-collection watch kinds,
still localStorage-bound, are NOT yet covered — they need the A1 identity work).

## Architecture (4 moving parts)
1. **Migration `0014_alpha_alert_state.sql`** — table `alpha_alert_state
   (chain, slug, collection, members, threshold, observed_at, PK(chain,slug,collection)) STRICT`.
   D1 is the only state that survives Cloudflare's per-isolate isolation (same reason
   migration 0010's `cron_status` exists). Module globals cannot hold the previous snapshot.
2. **Repository methods** (`src/lib/indexer/d1-repository.ts`):
   - `getAlphaAlertState()` — read the whole snapshot
   - `putAlphaAlertState(rows)` — DELETE all + INSERT (full replace; bounded by cohort size).
3. **Delivery module** `src/lib/alerts/alpha-group-delivery.ts`:
   - Reuses `deriveAlphaGroupAlerts` from `alpha-group.ts` verbatim — same edge-trigger
     (below→at/above threshold transition), same `AlphaGroupAlert` shape, so the Discord
     message title matches the board exactly: `` `${slug} buying (${members}/${threshold})` ``.
   - `computeSnapshot(repo, groups)`: one activity scan per DISTINCT window across the
     group set, both chains (Funkari's roster contract is Ethereum; its cohort trades
     on Robinhood — membership is chain-scoped).
   - First run (empty `alpha_alert_state`) SEEDS without firing — a page load is not
     an event; a later webhook enablement starts from a true baseline.
   - `postToDiscordWebhook(url, content)` — POST JSON `{content}`, `res.ok` is the test.
   - **Never throws**: the cron leg must not be able to fail ingestion (the codebase's
     documented 30-minute-blackout discipline).

   **Message format (SHIPPED 2026-08-19)**: the alert now appends the actual OpenSea
   link. In `deliverAlphaGroupAlerts` the per-found collection-meta lookup (the same
   loop that resolves the display name) also caches `slug` and builds
   `https://opensea.io/collection/{slug}`; `formatAlphaAlertMessage(alert, label, crossed,
   openseaUrl)` appends a `OpenSea: <url>` line. The line is **omitted when `slug` is
   null** (RH-chain-only collections with no imported OpenSea slug). This reuses the
   already-populated `collection_meta.slug` column — NO per-alert OpenSea API call, keeps
   delivery cheap. No new migration; deploy the worker only. Fallback offer on the table:
   deterministic `https://opensea.io/assets/<chain>/<contract>` for slugless collections.
4. **Worker wiring** (`src/worker/index.ts`): inside `runIngestionWithCapture`, AFTER
   `runIngestion`, in its own try/catch:
   ```
   try { result.alphaDelivery = await deliverAlphaGroupAlerts(env); }
   catch (error) { result.alphaDelivery = { error: ... }; }
   ```
   The outcome is folded into `/health`'s `lastCron.summary.alphaDelivery` so delivery
   failures are visible, not silent.

## Secret handling (never in git)
- `DISCORD_WEBHOOK_URL?: string` on the `Env` interface only.
- Stored as a Cloudflare secret: `printf '%s' '<url>' | npx wrangler secret put DISCORD_WEBHOOK_URL`
  (piping avoids shell history). Same pattern as `OPEN_SEA_API_KEY` — the value never
  lands in the repo.
- No secret → `{disabled: true}` in the summary; delivery reports honestly rather than failing.

## Deploy + verify sequence (the full proof)
```
npx tsc --noEmit                                          # exit 0
npx vitest run src/lib/alerts/alpha-group-delivery.test.ts ...
npx vitest run   # full suite (fileParallelism:false, ~110s) — expect 897 tests here
npx wrangler deploy --dry-run --outdir /tmp/mfg-dryrun   # gate deploys on dry-run, never grep
npx wrangler d1 execute mint-market-dashboard --remote --file migrations/0014_alpha_alert_state.sql
npx wrangler deploy
curl -s https://mint-market-dashboard-indexer.mintfieldguide.workers.dev/run \
  | jq .alphaDelivery        # expect {fired:[],sent:0,disabled:false} on seed run
curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" \
  -d '{"content":"test"}' "<webhook_url>"   # expect HTTP 204
```

## Pitfalls
- **Verify the webhook's target channel BEFORE wiring** — GET the webhook URL
  (read-only, returns name/channel_id/guild_id). the user created it pointed at the wrong
  channel, then fixed it; check first, never post blind to an unverified target.
- Approval: recurring outbound messages need a workspace approval slate naming the
  exact channel, cancellation terms (remove the secret / delete the webhook), and
  `max_spend 0` BEFORE the first test post. Consume the approval before executing.
- Test-post BEFORE relying on the pipeline, but never test-post a message the user
  would be embarrassed by in a 100+ member channel — keep the test text neutral.
- Don't record the webhook URL in skill files or repo docs; reference the secret name.

## Status note for docs
START-HERE header and ROADMAP §6-B now carry "ALPHA-GROUP ALERTS DELIVER TO DISCORD"
entries; future sessions should read those, not this reference, for live state.