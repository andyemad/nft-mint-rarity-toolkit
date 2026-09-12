# On-chain secondary-sale detection (volume/change/sales without marketplace APIs)

Goal: a Market column that shows collections being swept/bought (volume, sales,
change) when the chain has NO marketplace stats API (Robinhood chain: OpenSea v2
has no stats endpoint for it). Detect sales directly from RPC logs — verified on
Robinhood chain 2026-08-14.

## Sale heuristic (v1, verified)

**A sale = a secondary Transfer event (from != 0x0, to != 0x0) whose transaction
carries native value (`tx.value > 0`). Price = tx.value.**

- ERC-721: `eth_getLogs { address: collection, topics: [TransferTopic] }` per
  collection (mint events included — from == 0x0 — filter them client-side).
- For each tx with secondary transfers, `eth_getTransactionByHash` and read the
  `value` field. Receipts are NOT needed and do NOT show native flows; the tx
  `value` field is the cheap reliable signal.
- Measured on RH chain: ~36% of secondary txs carry value > 0 (real purchases at
  0.02 / 0.0077 / 0.003 RH etc.); the rest are wallet moves.
- **Bulk distribution bots must be excluded**: one "router" address pushed 519
  NFTs in a single zero-value tx. Their txs are value=0 so the heuristic drops
  them automatically — do not count transfer counts without the value check.
- Sweep attribution: a tx sweeping N NFTs of ONE collection = N sales, volume =
  tx.value. A tx touching MULTIPLE collections: attribute volume proportionally
  (`volume_coll = tx.value * count_coll / total_count`), sales = per-NFT count.
- Buyers per collection = distinct `to` addresses in value-bearing txs.

## JSON-RPC batch is the cost lever

- arrowrpc (RH) accepts JSON-RPC batch arrays: 60 `eth_getTransactionByHash` in
  one HTTP request ≈ 0.16s vs 60 × ~0.25s sequential. Batch `eth_getLogs`
  (10/call), `eth_getTransactionByHash` (60/call), and `eth_call` (40/call).
- Worker cost profile drops from minutes to seconds: chunked batched getLogs
  (120 calls → 12 batch requests) + tx values (600 txs → 10 batch requests).
- Keep one HTTP client with a `requestBatch(items)` method; treat non-array
  responses (some providers answer a batch with a single error object) as
  provider failure, not success.

## CRITICAL pitfall: arrowrpc's range cap masquerades as HTTP 429

`rpc.arrowrpc.com` rejects `eth_getLogs` block ranges **> 1000** with an HTTP
**429** whose body is a JSON-RPC error:

```
{"jsonrpc":"2.0","id":null,"error":{"code":-32005,
 "message":"batch rejected: block range 2500 exceeds max 1000"}}
```

This wasted several deploy cycles: the 429 looks exactly like rate limiting
("RPC batch rate limited"), and rate-limit fixes (pacing, smaller batches,
retry backoff) do nothing. **Read the response BODY before assuming rate
limiting.** Any time a public RPC returns 429, check whether the body is a
query-shape rejection (-32005 range limits, invalid params) vs a true
rate-limit error. Chunk getLogs windows to ≤1000 per call (per-chain constant —
see `cloudflare-worker-evm-indexer.md`).

## No standard WETH on Robinhood chain

Probing `0x4200000000000000000000000000000000000006` (OP-stack WETH) and other
candidates returned empty `eth_getCode` (no contract). WETH-transfer-in-receipt
pricing does not work for general RH secondary activity. This is consistent with
the Seaport caveat in the umbrella skill (RH Seaport listings settle in WETH via
the marketplace contract) — for MARKET sweep detection use the tx.value
heuristic; for exact per-trade P&L keep using state-changes/WETH (wallet_recon
path). They are different measurement layers.

## D1/SQLite volume storage — avoid wei TEXT

`SUM(CAST(volume_wei AS INTEGER))` over TEXT columns: D1 serializes SQLite
INTEGER sums as JS numbers → precision loss above 2^53 (any real volume in wei).
Store per-bucket volume as **REAL native-token units** (`volume_rh REAL NOT NULL
CHECK (volume_rh >= 0)`) computed in JS (`Number(wei) / 1e18`); float error is
display-negligible and SUM stays sane.

Schema (per minute, rebuilt/upserted each scan run):

