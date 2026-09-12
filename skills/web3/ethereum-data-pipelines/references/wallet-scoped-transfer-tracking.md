# Wallet-scoped transfer tracking

Reference implementation: `~/Projects/wallet-radar/` (Next.js + Vercel + Upstash; production-validated 2026-08-28).

## Wallet-scoped `eth_getLogs`

A wallet tracker filters indexed addresses in both receive/send positions instead of scanning every transfer and filtering afterward.

**Indexed addresses must be 32-byte topic words**, not raw 20-byte addresses:

```ts
export function addressTopic(address: string): string {
  return `0x${"0".repeat(24)}${address.toLowerCase().replace(/^0x/, "")}`;
}
```

A raw `0x` + 40-hex address can pass unit fixtures yet fail live RPC with `hex has invalid length 20 after decoding; expected 32 for topic`. Add a regression assertion that each generated address topic has length 66.

For ERC-721 (`Transfer(address,address,uint256)`):

```ts
// received: topic[2] = tracked wallet
{ fromBlock, toBlock, topics: [ERC721_TRANSFER, null, walletTopics] }
// sent: topic[1] = tracked wallet
{ fromBlock, toBlock, topics: [ERC721_TRANSFER, walletTopics, null] }
```

Do not blindly combine ERC-721 and ERC-1155 signatures into those same two query shapes. ERC-1155 `TransferSingle`/`TransferBatch` use topic[1]=operator, topic[2]=from, topic[3]=to; query them separately with the correct indexed positions.

Cost remains roughly flat in wallet count until the provider's topic-selector cap because one query covers the entire OR-list.

## Four-query batching with independent cursors

