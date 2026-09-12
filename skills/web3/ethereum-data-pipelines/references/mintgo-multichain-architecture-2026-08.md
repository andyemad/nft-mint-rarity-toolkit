# MintGo multi-chain architecture evidence (2026-08-13)

Use this reference when reproducing MintGo-class mint intelligence without depending on its private APIs.

## Current artifact and topology

- Page: `https://mintgo.fun/`
- Bundle: `https://mintgo.fun/app.6f4b1cef6de0.js`
- Bundle size: 408,953 bytes
- SHA-256: `6f4b1cef6de07bfdbf07b9bb8c6d082bf473a87ea5611df17eb5d8f09642abb0`
- Browser uses same-origin REST plus Server-Sent Events. It does not open chain WebSockets directly.
- MintGo's server owns RPC/WSS failover, aggregation, snapshots, replay, SeaDrop discovery, and OpenSea enrichment.

## Session and realtime mechanics

- `POST /api/session` requires browser-like same-origin headers and a read/write cookie jar.
- Observed cookies: `mg_access` (~30 minutes) and `mg_vid` (~1 year), both HttpOnly/Secure/SameSite=Lax.
- Client renews about five minutes before expiry and retries once after a 401.
- Per-chain SSE: `/api/events?chain=ethereum&marketPatch=1&mintBatch=1`
- Unified SSE: `/api/all/stream?marketPatch=1&mintBatch=1`
- Captured event classes: `ready`, `chain-ready`, `mint-batch`, `trending-snapshot`, `market-patch`, `seadrop-radar`, `discard`, and `deployer-finance-patch`.
- Event IDs are resumable cursors; reconnect with `?since=<id>`. Handle `replay-reset` by clearing the cursor and repairing from REST snapshots.
- Watchdog behavior observed in the bundle: check every 15 seconds, reconnect after roughly 45 seconds without activity, and rate-limit REST fallback refreshes to about 10 seconds.

## Chain configuration

### Ethereum

- Chain ID 1.
- HTTP pool observed: MEV Blocker, Blast public, PublicNode.
- WSS pool observed: PublicNode, 0xRPC, Tenderly public gateway.
- Poll fallback ~4 seconds; snapshots ~10 seconds; full rebuild ~120 seconds.

### Robinhood Chain

- Mainnet chain ID 4663 (`0x1237`), native ETH, Arbitrum L2.
- HTTP endpoints directly verified: official RPC, ArrowRPC, PublicNode, Pocket Network.
- Standard WSS directly verified: `wss://robinhood-rpc.publicnode.com`, `wss://robinhood.rpc.blxrbdn.com`.
- Explorer: `https://robinhoodchain.blockscout.com`; its v2 API is keyless. Do not assume legacy Etherscan API compatibility.
- The official `feed.mainnet.chain.robinhood.com` is an Arbitrum sequencer feed, not ordinary JSON-RPC WebSocket.
- MintGo poll fallback ~5 seconds; max block range 80; snapshots ~10 seconds; full rebuild ~300 seconds.

## SeaDrop on Robinhood

Canonical SeaDrop deployment, verified through bytecode, Blockscout source/ABI, and live events:

`0x00005ea00ac477b1030ce78506496e8c2de24bf5`

Public stage event:

- Signature: `PublicDropUpdated(address,(uint80,uint48,uint48,uint16,uint16,bool))`
- Topic: `0x3e30d8e1f739ea4795c481b21c23f905e938b80339305f3508e43c558e5dead3`
- NFT contract: `topics[1]`
- Six data words: mint price, start, end, max per wallet, fee BPS, restricted fee-recipient flag.

A live 5,000-block Robinhood sample returned 23 updates. A live 20-block generic mint probe returned 24 ERC-721 mints after excluding six three-topic ERC-20 transfers.

Other useful SeaDrop events include `SeaDropMint`, signed-mint validation updates, token-gated stages, allowlist updates, fee-recipient updates, payout changes, payer changes, and DropURI changes.

## Source-to-product mapping

- **New Mints:** ERC-721 Transfer from zero with exactly four topics; ERC-1155 TransferSingle/TransferBatch from zero. Group by collection and short time bucket.
- **Trending:** derived rolling metrics, not an upstream ranking API. Keep exact 1m/5m/10m/15m/30m/1h/4h/6h/12h/24h components and visible reasons.
- **Runners:** decode marketplace fills independently. A sale price is not a live floor; true floor requires an order book.
- **Upcoming:** persist latest PublicDropUpdated config by chain/collection. Signed and allowlist stages require off-chain enrichment and separate provenance.
- **Collection details:** contract calls plus Blockscout/OpenSea enrichment. Exact holders and deployer history require persistent indexing.
- **Wallet activity:** index global chain events once, then join watched wallets; never run one chain scan per wallet.

## Production architecture

A bounded Vercel route-time RPC scan is an acceptance-stage fallback, not a durable indexer. Use one cursor per chain, canonical block/log storage, protocol decoders, one-minute buckets, materialized rolling snapshots, enrichment jobs, and a read API/SSE layer. Reorg repair must compare parent hashes, find the common ancestor, mark orphaned facts noncanonical, rebuild affected buckets, and resume.

Low-cost recommendation from this session: Vercel frontend plus Cloudflare Workers Paid/Queues/D1/R2, approximately $5/month before paid RPC upgrades. Never create paid infrastructure without approval.

## Acceptance and filtering lessons

- Verify semantic output, not only HTTP 200/schema validity: assert populated sections, representative values, provenance, and rendered cards.
- Public RPC success is intermittent; test ordered failover and degraded per-chain behavior.
- Filter Robinhood utility NFTs before ranking art/collectible mints. Useful signals: known contract denylist plus names containing SBT, soulbound, position NFT/receipt, LP position, vote-escrow, veNFT, credential, or certificate.
- Preserve missing identity/price/floor as missing; do not turn contract activity into investment-quality claims.
