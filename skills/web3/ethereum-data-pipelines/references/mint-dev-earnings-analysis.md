# Mint dev-earnings analysis ("how much money has the dev made?")

Verified 2026-08-14 on FlayingCats (Robinhood Chain, ERC721SeaDropCloneable).
Recurring user question: how much has a collection's dev made from mint + royalties?

## Answer shape (concise)

- **Mint revenue** = paid mints × stage price. Free stages earn nothing.
- **Royalties** = 0 unless `royaltyInfo()` returns a nonzero recipient/amount.
- **Proceeds destination** — check whether the mint ETH actually reached the dev:
  contract balance, dev-wallet balance, and the SeaDrop fee-splitter route.

## Recipe (no API keys — public RPC + OpenSea page)

1. **Get stage schedule + prices** from the OpenSea page's GraphQL hydration JSON
   (`SEADROP_V1_ERC721` fragment): stages carry `stageIndex`, `startTime`,
   `endTime`, `price.token.unit` (ETH) + `price.usd`. Stage 0 is usually the
   paid/public stage; stages 1+ may be free windows. `totalSupply` =
   `maxSupply` when sold out. This gives the exact paid/free boundary timestamp.

2. **Find the boundary block** for the paid-stage start time via binary search
   on `eth_getBlockByNumber`: first block whose `timestamp >= target_ts`.
   (Robust — do NOT assume a block offset from the mint start.)
   **Caveat (Brokers Holders 2026-08-15): stage windows can predate the actual
   mint entirely** — stages were set for Aug 13–14 but all 715 mints happened
   Aug 15, so stage-time bucketing classified everything into the final stage.
   Cross-check with the successful mint receipts and their protocol-semantic mint
   events. A direct mint's outer `tx.value` is useful, but it is **not always ground
   truth**: Relay `multicall` / `transferAndMulticall` and account-abstraction
   `handleOps` transactions may have outer `value=0` while an inner call pays the
   mint from a router or smart-account balance. For SeaDrop, decode the
   `SeaDropMint` log (`topic0 = 0xe90cf9cc0a552cf52ea6ff74ece0f1c8ae8cc9ad630d3181f55ac43ca076b7d6`):
   its data words include payer, quantity, mintPrice, feeBps, and stage index.
   Compute gross as `sum(quantity × mintPrice)` across successful mint calls, and
   use outer `tx.value` only as a reconciliation check. Stage-time buckets remain
   only a classifier. For dev-fronted / wash-trade analysis of the same wallets,
   see `dev-fronted-mint-wash-trade-forensics.md`.

3. **Count mints per stage**: `eth_getLogs` for `Transfer` topic0 with
   `topics[1]` = the 32-byte zero word (from = zero → mint), chunked ≤1000
   blocks (arrowrpc hard cap; over-range answers 429 + -32005). Bucket each
   log by `blockNumber` vs the boundary block → paid vs free counts.

4. **Royalty check**: `eth_call` `royaltyInfo(uint256,uint256)` (selector
   `0x2a55205a`) with e.g. tokenId=1, salePrice=1 ETH. Zero recipient +
   zero amount = no royalties. Also confirm with
   `supportsInterface(0x2a55205a)` (ERC-2981).

5. **Proceeds destination**: `eth_getBalance` on the contract and dev wallet.
   SeaDrop clones route mint funds through the fee splitter
   (`0x00005ea0...`, log topic `0xe90cf9cc...`) — the contract balance drains
   to near zero while the dev EOA may hold almost nothing, so "dev wallet
   balance ≈ 0" does NOT mean the dev earned nothing; the ETH went through
   the splitter to the creator payout address. Report the revenue number
   (paid mints × price) as the dev's mint take, note where it routed.

6. **Dev inventory**: `eth_call` `balanceOf(dev)` on the NFT contract — unsold
   or withheld tokens are an asset, not revenue.

## the rarity-test collection / raritytest-888 worked numbers (2026-08-19, RH chain 4663)

