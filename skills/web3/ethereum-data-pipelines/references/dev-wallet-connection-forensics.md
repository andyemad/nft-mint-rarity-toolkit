# Cross-project developer-wallet connection forensics (no keys)

Write-up for when a social post claims "same guy did Collection X AND Y" / "X and Y are
run by the same dev" and you must test it on-chain. Verified 2026-08-24 on InkBrokers vs
CornHood (a FUD tweet claiming a shared operator). Complements `dev-fronted-mint-wash-trade-forensics.md`
(single-project dev/go-to-market forensics) — this one is the *two-or-more-collection link test*.

## The workflow

1. **Resolve the contract owner/operator of each project, not the collection editor.**
   The OpenSea `owner`/editor field is a wallet of record but is not always the deployer.
   Call the SeaDrop `owner()` selector (`0x8da5cb5b`) over RPC — the returned address is
   who actually controls the drop.
   For the deployer: a cloned SeaDrop collection is created via `createClone` on the
   cloneable factory — the caller of that tx is the creator EOA.

2. **Profile each owner/deployer wallet to characterize it:**
   - tx count + every tx method (`transactions` endpoint) — a *clean single-project wallet*
     shows only `updatePublicDrop`/config txs to its own contract and nothing else.
   - other collections deployed/held (`token-balances`, any `created_contract` in tx list).
   - cross-chain presence (query the same address on the other chain's explorer, and on
     Ethereum via RouteScan `module=account&action=balance`).
   A wallet with a handful of txs all scoped to one drop = purpose-built operator, NOT a
   repeat scammer. A wallet that repeatedly `createClone`s many collections = flag.

3. **Enumerate every counterparty of both wallets and intersect.**
   Collect `from`+`to` across transactions AND internal-transactions for each wallet.
   The only overlap you find is very likely a shared PROTOCOL contract, not a person.

4. **Identify the overlapping address BEFORE calling it a link.** This is the trap:
   - `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5` is the **SeaDrop** protocol contract,
     present on every EVM chain (Ink and RH both showed `name: SeaDrop`). Every NFT project
     mints through it, and the mint-fund refunds flow back from it to operators. Two projects
     both touching SeaDrop is infra, NOT a relationship.
   - Cloneable factories (e.g. `0x00b19A52...218400` = `ERC1155SeaDropCloneFactory`) are also
     shared infrastructure dozens of unrelated wallets call `createClone` on.
   Only a shared NON-protocol counterparty (an EOA both funded / both paid / both transfered
   to/from) is the evidence of a real connection.

5. **Separate "is true" from "is a fraud caution."** The tweet's factual kernel may be real
   (e.g. "Collection Y never traded" — 0 volume/0 sales/0 owners on OpenSea) while its
   conclusion ("same guy runs X") is unsupported. Report both honestly: a dead companion
   project is a *caution*, not proof the operator overlaps.

## Pitfalls
- Blockscout v2 `transactions?filter=to|from` returns 0 rows / errors — call the plain
  `/transactions` endpoint and read `to`/`from` per row instead.
- `punctuation`/`&` in exploratory shells triggered the sandbox's backgrounding/pipe-to-
  interpreter heuristics — write canned lookups as files, not inline `cat|python`.
- The deployment tx is often NOT in the collection contract's own txlist (cloneable + factory
  on OP-stack chains). Don't conclude "no deployer" from an empty contract tx history — query
  the factory createClone callers or the owner() role.

## Ink chain infrastructure (verified 2026-08-24)
- RPC: `https://rpc-gel.inkonchain.com` (chainId `0xdef1`); works with plain curl + UA.
- Explorer API (blockscout v2, works no-key with browser UA):
  `https://explorer.inkonchain.com/api/v2/addresses/<hash>` (incl. `creator_address_hash`,
  `creation_transaction_hash`, `implementations`, `reputation`, `is_scam`, `token.*`,
  `proxy_type`), `.../transactions`, `.../internal-transactions`, `.../token-balances`,
  `.../token-transfers`, and
  `https://explorer.inkonchain.com/api/v2/tokens/<contract_addr>/holders` (holder counts).
- SeaDrop = `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5`; SeaDrop cloneable implementation
  `0x09a26fC8...81Dd6A` (`ERC721SeaDropCloneable`, eip1167 proxy).
- `reputation: ok` + `is_scam: false` + `is_verified: true` on a SeaDrop cloneable are the
  explorer's honest-health signals for an initial red-flag screen.

## OpenSea listings on Ink (keyless collection page + keyed events feed)
- Collection page `<title>` encodes floor (`"Ink Brokers 0.033 ETH"`) — no-key floor read.
- Rich `collectionBySlug` hydration fragment (brace-count it) carries `floorPrice`,
  `maxSupply`, `totalSupply`, `oneDay.volume`, `listedItemCount`, `ownerCount`.
- Keyed live listings: `X-API-KEY` + `https://api.opensea.io/api/v2/events/collection/<slug>?event_type=listing&chain=ink&limit=30`
  → `asset_events[].asset.identifier` + `payment.quantity` (wei / 1e18 = ETH*). Shows a
  bipolar bid-ask (common tiers at floor, scatter of 1–3 ETH and even 320 ETH long-shot
  listings) — quantify that spread when advising on selling a rare tier.
