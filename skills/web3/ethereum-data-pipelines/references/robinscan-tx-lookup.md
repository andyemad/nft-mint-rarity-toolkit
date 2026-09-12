# Robinscan tx lookup: dexscreener pair link -> swap tx hash (keyless)

Verified 2026-08-31 pulling the tx for a `vanta sweeping` QUOTRON/WETH buy (2,999,987,455,304,605 tokens) off a Wallet Radar Discord alert.

## Robinscan is a KEYLESS live JSON API on the main host

`robinscan.io` is an Arbitrum-Nitro (chain 4663) explorer/SPA. Its public API is served from the MAIN host, not a subdomain:

- `https://robinscan.io/api/health` -> `{ok, lastIndexedBlock, chainTip, lagBlocks}` (liveness + tip).
- `https://robinscan.io/api/txs?page=N&pageSize=50` -> `SnapshotPaginated<Transaction>`.
- `https://robinscan.io/api/txs/<hash>` -> full tx: method, from/to, value, blockNumber, timestamp, `tokenTransfers`, `logs`, `internalTransactions`, `pools`.
- `https://robinscan.io/api/tokens/<addr>/transfers?page=N&pageSize=50` -> `{items, total, page, pageSize, status}`, each item = `{txHash, logIndex, blockNumber, token, from, to, value, standard, action, timestamp}`.
- `https://robinscan.io/api/addresses/<addr>/txs` -> `Paginated<Transaction>`.
- Browser page: `https://robinscan.io/tx/<hash>` (200 once the tx is indexed; a freshly-included tx can be missing for a few seconds).

Docs: `https://docs.robinscan.io` (also `https://docs.robinscan.io/llms.txt`, `/api-reference`, `/mcp`). Robinscan also ships `@robinscan/mcp` (stdio, read-only).

**Do NOT use `api.robinscan.io` — that subdomain 404s / DEPLOYMENT_NOT_FOUND. Use the main host.**

## Capture to find a specific swap

Given a dexscreener link `dexscreener.com/<chain>/<pair>`:

1. The slug IS the pair/pool address. Get its tokens keylessly:
   `curl -s -A "Mozilla/5.0" https://api.dexscreener.com/latest/dex/pairs/robinhood/<pair>`
   -> `pairs[0].baseToken.address` / `.quoteToken.address` (and name/symbol), `priceUsd`, `liquidity`.
   - Dexscreener REST `/latest/dex/trades/...` and `/token-txs/...` return 404 for this route shape — use the token-transfers approach below instead of hunting for a trades endpoint.
   - When the Nous web gateway is down, curl the dexscreener API directly (it works keyless).
2. Query robinscan transfers for the token you care about, NEWEST-FIRST, and match on the quoted amount:
   `curl -s -A "Mozilla/5.0" "https://robinscan.io/api/tokens/<baseAddr>/transfers?page=N&pageSize=50"`
   - **pageSize caps at 50** (100 -> HTTP 400). Paginate `page=1,2,3...` until you pass the target timestamp.
   - Match on `value` (raw units) — the exact string of the quoted token count is the reliable key, since a swap posts two same-value legs (into and out of the router) plus the WETH/quote legs.
3. Confirm with `/api/txs/<txHash>`: check `method` (Uniswap v4 = `exec` to `0x0000...1ff3684f28c67538d4d072c22734`), `from`/`to`, and `tokenTransfers` (quote-token leg = the amount paid; base-token leg = amount received).

## Time-lag gotcha

An alerting bot (e.g. Wallet Radar) posts a message MINUTES after the on-chain timestamp — on 8/31 the alert read 19:59:03Z while the actual tx was 19:56:36Z. Do not reject a candidate tx for a timestamp mismatch; match on amount + transfers instead.

## Robinscan quirk vs Blockscout

For the same RH-chain data, Blockscout v2 (`robinhoodchain.blockscout.com`) is the other keyless explorer; robinscan.io is a friendlier labeled public read for tx-level receipts and token swaps. For collection transfer/holder maps the ethereum-data-pipelines umbrella already prefers Blockscout `/api/v2/tokens/{addr}/transfers` + `/holders`.
