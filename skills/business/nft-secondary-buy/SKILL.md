---
name: nft-secondary-buy
description: Buy an NFT off secondary (OpenSea/Robinhood) fast.
version: 1.0.0
author: Hermes
license: MIT
platforms: [macos, linux]
prerequisites:
  commands: [python3]
  files:
    - ~/.hermes/secrets/bot_wallet_key
    - ~/.hermes/secrets/opensea_key
---

# NFT Secondary Buy (fast)

One-shot "buy it now" off OpenSea secondary on Robinhood Chain, using the
designated bot wallet `0x1111111111111111111111111111111111111111`.

Goal: from zero to a **dry-run-verified, signed, ready-to-broadcast** buy in
seconds, so live spend only needs the approval gate — no re-research.

## When to use
- "Buy X", "pick up a broker", "grab the floor on <collection>", "buy off secondary", "snap buy".
- Do NOT use for a fresh/live mint — that's the RH SeaDrop mint flow in
  `~/Projects/rh-mint-bot/mintbot.py`.

## Facts (memorize, don't re-derive)
- RH RPC: `https://rpc.mainnet.chain.robinhood.com` (chainId 4663)
- OpenSea API v2 base: `https://api.opensea.io/api/v2` (needs `X-API-KEY` from `~/.hermes/secrets/opensea_key`)
- Seaport 1.6 protocol on RH: `0x0000000000000068f116a894984e2db1123eb395`
- Buyer key: `~/.hermes/secrets/bot_wallet_key` (0x1111…1111).
- The OpenSea V2 **listings** endpoints work with the API key; the older
  `/orders/{chain}/seaweed/sell/best` paths return 404 on RH. Use
  `/listings/collection/{slug}/best`.

## Fast path (run script, don't hand-roll)
Reference script: `scripts/buy_secondary.py` in this skill.

```
python3 buy_secondary.py <collection_slug>                      # dry-run: floor + cheapest listing + encoded/validated fill
python3 buy_secondary.py <collection_slug> --target-eth 0.001   # only touch listings <= target
python3 buy_secondary.py <collection_slug> --live               # broadcasts (NEEDS APPROVED SLATE FIRST)
```

The script:
1. Reads wallet balance on RH RPC and floor via `/collections/{slug}/stats`.
2. Pulls best listings via `/listings/collection/{slug}/best`.
3. Grabs `/listings/fulfillment_data` for the cheapest candidate.
4. Encodes Seaport `fulfillAdvancedOrder` (reuse the encode logic from
   `~/Projects/sniper/encode_test.py`).
5. `eth_call` dry-runs the fill from the bot wallet — **no spend**.
6. In `--live`, signs and broadcasts.

## Listing (maker) flow — approve conduit FIRST
Creating a listing via `/listings/actions` returns a TWO-step payload in `steps`:
1. `itemApprovalAction` — a `setApprovalForAll` tx approving OpenSea's **conduit**
   operator (NOT the Seaport contract itself). If the wallet never approved this
   conduit, the listing endpoint can fail or the order won't be fulfillable.
   Broadcast this tx first (gas ~0, no value) and wait for status 0x1.
   (Approving only the Seaport contract address is NOT enough — the conduit
   `0x963f00d3ff…` is the operator Seaport actually pulls the NFT through.)
2. `createListingsAction` -> `signatureRequest.message` (EIP-712) -> sign ->
   `POST /orders/{chain}/seaport/listings`.
Select steps by iterating for the key name, not `steps[0]` (order varies).
Verify listings live via `GET /listings/collection/{slug}/best` (check each token+price).

## Rug-risk gate (RUN BEFORE ANY SWEEP — do not skip)
Fresh anonymous floor-stuffed collections are the #1 recurring loss for the user
(e.g. bakemono-crayons 8/19: 1-day-old, no roadmap/community, floor-stuffer stacked
then dumped under everyone's entry — exact in-wash rug). Before sweeping or buying
a low-liquidity floor, check and state:
1. Collection age (created_date in `/collections/{slug}`) — <2 days = high risk.
2. Total supply vs unique owners vs 24h volume — concentrated/thin book = rug-prone.
3. Floor-stuffer identity: are the cheapest listings all ONE maker? Is that maker
   the creator/editor (`owner`/`editors` field)? Same maker stacking floor = likely
   about to dump on you. Cross-check maker against `owner`.
4. Presence of roadmap / community (discord/twitter populated? activity real?).
5. ONLY after these pass does the normal buy flow / approval gate apply.
Prefer liquid, higher-volume collections. If the user is chasing another anonymous
fresh floor, say so plainly and refuse to auto-sweep without his explicit go.

## Approval gate (MANDATORY — never skip)
Buying spends real ETH. A live broadcast is an external financial consequence:
1. Show the dry-run result: target token, exact cost ETH, wallet balance, gas.
2. `workspace_propose` a single slate: recipient = market/counterparty, max
   spend ETH, cancellation = "before broadcast" (unfilled order, no burn).
3. Stop. Only after explicit approval → `workspace_decide` + `workspace_consume`
   → run `--live` → read back tx receipt → `workspace_receipt`.

Never batch-fill or spend past the approved cap. Never let "buy as many as you
can" override a needed hard budget — get a number from the user first.

## Known blocker (see status below)
The OLD advanced-order path (`fulfillAdvancedOrder` for orderbook fills) reverted
**49/49** on RH chain in the BUNKER project — root cause unresolved (suspected
restricted-zone/conduit authorization or encoding detail). BUT: cheap floor
listings on OpenSea here come back as **basic orders**
(`fulfillBasicOrder_efficient_6GL6yc`, flat `parameters`) which dry-run **SUCCESS**
via `eth_call` (verified on robinstr 2026-08-19). So the common floor-buy case
is unblocked. Rules:
- ALWAYS dry-run first; a clean `eth_call` success is a prerequisite.
- If your live fill still reverts, STOP, do not retry blindly, and report the
  revert reason. Debug autonomously before spending more.

## Basic vs advanced order
`encode_fill()` handles both automatically by inspecting `tx['input_data']`:
basic orders have a flat `parameters` key, advanced orders have `advancedOrder`.


## Pitfalls
- **Gas-fee race on RH (EIP-1559):** `eth_gasPrice` can return a legacy value below the block's `baseFeePerGas`, causing "max fee per gas less than block base fee" send failures. Fix: sign a **type-2 tx** with explicit `chainId: 4663` (REQUIRED for type-2), `maxFeePerGas = baseFee + margin`, `maxPriorityFeePerGas` ~2 gwei. Legacy gasPrice works most of the time; retry with type-2 on failure.
- **Sweeping = dedupe by `asset.identifier`.** The floor can contain multiple listings for the SAME token id (re-lists / multiple makers). Buy one listing per unique token or the 2nd fill for that NFT reverts. Dedupe before selecting the N cheapest.
- Older `/orders/…/seaweed/sell/best` and `/listings/…/all` paths 404 or error — use `/listings/collection/{slug}/best`.
- Wallet can look funded in one tool and empty on RH RPC — check the RPC balance, not the browser key.
- Never read/print `~/.hermes/secrets/*` contents into chat.
- No approval = no broadcast, no exceptions.

## Verification
- Dry-run: `eth_call` returns success (non-empty `result`, no `execution reverted`).
- For a confirmed live buy: read the tx receipt `status:0x1` from the RPC before reporting done.
