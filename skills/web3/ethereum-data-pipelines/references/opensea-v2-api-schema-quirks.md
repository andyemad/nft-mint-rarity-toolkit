# OpenSea V2 API schema & RPC quirks (keyed reads)

Verified 2026-08-31 while running a full `nft-market-analysis` on Argonauts (Ethereum mainnet). These are the request/schema traps that cost the most time on keyed OpenSea V2 reads and on the Ethereum no-key RPC. For the trade-EXECUTION path (fulfill/relist signing), see `opensea-v2-orderbook-buy-relist.md`.

## Cursor + event key
- Every collection/events/listings/offers endpoint returns `next` as an **opaque base64 cursor**, never a URL. Build the next request as `?limit=100&next=<cursor>` on the SAME path — do NOT assign `next` straight into the URL variable (that passes the base64 token as the full URL and crashes with `ValueError: unknown url type`). Hit twice on Argonauts.
- The events endpoint returns the array under key **`asset_events`**, NOT `events`. Reading `.get("events")` silently returns `[]` while `next` keeps paginating → an empty tape that looks like "no sales" but is actually a wrong-key bug.

## Sale-event schema
An `event_type=sale` item has `asset`, `seller_account`, `winner_account`, and `listing` as **null** at the top level. The real fields are:
- `payment` `{quantity (wei string), token_address, decimals, symbol}` — symbol is `ETH` or `WETH`.
- `seller`, `buyer` (addresses), `quantity`, `closing_date`, `transaction`, `order_hash`, `protocol_address`, `chain`.
- `nft` `{identifier, traits[], name, opensea_url}` — traits come free with each sale.
Dedupe by `(transaction, order_hash, nft.identifier, buyer, seller, closing_date)`; a single `transaction` can carry several item sales (a bundle).

## Settlement currency (Ethereum mainnet)
ETH-mainnet sales settle in BOTH native ETH and WETH (Argonauts: 1006 WETH / 1594 ETH in a 2600-sale sample). Compute each price from `payment.quantity / 10**payment.decimals` regardless of symbol; never assume a single currency. (Contrast Robinhood chain, which settles in WETH only.)

## fulfillment_data (buy path)
`POST /api/v2/listings/fulfillment_data` (GET returns 405). Body `{"listing":{"hash","chain","protocol_address"},"fulfiller":{"address"}}`. Newer Seaport 1.6 listings return a **basic-order** `function` like `fulfillBasicOrder_efficient_6GL6yc(...)` (not the documented `fulfillAdvancedOrder`), and the tx `value` / `value_hex` = the full native-ETH price. `input_data.parameters` holds the structured order: `considerationAmount` = seller net, `additionalRecipients[].amount` = the creator fee (Argonauts: 0.193 price → 0.192753 seller net → 0.001947 = 1% fee). Buyer break-even relist = `price / (1 - fee_rate)`.

## eth.drpc.org (Ethereum no-key RPC)
- eth_call batches: ~45-call batch → HTTP 500; ~12 per batch with retry/backoff works; single calls fine. Requires a curl-like `User-Agent` (also documented in SKILL.md).
- **Value-bearing eth_call needs a funded `from`.** A read-only simulation of a buy (tx with `value` = price) is rejected `-32000 insufficient funds for gas * price + value: address … have 0 want …` unless the `from` address holds enough ETH. For a pure dry-run, set `from` to a funded address (a known holder/whale — e.g. the floor-maker with 17 ETH on Argonauts); it is read-only, no funds move. The funding gate is hit BEFORE the calldata executes, so an unfunded `from` tells you nothing about the order's validity.
