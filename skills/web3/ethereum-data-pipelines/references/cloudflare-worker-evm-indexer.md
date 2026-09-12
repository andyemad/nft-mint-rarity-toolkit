# Cloudflare Worker EVM indexer (budget + failover + sampling)

Running a no-key on-chain indexer inside a Cloudflare Worker (D1 store, cron trigger,
served via `/mints` + `/stats` endpoints with CORS `access-control-allow-origin: *`, a
Next.js frontend polling client-side). Verified 2026-08 on the Robinhood Chain mint feed.

## Hard platform limits that shape the design

- **Subrequests: 50 per invocation (free) / 1000 (Workers Paid).** Every `fetch()` to an
  RPC is one subrequest, and each D1 `db.batch()` call is another. The killer at scale is
  per-block `eth_getBlockByNumber` for timestamps: a 40-block window × 2 chains ≈ 80
  subrequests already over the free 50, and a naive "raise the window to 480" bump means
  ~460 getBlock + ~460 D1 batches ≈ 920 — right up against the paid 1000 ceiling. Fix:
  cap mint-bearing blocks per chain per run (free tier: robinhood 38, ethereum 5) OR drop
  per-block getBlock entirely via block-time estimation (below), which removes the cap.
- **Wall-clock, not just subrequests, also kills per-block getBlock.** At the client's
  150ms throttle, 440 sequential getBlock calls ≈ 66s — over the Worker's ~30s wall limit
  even when subrequests stay under budget. Block-time estimation sidesteps both (only ~4
  RPC calls per run).
- **D1 writes: 100k/day (free tier).** Full mint indexing on a busy chain blows this in
  under two hours (Robinhood mints ~1.6/block × ~610 blocks/min ≈ 59k/hr). Sampling is a
  deliberate cost control, not a bug: pick the most-recent N mint-bearing blocks per cron
  run and let the feed accumulate over time. Compute the ceiling:
  `100k writes/day ÷ runs/day` (a 5-min cron = 288 runs → ~347 writes/run budget).
- **Robinhood `eth_getLogs` caps block ranges at 1000** — larger ranges return `-32005:
  block range N exceeds max 1000`. Full-coverage catch-up must chunk ranges at ≤1000
  blocks per call.
- **Cron runs are isolated sessions** with no chat context — the prompt/skills must be
  self-contained, and a run must never schedule another cron job.

## Paid tier (Workers Paid, $5/mo) — verified pricing + limits

Pulled from the Cloudflare docs pricing/limits tables (raw `cloudflare-docs` repo) 2026-08.
Numbers matter because full-chain indexing is a real money decision, not a flag flip.

**D1 pricing** (included on Workers Paid, then overage):
- Rows read: first **25 billion/month** included → `$0.001 / million` after.
- Rows written: first **50 million/month** included → `$1.00 / million` after.
- Storage: first **5 GB** included → `$0.75 / GB-month` after.

**D1 hard limits** (per statement unless noted):
- 1000 queries per Worker invocation (paid) / 50 (free).
- 100 bound parameters per query, 100 KB SQL statement length, 100 columns/table.
- `db.batch()`: the 30s API-resolve limit applies to the WHOLE batch call, and
  per-statement limits apply to each statement inside it.

**The retention trap — deletes bill as writes.** D1 counts `INSERT`, `UPDATE`, **and
`DELETE`** as "rows written". So once you trim old rows at steady state, daily deletes ≈
daily inserts → total writes DOUBLE to ~84M/mo for 1.4M mints/day, i.e. ~$34/mo overage
*regardless of the retention window* (the window only changes storage, not the write
bill). Full-coverage cost model (facts-only storage, 1 row/mint):

| Option | Writes/mo | D1 write bill | Storage |
|---|---|---|---|
| facts-only, no retention | ~42M | $0 | grows ~0.4GB/day, past 5GB in ~10 days |
| facts-only, 7-day retention | ~84M | ~$34 | flat ~4GB |