- 5,000 supply, sold out same-day launch. Contract `0x512faa1354c8d634cd0e78e6ec5ba1d9fe19d55c`
  (ERC721). Stages (hydration JSON `SEADROP_V1_ERC721`): stage 1 FREE "TEAM" signed presale
  (13:45–14:00 UTC), stage 2 whitelist 0.001 ETH (14:00–15:00), stage 0 public 0.001 ETH (15:00 on).
  One paid price = 0.001 ETH (~$2.099; ETH ≈ $2,098.53).
- **BATCHED-MINT GOTCHA:** 5,000 mint events but only 2,667 unique mint txs — many txs mint multiple
  tokens. Do NOT read revenue off the paying-tx count. Count paid mint **EVENTS** (each
  `Transfer`-from-zero log) weighted by its tx's `eth_getTransactionByHash` value: 4,666 paid events
  × 0.001 = **4.666 ETH ≈ $9,790**, 334 free TEAM events. Summing every distinct mint tx's value also
  gives 4.666 ETH — cross-check paid-events×price gives the same total.
- `royaltyInfo` = 0 → **$0 royalties**. Contract balance 0 (SeaDrop splitter routes mint ETH to the
  creator payout address, not the EOA).
- **Bottom line shape for the user:** "dev made X from the mint, $0 royalty tail", note batched minting.

## Piggy Banks worked numbers (2026-09-04, RH chain 4663)

- Contract `0xf39d4c50a08e0fdafc51d37fc92bd2c25191da6a`, 3,333/3,333 minted in
  940 unique transactions. Robinscan's token-transfer endpoint paginates at a
  maximum `pageSize=50`; filtering `from == 0x000…000` recovered all mint transfers.
- Naively summing distinct outer transaction values produced **41.78 ETH** and
  falsely classified 142 tokens in 43 Relay/account-abstraction transactions as
  free because those outer transactions had `value=0`.
- Decoding the SeaDrop semantic mint logs and the one nested Relay calldata call
  recovered the actual tier distribution: 3,000 × 0.01 ETH, 300 × 0.03 ETH,
  30 × 0.10 ETH, and 3 × 0.50 ETH = **43.5 ETH gross**. The tier quantities sum
  exactly to totalSupply, an important completeness invariant.
- Every sampled/decoded stage used `feeBps=1000` (10%), yielding **39.15 ETH
  creator net** and **4.35 ETH fee-recipient share**. Report gross and creator net
  separately; do not call outer-value-zero routed mints free.

## FlayingCats worked numbers (2026-08-14, chain 4663)

- 9,999 supply, sold out same day. Stages: 1–3 free (0 ETH, 1-min windows),
  stage 0 paid 0.00008 ETH (~$0.15; ETH ≈ $1,877).
- Free mints 1,706 / paid mints 8,293 → mint revenue 0.6634 ETH ≈ **$1,245**.
- `royaltyInfo` = 0 → **$0 royalties** (dev earns nothing on secondary).
- Contract balance 0 (routed via SeaDrop splitter); dev EOA ~0.0009 ETH;
  dev still holds 100 tokens.

## Finding the mint window (RH archive quirk)

The RH RPC archive does NOT serve `eth_getCode` for blocks below ~20.3M (answers error `-32000
"metadata is not found, <blocknum>"`). Do NOT binary-search deployment to locate the mint region —
that path dies on the archive floor. Instead **calibrate block↔date from recent blocks** (read
timestamps at `latest`, `latest-1000/10000/100000/1e6` to derive blocks-per-window), convert the
known mint dates (stage start) into a block range, then `eth_getLogs`-scan that bounded window for
`Transfer`-from-zero logs. Mint-window scans of ~100k blocks are comfortable; full-history scans from
block 0 to 40M in 1000-block chunks are far too slow — always narrow to the launch window via the
OpenSea `createdAt` / stage timestamps first.

## Resume-after-restart gotcha

A gateway restart kills a long-running research task mid-analysis and then
auto-resumes it with a status post (see hermes-gateway-notification-config
leak #7). The transcript survives in `~/.hermes/state.db` (messages table,
session id from the gateway routing) and any scratch script the run wrote
(`/tmp/rpc_probe.py` etc.) is still on disk — read those to resume the exact
step instead of restarting the analysis from scratch.