```sql
CREATE TABLE sale_buckets (
  chain_id INTEGER NOT NULL,
  minute_start INTEGER NOT NULL,          -- unix seconds floor(now/60)*60
  collection TEXT NOT NULL,
  sales_count INTEGER NOT NULL,           -- NFT transfers in value-bearing txs
  volume_rh REAL NOT NULL,
  buyers_count INTEGER NOT NULL,
  source_through_block INTEGER NOT NULL,
  rebuilt_at INTEGER NOT NULL,
  PRIMARY KEY (chain_id, minute_start, collection)
) STRICT;
CREATE INDEX sale_buckets_by_window ON sale_buckets(chain_id, minute_start DESC, collection);
```

`/market?chain=&minutes=` reads cur window + prev window from sale_buckets for
changePct (`(cur - prev) / prev`, null when prev == 0), merges mint counts from
minute_buckets as fallback rows.

## Worker wiring lessons

- **Independent sub-tasks need separate try/catch.** Originally the sales scan
  ran inside the chain-ingestion try block; a scan failure replaced a
  SUCCESSFUL ingestion result with `{error}`. Wrap the scan separately so
  `results[chain]` (ingestion) and `results[chainSales]` (scan) can't clobber
  each other.
- **`wrangler d1 migrations apply` is interactive** (prompts "About to apply").
  Piped through `tail` it can silently not apply — and a missing table then
  crashes the endpoint with Worker error 1101. After applying, verify the table
  exists (`SELECT name FROM sqlite_master WHERE type='table'`) or use
  `wrangler d1 migrations list` before assuming it landed.
- Scan window vs cron cadence: with a 5-min cron, a 2500-block (~4 min) window
  chunked at 1000 leaves small overlap so every minute gets re-upserted. Cap
  total txs per run (e.g. 600) — under-counting under extreme activity is
  acceptable v1; the latest minutes always get scanned so "now" windows stay
  right.

## Mint prices: ingestion rewrites silently regress paid mints to "Free"

The go-big rewrite dropped tx-value resolution from the mint ingestion loop, so
EVERY mint fact carried `nativeValueWei: "0"` and paid mints displayed as Free
(regression caught via user screenshot comparison 2026-08-14). Fix pattern:
collect unique tx hashes from the mint logs FIRST, batch
`eth_getTransactionByHash` once (`fetchTxValues`), build a tx→value Map, then
pass `nativeValueWei: String(value)` into each `decodeMint` context. Zero-value
stays Free; paid mints show a price. Add a sanity assertion to a future
deployment gate: "feed contains at least some paid mints" — a fully-Free feed
after a rewrite is the symptom.

## Frontend shape

- Window switcher is a segmented control per column; Trending set
  1m/5m/10m/30m/1h/6h/12h/24h, Market set 1m/5m/15m/1h/1d (MintGo's sets).
- Market column parity (MintGo screenshot comparison): headers **NAME / VOL /
  CHG / SALES ↓** in that order, rows sorted by SALES desc (MintGo sorts
  SALES ↓), a minimum-sales threshold control (`All / ≥50 / ≥100 / ≥200`),
  and CHG colored green/red when a prior-window baseline exists (dashes are
  honest — they fill in as bucket history accumulates, not a bug).
- **Floor price is the parity boundary**: MintGo shows `Ξ` floor prices, but
  floor needs orderbook data that only OpenSea serves and their v2 API has no
  keyless stats for RH chain. Use **avg sale price (volume/sales)** as the
  honest on-chain proxy; never fabricate a floor.
- Price tags in New Mints: chain-aware symbol — `Ξ` for Ethereum, `◇` for RH —
  derived in the client mapping from `nativeValueWei` (wei/1e18), only when > 0.
- Volume displays in native RH units (RH token has no CoinGecko listing → no
  USD conversion available).

## Stablecoin-paid activity (USDG/USDC) — what receipts actually show

MintGo's Market shows a USDG tag + USDT volume. On RH chain, receipts of
`value=0` secondary/mint txs DO contain ERC-20 Transfer logs — but they are
**launchpad/royalty fee splits, not seller prices**: transfers go to 5 FIXED
recipients that repeat across every tx (creator wallet, treasury, platform,
collection contract, `0xdead` burn). Do not assume an ERC-20 transfer inside a
sale tx is the price; the seller-payment recipient is a specific pattern you
must verify per marketplace. Catching USDG-denominated mints/sales for USD
volume requires a real receipt-scan design (next build) — v1 honestly counts
only native-visible sales.