Storing every mint row forever is inherently $5/mo + a climbing storage bill; keeping it
flat costs ~$39/mo in delete-as-write. The eventual cheapest steady state is aggregation
in D1 (per-collection-per-minute buckets, bounded by #collections × minutes) + raw history
in R2 object storage (no per-row delete fees). Billing enablement is the USER's action
(`dash.cloudflare.com → Workers & Pages → Plans → Workers Paid`) — an agent cannot touch
it; stage code but do not deploy a higher-volume worker until the plan is on, or the free
D1 100k/day cap breaks the currently-working feed.

## Foreign-key write amplification + the aggregate-forward answer (2026-08-14)

Two corrections to the cost model above, found while actually pricing full coverage:

- **Re-measure the mint rate before pricing.** Robinhood's rate is NOT a fixed
  ~1.6/block. Sampled live across three 1000-block windows on 2026-08-14: 6.5, 6.2,
  and 2.5 mints/block — a hot drop pushes it toward ~6/block while the baseline sits
  near ~2.5. Full coverage is realistically **~2–5M mints/day, not 1.4M**, and cost
  scales linearly with it. Always measure with the mint-only filter over a few
  1000-block windows before quoting a price to the user.

- **"Facts-only" is usually wrong until you check foreign keys.** A canonical event
  store that declares `FOREIGN KEY (chain_id, block_hash) REFERENCES canonical_blocks`
  on `mint_facts` (and `chain_cursors`) with `PRAGMA foreign_keys = ON` silently
  forces a `canonical_blocks` row for every mint. So "drop raw_logs, write only
  mint_facts" still costs ~2 writes/mint (fact + block). At 2.5M mints/day that is
  ~63M writes/mo — past the 50M included → ~$18/mo overage, not $0. True facts-only
  needs a migration to drop the FK (recreate the table without it — SQLite/D1 has no
  `ALTER TABLE DROP CONSTRAINT`).

**Aggregate-forward is the cheap full-coverage design** (the "go big" end state).
Decode 100% of mints (catching every new collection is the momentum edge), but do NOT
retain every mint row:

1. Cursor-based catch-up + chunked `getMintLogs` (≤1000-block ranges) + block-time
   estimation → full decode.
2. Aggregate per collection per minute into `minute_buckets` via an UPSERT that sums
   `mint_count`; track unique minters in a separate `minute_bucket_minters` table with
   an idempotent `ON CONFLICT ... DO UPDATE` (a wall-clock minute can straddle two cron
   cycles, so a plain INSERT double-writes).
3. Keep only a **bounded recent feed** (latest ~1000 mints) for the live `/mints` view.

The feed trim must be **delete-all-then-insert-the-latest-N** (sort by
blockNumber/logIndex desc, slice N), never insert-all-then-trim-old — the latter
deletes ≈ full volume each cycle and re-introduces the delete-as-write penalty
(~2M deletes/day at 2.5M mints/day).

Writes then stay bounded by #collections × #minutes + feed size (~15–45M/mo), under the
50M included. Accepted approximations: `uniqueMinters`/`transactionCount` double-count a
minter/tx in a minute that straddles two 5-min cycles (negligible), and `mintCount`
becomes total quantity rather than distinct mint-event count. A complete self-contained
implementation spec (migration SQL, repository methods, worker cursor-based rewrite,
verify steps) is checked into the mint-field-guide repo as `GO-BIG-HANDOFF.md`.

## RPC failover (the 429 problem)

The official Robinhood RPC (`rpc.mainnet.chain.robinhood.com`) intermittently **429s
Cloudflare's egress IPs** — works fine from a personal Mac, throttles worker traffic. Fix:

1. Use the chainlist-listed alternative `https://rpc.arrowrpc.com` as primary — it serves
   `eth_getLogs` fine and its head is actually *fresher* than the official node.
2. Keep an **ordered failover list** per chain (e.g. `[arrowrpc, official]`) and try each
   in turn inside the chain's try/catch; idempotent upserts make a partial-then-retry run
   safe. Ethereum kept `eth.drpc.org`.
3. `robinhood.drpc.org` and `robinhood-rpc.publicnode.com` answer `eth_chainId` but
   reject/restrict `eth_getLogs` — probe getLogs specifically before trusting a candidate.

To discover RPCs for a new/obscure chain without web_search: fetch
`https://chainid.network/chains.json`, find the `chainId`, and read its `rpc[]` list.

## The mint-only filter is what makes the budget work

A Transfer-topic `eth_getLogs` returns ALL ERC-721/1155/20 transfers (~15/block on
Robinhood), of which only ~1.6/block are true mints (from = zero address). Fetching all
transfers and decoding client-side wastes the response budget and the getBlock cap. The
position-specific mint-only filter (see SKILL.md step 3) returns *only* from-zero
transfers, so ~10× more mints fit the same window and subrequest cap.

## Timestamp source — block-time estimation, not per-block getBlock

`eth_getLogs` returns `blockNumber`/`blockHash`/`txHash` but **not the timestamp**.
Per-block `eth_getBlockByNumber` for timestamps is what forces the block cap AND blows the
wall clock at scale. Instead, measure the chain's cadence once per run and infer every
mint block's timestamp:

```
anchor      = getBlock(head.number - 500)          // ONE extra RPC
blockTimeMs = (head.ts - anchor.ts) / 500
observedAt  = head.ts - (head.number - blockNumber) * blockTimeMs
```

Robinhood block time is rock-steady **~98–102ms** (~610 blocks/min ≈ 878k blocks/day ≈
~1.4M mints/day at 1.6/block). **Verified 2026-08-14: max timestamp error 0.41s** over a
480-block window — irrelevant for 24h stats windows. This (shipped in the 15% sampling
bump) is what makes any meaningful window — and future full coverage — possible; per-block
getBlock cannot scale past ~40 blocks. Build the synthetic block object as
`{ chain, number, hash: log.blockHash, parentHash: "", timestamp }` — the log already
carries blockNumber/blockHash, parentHash is unused by the canonical store, and reorg
note the cadence must be
measured PER CHAIN (Ethereum ~12s/block, Robinhood ~100ms/block); use a per-chain fallback
(98ms / 12000ms) when the anchor fetch fails.

## Keyed providers, per-chain chunking, D1 STRICT gotchas (2026-08-14)

When a chain's free no-key RPC is unusable, a keyed provider is the pragmatic upgrade —
but it changes the getLogs budget:

- **Alchemy**: key format `alch_…`, endpoint `https://eth-mainnet.g.alchemy.com/v2/<key>`.
  Free tier is generous for plain RPC volume but caps `eth_getLogs` at a **10-block range**
  (`-32600 … up to a 10 block range`); PAYG removes it. A 5-min Ethereum cycle (~300
  blocks) therefore needs ~30 chunks × 2 filters = 60 getLogs calls — fine on the paid
  1000-subrequest budget.
- **Make chunk size AND catch-up bound per-chain records**, not globals:
  `GETLOGS_CHUNK: Record<DataChain, number> = { robinhood: 1000, ethereum: 10 }` and
  `MAX_CATCHUP_BLOCKS = { robinhood: 20000, ethereum: 3000 }` (Ethereum catch-up is bounded
  so a cold start stays under the subrequest budget: 3000/10 × 2 = 600 calls).
- **Verify the secret took effect by the error SHAPE**: before the key, a chain errors with
  its old provider's signature (e.g. drpc free `HTTP 408` timeout); after the key lands,
  the error changes to the new provider's limit (Alchemy `HTTP 400` + range message). A
  changed status code means the new endpoint is live; then fix the request shape.
- **D1 STRICT tables coerce, don't accept, numeric TEXT math.** Summing a TEXT column in an
  UPSERT (`native_volume_wei` with `CHECK NOT GLOB '*[^0-9]*'`) must be wrapped in casts:
  `CAST(CAST(x AS INTEGER) + CAST(y AS INTEGER) AS TEXT)`, or the CHECK rejects the
  INTEGER-typed result.
- **Dropping a D1 FK = recreate + rename.** SQLite/D1 has no `ALTER TABLE DROP CONSTRAINT`;
  the working pattern (executed on remote D1, 12 commands, ~0.5s) is: `CREATE TABLE
  x_new` (same columns, no FK) → `INSERT INTO x_new SELECT * FROM x` → `DROP TABLE x` →
  `ALTER TABLE x_new RENAME TO x` → recreate indexes. Safe only when nothing else
  references the renamed table; check the schema first (in mint-field-guide nothing
  references `mint_facts`/`chain_cursors`, but `raw_logs`/`sale_facts` still FK to
  `canonical_blocks`).