For a mixed ERC-721/ERC-1155 tracker, one chain needs only four log filters per block window, regardless of wallet count (until the provider's OR-topic cap):

1. ERC-721 outgoing: `[Transfer, walletTopics]`
2. ERC-721 incoming: `[Transfer, null, walletTopics]`
3. ERC-1155 outgoing: `[[TransferSingle, TransferBatch], null, walletTopics]`
4. ERC-1155 incoming: `[[TransferSingle, TransferBatch], null, null, walletTopics]`

Do not loop these four shapes per wallet. In a validated 9-EVM-wallet daemon, per-wallet querying made 54 `eth_getLogs` calls per chain per cycle; OR-list batching reduced that to 4. Across two EVM chains plus block-head and one Solana signature probe, the baseline dropped from about 111 to 11 requests per cycle. A 15-second batched cadence still used about 60% fewer requests than the original 60-second per-wallet cadence while cutting alert latency by up to 4x.

Preserve wallet isolation when cursors differ:

- Keep one cursor per `(chain, wallet)`.
- Query from the minimum active cursor and include wallets whose cursor falls within that window.
- Before classifying a fetched transaction for a wallet, require its block number to be at or after that wallet's own cursor. This prevents replaying an older transaction for a wallet that was already ahead.
- Fetch transaction/receipt metadata once per unique hash, then classify the same metadata independently for each eligible wallet.
- Advance every participating cursor only after all four log queries, metadata reads, classification, and persistence succeed. If any query fails, advance none of them; existing event-key dedupe makes a retry safe if persistence partially succeeded.
- Treat a non-list `eth_getLogs.result` or a list containing non-object entries as provider failure. A JSON-RPC body with `"result": null` must degrade the chain, not silently advance cursors past unseen activity.

Production verification should use a temporary database and delivery disabled: seed each wallet cursor to one confirmed live block, run one real window on every chain, assert exactly four `eth_getLogs` calls per chain, and confirm no post path is configured. Separately verify the persistent process survives multiple cycles, advances application cursors, and keeps stderr clean; PID existence alone is not completion evidence.

## Classification

- `to == wallet && from == zero` → mint
- `to == wallet` → buy
- `from == wallet` → sell
- `from == to` → drop as self-transfer noise

ERC-20 shares the ERC-721 topic0 but emits only three topics; require exactly four topics before decoding an ERC-721 token ID.

## Sweep aggregation

1. Same transaction always merges by `(wallet, kind, collection, txHash)`; a 20-token sweep becomes one row with quantity 20.
2. Cross-transaction merging requires known timestamps and a bounded window (120s in the reference implementation).
3. Unknown timestamps never merge across transactions.
4. Buys, sells, and mints remain separate buckets.
5. Sum wei as exact integer strings/BigInt. Unresolved value is `null`, never fabricated as zero/free.

## Public-RPC limits must be chain-specific

Validated production settings from the Wallet Radar deployment:

| Chain/provider | Working endpoint | `eth_getLogs` chunk | Max JSON-RPC calls per HTTP batch | Blocks per poll |
|---|---|---:|---:|---:|
| Robinhood | `https://rpc.mainnet.chain.robinhood.com` | 900 | 10 | 4,500 |
| Ethereum dRPC free | `https://eth.drpc.org` | 100 | 3 | 1,000 |

Durable lessons:

- `rpc.arrowrpc.com` returned Cloudflare HTTP 530 from Vercel during this deployment; the official Robinhood endpoint completed real scans.
- dRPC free returns HTTP 500 for oversized batches, with JSON-RPC errors explaining that batches over 3 require a paid plan. Read the body before treating every 500 as transient.
- The same provider limit applies to follow-up `eth_getBlockByHash` and `eth_getTransactionByHash` batches, not just `eth_getLogs`.
- Run chains concurrently (`Promise.all`) when each maintains independent cursors; sequential scans can consume the serverless duration window.
- A transport-level HTTP 200 is insufficient. Require the poll payload's application-level `ok`, per-chain scanned-block counts, and `error:null`.

## Serverless state and catch-up

- Read the tracked-wallet set fresh on every poll.
- Persist wallets, activity, per-chain cursors, and poll health in Redis.
- Merge built-in/default wallets with stored entries if the first deployment must come up pre-seeded.
- Vercel Marketplace Upstash exposes `KV_REST_API_URL`/`KV_REST_API_TOKEN`; direct Upstash setups commonly expose `UPSTASH_REDIS_REST_URL`/`UPSTASH_REDIS_REST_TOKEN`. Support both names.
- Prove persistence by calling `/api/poll`, then reading `/api/feed` in a separate serverless request and checking the cursor/health timestamp survived.
- Bound first-run lookback and advance gradually. Report catch-up honestly; an empty feed after one successful bounded scan is not proof that watched wallets had no older activity.

For Vercel Hobby cron constraints and marketplace provisioning, see the `vercel-deployment-management` skill reference `references/vercel-hobby-upstash-trackers.md`.

## Client alerts

The browser can fetch `/api/feed` every few seconds, diff row IDs, and play a WebAudio chime/browser Notification for new rows. These alerts only work while the page is open. Closed-browser monitoring requires an external scheduler/push channel and separate approval.

## Discord alert message format (learned 2026-08-31)

A wallet tracker persists `tx_hashes` on every alert row, but the MESSAGE FORMATTER must
actually emit a resolvable verification link — it is easy to store the hash and drop it
during formatting, so a user asking "share the tx too?" is the symptom. Distinct alert types
deliberately differ:

- **NFT mint/buy = compact ONE link.** With a resolved OpenSea slug print only
  `OpenSea: <collection>`; without a slug print `Transaction: <explorer>/tx/<hash>` (and
  only then). Never emit the tx a second time on a separate line — that double-prints.
- **Token buy = TWO links.** `Market: <dexscreener pair>` (best-liquidity, from the
  `/latest/dex/tokens` resolver, search fallback) AND `Tx: <explorer>/tx/<hash>` since the
  market link cannot identify the exact purchase. No transaction-link line for NFTs-with-a-slug
  (keeps them compact); the token-buy Tx line is the whole point.

**Per-chain explorer base must be correct — robinhood uses `robinscan.io`, NOT the generic
Blockscout instance.**
```python
def explorer_tx_base(chain):
    return {"ethereum":"https://etherscan.io","robinhood":"https://robinscan.io",
            "solana":"https://solscan.io"}.get(chain, "")
```
The stale `https://robinhoodchain.blockscout.com` base silently points users at a generic
explorer; robinscan.io is the authoritative Robinhood (chain 4663) explorer. Multi-tx sweeps
should cap the printed list (~3) with a `+N more` suffix.

**Do not validate an explorer base with a dummy hash.** A real explorer SPA returns HTTP 200
for ANY path (including a nonexistent 0xaaa), and fake test hashes can return 404 on the
authoritative explorer while a generic instance returns 200 — so the curl-the-dummy-hash
check is misleading. Validate the base by curling a REAL transaction hash you already resolved,
or by trusting the documented explorer authority (robinscan.io = Robinhood chain 4663).
Regression-tested by pointing the token-buy test at `Tx: <explorer>/tx/<hash>` (two `http`
links) and the NFT-no-slug test at `Transaction: <explorer>/tx/<hash>` (one `http` link).

## Fixture trap

ABI data words concatenate without internal `0x`; topics retain `0x`:

```ts
const word = (n: bigint) => n.toString(16).padStart(64, "0");
const topicWord = (n: bigint) => "0x" + word(n);
```

If a merge-window test unexpectedly produces one row, verify the fixture did not reuse one transaction hash: same-transaction logs merge by design.
