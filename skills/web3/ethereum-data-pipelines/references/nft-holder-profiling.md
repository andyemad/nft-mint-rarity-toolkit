# NFT Holder-Profile Assessment (Robinhood Chain, keyless)

Goal: answer "who is holding this collection?" — wallet types, notable holdings,
whales/degens, mint fairness, and a verdict a trader can act on. Verified 2026-08-17
on Bancroft (`0xee64340e4f3465f53249e5b035dc67cc3e320961`, 624 supply, RH chain);
re-verified 2026-08-26 on The Sunday Society
(`0x063ba98d0c2bc778e3ebdb5ef79e6a9e18e97e43`, 102/222 minted, 84 holders).

All data below is keyless: RPC (`rpc.mainnet.chain.robinhood.com`, UA required) +
Blockscout v2 (`https://robinhoodchain.blockscout.com`) + OpenSea public page.

**Wallet exclusion rule:** when Emad asks for a holder analysis, his own wallet
(0x1111…1111 and any he names) must be filtered out of the holder list, the
profiling loop, and the report — never analyzed or mentioned
("do not analyze or mention mine"). Apply the filter BEFORE profiling.

**Preferred primary source (2026-08-26): Blockscout token endpoints, not RPC getLogs.**
`/api/v2/tokens/{CA}/transfers?` (paginate via `next_page_params`) returns the
collection's FULL transfer history with timestamps + tx hashes, and
`/api/v2/tokens/{CA}/holders?` returns the authoritative current holder map with
per-wallet counts (`value`) and ENS names. Both worked cleanly at ~0.35s pacing and
carried the entire Sunday Society run when arrowrpc getLogs 429-stormed for the whole
2.5M-block scan window. Each transfer row carries `from`/`to` address objects (with
`ens_domain_name`) and `total.token_id`; `from.hash` == zero address = mint. This
replaces steps 3–5 below as the default; keep the RPC getLogs path only as fallback.

## Recipe

1. **Contract probe (one batched RPC call)**: name / symbol / totalSupply (`0x18160ddd`) /
   owner (`0x8da5cb5b`) + `eth_blockNumber`. 624 supply, owner = dev wallet.
   Pair with keyless `https://api.opensea.io/api/v2/chain/robinhood/contract/<addr>` for
   collection slug, standard, and chain confirmation.

2. **OpenSea page hydration** (`https://opensea.io/collection/<slug>`): the page embeds
   several `collectionBySlug` fragments; pick the one containing BOTH `stats` and `name`
   (parse by brace matching, not regex). Rich fragment gives: `stats` (totalSupply,
   uniqueItemCount, ownerCount, listedItemCount, volume with native symbol — USDG on RH —
   and rolling windows oneMinute..thirtyDays), `drop` (SEADROP_V1_ERC721 stages with
   startTime/endTime/price), `description`, `isVerified`, `owner` profile (dev display
   name/address), socials. When a collection is a meta-art project, the description IS
   the pitch — read it.
   Note: page `<title>` also exposes floor keyless ("Bancroft 8.95 USDG - Collection | OpenSea").

3. **Find creation block**: Blockscout `/api/v2/addresses/{addr}` → `creation_transaction_hash`
   (and `creator_address_hash` = dev EOA). Blockscout `/api/v2/transactions/{hash}` gives the
   timestamp but NOT `block` (None); use RPC `eth_getTransactionByHash` for blockNumber.

4. **Full Transfer log scan** (chunked ≤1000 blocks, from creation block to latest):
   `eth_getLogs` with `topics: [TransferTopic]` — need ALL transfers (mints + secondary) to
   build the holder map. 624 supply ≈ ~900 events, ~20s of scanning. Keep `(block, tx,
   logIndex, from, to, tokenId)`.

5. **Holder map**: `final_owner[tokenId] = to` of the LAST non-burn transfer; count per
   wallet = current holdings. Mint-fairness check: 624 mint events / 624 unique minters =
   perfectly even launch (no whale mint). Compare with current holders (459) — the delta is
   post-mint distribution.

6. **Sales**: `eth_getTransactionByHash` batched ≤20/call, sleep ~0.4s between batches,
   retry-3 on 429 (verified against 834-tx scan; a 50-batch 429s). `value>0` transfer tx =
   sale; value = price in wei. Aggregate; note multi-transfer txs (bundle buys) so tx value
   spreads across n tokens — per-token ≈ value/n only for single-transfer txs; a 9-token
   buy at 0.0449 ETH in ONE tx is ~0.005/token, not 0.0449. Caveat: RH Seaport can settle in
   WETH/USDG (ERC-20), so tx.value>0 is the NATIVE lower bound; OpenSea's volume window
   (USDG) is the ERC-20-inclusive total. Report both.

