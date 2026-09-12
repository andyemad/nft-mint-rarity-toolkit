---
name: nft-minter-legitimacy-audit
description: Use when asked "are these minters legit?" to vet a launch.
---

# NFT Minter Legitimacy Audit ("are these minters legit?")

Answer whether a collection's mint was organic (real individual buyers) or
manufactured (dev-fronted / wash-traded). Verdict first, then the evidence.
Built and verified 2026-08-24 on Terminal Kids (`0xbe7342625609ea2dcaf5708db6432fec38a7fabb`,
Robinhood, deployed same-day): minters proved legit (947 submitters ≈ 948 recipients,
uniform 4.5/lib), but 1,081 tokens were parked in the contract — the real flag.

This is the MINTER-side forensics. For the developer-payout ring and OpenSea
stats analysis see `ethereum-data-pipelines` `references/dev-fronted-mint-wash-trade-forensics.md`
and `references/opensea-activity-and-small-cap-trade-assessment.md`.

## When to use
- "are these legit minters?" / "is this launch organic?" / "vet this minter set"
- Judging whether a fresh drop's traction is real before considering a buy.

## Reusable script
`scripts/minter_legitimacy.py <contract_address> <deploy_block>` does the whole
scan (mints + all transfers + recipient/submitter/payment/wash-ring) and dumps
JSON + a verdict summary. Run in the background (`notify_on_complete=true`) —
deploy-to-head on Robinhood is ~159k blocks ≈ 159 chunked getLogs, minutes.

For a NEW collection, find `deploy_block` first:
- Blockscout creation tx: `GET /api/v2/addresses/<contract>` → `creation_transaction_hash`,
  then `GET /api/v2/transactions/<that_tx>` → but `block` is often `None`. Use the RPC
  instead: `eth_getTransactionByHash(<creation_tx>)` → `int(blockNumber,16)` (verified).

## Recipe
1. **Identity** — Blockscout `/api/v2/tokens/<contract>`: name, symbol, type,
   `reputation` (`ok` at minimum), `holders_count`. Also `/api/v2/addresses/<contract>`
   for `creator_address_hash` + `creation_transaction_hash`, and `/api/v2/transactions/<creation_tx>`
   for `from` (deployer) + `timestamp` (age — says it all if it's same-day).
2. **Collect all Transfer logs** from deploy block to head, chunked `eth_getLogs`
   ≤1000 blocks (arrowrpc hard cap — bigger ranges 429 with `-32005`). Mints =
   topic0 == TransferTopic && topics[1] == 0x0000…0000 (from zero). Also grab all
   secondary transfers (from != 0) for wash-ring.
3. **Recipient concentration**: count unique mint `to` addresses vs mint events.
   `≈1`-per-wallet + many wallets = organic. One dominant recipient = check if it's
   the contract itself (reserved inventory) or a single wallet (dev fronting).
4. **Submitter concentration**: batch `eth_getTransactionByHash` over unique mint
   tx hashes (≤20/batch, sleep ~0.4s). Count `tx.from`. **The key tell: dev-fronted
   mint = ~95%+ mint txs submitted by ONE wallet, minting to hundreds of recipients
   who paid nothing on-chain.** Clean signal = unique_submitters ≈ unique_recipients.
5. **Payment mix**: count mint txs by actual `tx.value` (GROUND TRUTH — never
   classify by stage-time buckets; stage times misclassify whenever windows don't
   overlap). Dutch-curve collections show a spread (floor + higher early prices).
6. **Wash-ring** on secondary transfers: wallets that both bought AND sold, and
   transfers packed into few txs (a tx with 9 transfers = batched washes). On a
   same-day young launch, a handful of both-sell-buy wallets is mild residue, not
   manufactured — size it against the total mint count before crying foul.
7. **Reserved-supply check (the easy miss)**: the LARGEST mint recipient is often
   the contract address itself (e.g. 1,081/4,335 = 25% minted to contract). That's
   withheld/dev-controlled inventory — the real caution even when minters are clean.
8. **Verdict**: minter set legit/manufactured + the real risk (reserved supply),
   dev's gross take (Σ paid mint values), net $ / time / risk framing — no %-ROI
   dressing.

## Pitfalls
- **From-zero topic is a 32-byte word**: pass `0x` + 64 zeros, not a 40-hex address.
- **OpenSea may not have indexed a same-day collection** — the contract page returns
  the generic title ('' token trading'') and v2 API 401s keyless. Rely on Blockscout +
  RPC, not OpenSea, for brand-new launches.
- **Mint events ≠ token count**: count mint EVENTS; an ERC-1155 batch is one event
  with quantity. For ERC-721 (this shape) events ≈ tokens.
- **Never use stage-time buckets for payment** — always actual tx.value.
- Batch the RPC calls; single-call getLogs over 1000 blocks fails with 429.
