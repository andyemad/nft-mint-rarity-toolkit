# Mint-tools portfolio audit — key findings (2026-08-22)

Three parallel opencode agents audited the case-study collection Suites (mint-market-dashboard) and the control room (mint-control-room). Full reports live in the repos; this file holds the durable, session-independent findings a future session should know before touching either codebase.

## Report locations
- `~/Projects/mint-market-dashboard/.hermes/research/mfg-audit.md` (177 lines)
- `docs/research/control-room-audit.md` (216 lines)
- `~/Projects/research-dossier/portfolio-review-mint-tools.md` (100 lines, the strategy verdict)

## mint-market-dashboard (the case-study collection Suites) — machine-verified state
- M8 (alert delivery) is ~HALF-SHIPPED, not unstarted: server-side Discord webhook for ONE alert kind (alpha-groups) is live and healthy (`src/lib/alerts/alpha-group-delivery.ts`); three of four alert kinds still die when the tab closes.
- D1 database measured 1.358 GB on 2026-08-22 (docs said 811.8 MB on 8/19). ~7.3 MB/h real rate. 5 GB action point ≈ Sept 10–13. No prune code exists anywhere in the repo.
- ROADMAP.md is stale in ≥4 places (items marked open that shipped; decisions marked waiting-on-the user that were answered). START-HERE.md wins every conflict per its own header.
- Known steady-state defect: robinhood mint-price resolution leg is dark (`pricesUnresolved: 1247/1250`, RPC batch 429s); sales legs clean.

## the control room (mint-control-room) — critical defects found by audit
1. **Queue Mint is structurally built but dead end-to-end**: SeaDrop inspector emits `"scheduled"/"live"` (`lib/server/seadrop.ts:37-42`) but queue UI/API/worker consume `"future"/"active"` — a real future stage can NEVER reach the queue. All 45 tests stay green because test fixtures inject the same wrong strings (vocabulary-coupled fixtures).
2. **`app/api/wallets/route.ts` violates README's own safety contract**: implements disposable-wallet creation + funding from ops key + sweep-back, all under "Deliberate exclusions"; loads raw private key into Node process.
3. Quick-mint `broadcast` passes `uiAuthorized=true`, bypassing the `MINT_ROOM_LIVE=1` startup lock (`engine-runner.ts:90-92`) — deliberate tradeoff but now implicit, not tested policy.
4. NOT a git repository — production signing tool with zero history.
5. Adapter registry never generalized: only `mugs.ts` exists; `preflight.ts:17` calls it directly.
6. No P&L recording anywhere: mission logs exist but nothing computes whether mints made money.

## Strategy verdict (portfolio review)
- Freeze A's feature work; run the owner's own distribution test from `CHANNEL-NATIVE-DISTRIBUTION-PLAN.md` (public Telegram/Discord channel fed by existing alert pipeline ≈ hours of engineering; kill criteria already written: 15 posts, ≥25 qualified signups or kill).
- Keep B (the control room) PRIVATE permanently — loopback + local key is its moat. Its needed test is internal: instrument realized P&L per mint.
- Single most valuable integration: feed B's `.runtime/watchlist.json` from A's scam-cleared upcoming-stage detections (days of work, serves proven nightly usage).
- Archive: mintgo-intel (delete + Vercel project), mint-radar, casestudy-mint-sniper, rh-mint-bot (audit its wallets/ dir for loose keys first). Demote rarity-engine to "B's batch data layer".
- Merge A+B = dead idea (incompatible security models). Integrate, never merge.
- 2h/week survival config: B zero maintenance; A as signal appliance (health check + glance at /alpha-groups); one hard calendar item: D1 prune-or-shutdown decision before ~Sept 10.