7. **Top-holder wallet profiling** (Blockscout, the key win): for top ~20-60 holders,
   fetch `/api/v2/addresses/{addr}` + `/api/v2/addresses/{addr}/token-balances` (both work;
   `token-transfers` 422s). Per wallet: `coin_balance`/1e18 = ETH, `ens_domain_name`,
   `is_contract`, and NFT bags (name → count). Aggregate "collections held by ≥2 top
   holders" to describe the wallet TYPE (e.g. RH degen ecosystem: Robindroids, The Unusuals,
   Numbers, Workers, Sherwood, whi cats, Retail Punks, Inference Angels).

8. **Notable holdings**: for the highest-frequency other collections, hit
   `https://opensea.io/collection/<slug>` and read the `<title>` floor. Floor > collection's
   own floor = "notable". Separate spam/dust (sub-$0.50) from real (Retail Punks 11.70 USDG,
   Sherwood ~0.005 ETH). Whale test: any top holder with >5 ETH or known ENS? 43/60 holding
   $100+ USDG = real buyers with dry powder.

## Deliverable shape (matches Emad's read)

- **Basics**: supply sold out?, mint price, floor, volume (all-time + hour), owners/listed %,
  verified/socials, and the collection CONCEPT (2-3 lines).
- **Holding profile**: mint fairness (even vs whale), concentration (top-10 %), biggest buyer + his buy price level.
- **Notable wallets**: name (ENS) → Bancroft count → their other notable bags; flag priced-item holders.
- **Verdict-style read**: smart-money presence / no-whale signals, same-day momentum status,
  distribution timing (sellers vs buyers), and the price level to watch (the flippers' batch-buy
  level). Keep it action-framed, not a data dump.

## Pitfalls

- **Blockscout token endpoints are the fast path now** (2026-08-26): `/tokens/{CA}/transfers`
  and `/tokens/{CA}/holders` both paginate cleanly via `next_page_params` at ~0.35s pacing.
  When arrowrpc getLogs 429s across a large scan window, DON'T burn the whole analysis on
  RPC retries — switch to these two endpoints; transfers give the full history, holders give
  the authoritative current map with per-wallet `value` (count) and ENS. (Earlier notes said
  these 422'd — that was stale; verified working 2026-08-26.)
- **`/api/v2/addresses/{CA}` can 500 while `/api/v2/tokens/{CA}` works** — same contract,
  same explorer. If the address endpoint returns "Internal server error", hit the token
  endpoint instead; don't treat it as explorer-down.
- **OpenSea stats "sales" counts MINTS as sales.** The Sunday Society showed 69 "sales" but
  only 13 were real secondary transfers — the rest were mints. Never report OpenSea's sales
  count as secondary-market activity; compute real secondaries from the transfer history
  (from != zero address) and say so.
- **The OpenSea events feed (`/api/v2/events/collection/{slug}?event_type=sale`) can reject
  an otherwise-valid API key** ("Invalid API key") while `/collections/{slug}` and `/stats`
  accept the same key in the same session — tier-gated. Don't loop retrying it; fall back to
  on-chain transfer reconstruction for sale activity.
- **When mint is still open, say so** — if totalSupply < maxSupply and the last mint
  timestamp is recent, the collection is mid-distribution, not sold out. That changes the
  floor-pressure read entirely (no scarcity pressure until mint closes).
- **Dev-wallet selling is the one bearish tell worth surfacing on a young collection.**
  Identify the dev/creator wallet (from `owner` field or creation tx) and check whether it
  appears among secondary SELLERS, how many, and how recently. A dev dumping reserve into a
  fresh low-supply collection is a red flag even in small amounts.
- Zero-address topic compare: mint detection compares `from` to `0x` + 40 zeros (addr form),
  NOT the 64-zero word used in the topics filter — a 64-zero compare silently finds 0 mints.
- Blockscout checksummed hashes: `.lower()` both sides.
- token-balances ERC-20 `value` is RAW units — divide by token decimals.
- Some wallets hold millions of a sender's fungible token (e.g. BANC on the dev's same
  collection) — token-bag of record ≠ price-relevant.
- New contract at block ~38.45M, scan window is small; for older collections chunk from
  creation — getLogs chunks must stay ≤1000 (arrowrpc hard cap).