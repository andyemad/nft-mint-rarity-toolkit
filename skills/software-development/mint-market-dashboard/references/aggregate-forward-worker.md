# Aggregate-forward worker + D1 cost reality (go-big, 2026-08-14)

Session detail behind the SKILL.md pitfall block. The full build spec lives in the repo
at `GO-BIG-HANDOFF.md`; this file is the "what actually happened / what bit us" record.

## The design (deployed + verified)

`src/worker/index.ts` `ingestChainCatchup` replaces the old rolling-window sampling:

1. Read `chain_cursors` cursor; scan `cursor+1 → head` (clamped to `MAX_CATCHUP_BLOCKS`),
   chunking `getMintLogs` by per-chain `GETLOGS_CHUNK` (Robinhood 1000, Ethereum 10).
2. One anchor `getBlock(head-500)` measures block cadence (~98–102ms on Robinhood);
   every mint's `observedAt` is estimated from it — NO per-block getBlock. Max error
   measured 0.41s over a 480-block window.
3. Decode ALL mints (no sampling), aggregate via `materializeMinuteBuckets` into
   `minute_buckets` + `minute_bucket_minters`, keep a bounded 1000-row `mint_facts`
   feed per chain, advance the cursor.
4. `/stats` reads `minute_buckets` (`getCollectionStatsFromBuckets`); `/mints` reads the
   bounded feed.

First run: robinhood `facts=16808, buckets=146, minters=7181, feed=1000`. Steady-state
runs ~1–2k facts/5min per chain. Both chains live after wiring the Alchemy key
(Ethereum free tier = 10-block getLogs cap → chunk of 10).

## The feed wipe bug (reproduction)

Symptom: frontend "New Mints" showed only ~26 Ethereum mints; `/mints` count collapsed;
user: "no mints from robinhood".

Root cause: `runIngestion` loops chains sequentially and each `commitRecentFeed` did
`DELETE FROM mint_facts WHERE canonical=1` (ALL rows) then inserted that chain's top-1000.
Ethereum ran last → deleted Robinhood's feed, inserted only its own. The chain-scoped
delete (`AND chain_id=?`) fixed it, and `getCanonicalMints` now orders by `observed_at`
so the feed is true cross-chain recency. Verified after fix: 500 latest = 301 RH + 199 ETH.

## Bucket semantic drift

`rebuildMinuteBuckets` originally did `mintCount += fact.quantity`; an ERC1155
mega-batch made one collection show +964,803,852 "mints". Changed to `mintCount += 1`
(event count) — matches the old `/stats` `COUNT(*)` semantics. After changing the
semantics, clear the table once:
`npx wrangler d1 execute mint-market-dashboard --remote --command "DELETE FROM minute_bucket_minters; DELETE FROM minute_buckets;"`

## D1 numbers (measured/verified this session)

- Workers Paid $5/mo includes 50M rows written/month; overage $1/M. Reads 25B/mo.
- Full Robinhood coverage = ~2–5M mints/day (measured 6.5/6.2/2.5 per block across
  three 1000-block windows; the handoff's "1.6/block" is stale/low).
- With the `mint_facts→canonical_blocks` FK (pre-migration 0002), each mint costs ~2
  writes (fact + block row) → ~63–99M writes/mo → ~$18–54/mo. Dropping the FK
  (migration 0002, recreate table) makes facts-only ~42M/mo → $0 overage.
- Retention trims are NOT free: D1 counts DELETE as a write, so trim-as-write doubles
  the bill (~84M/mo → ~$34 overage + $5). No retention → storage grows ~0.4–1GB/day,
  crossing the 5GB free tier in ~1–2 weeks (~$0.75/GB-mo after).

## Verification sequence (worked)

```bash
cd ~/Projects/mint-market-dashboard
npx tsc --noEmit && npx eslint src/worker src/lib/indexer
npx wrangler d1 migrations apply mint-market-dashboard --remote   # for new migrations
npx wrangler deploy
curl -s -m 120 "https://mint-market-dashboard-indexer.mintfieldguide.workers.dev/run"
curl -s "https://mint-market-dashboard-indexer.mintfieldguide.workers.dev/mints"   # expect mixed chains
curl -s "https://mint-market-dashboard-indexer.mintfieldguide.workers.dev/stats?hours=24"  # expect sane mintCounts
```

## Model-switch note (how the handoff got executed)

The go-big implementation was deliberately executed by `deepseek-v4-flash` on opencode-go
(main model switched 8/14 to conserve weekly limits) following `GO-BIG-HANDOFF.md` —
the handoff was written with near-complete code (exact migration SQL, repository
methods, worker functions, verify steps) so a weaker model could implement without
re-deriving. Probe the target model BEFORE switching
(`curl opencode.ai/zen/go/v1/chat/completions` with the key; expect `GO_OK`), then set
model.default/provider/api_mode/context_length together (see hermes-model-provider-config).
