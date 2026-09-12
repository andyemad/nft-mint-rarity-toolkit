# NFT sweep average price in ETH

NFT-buy alerts now append `(~X ETH avg)` — e.g.
`**tma** bought 15 NFTs (~0.1 ETH avg) on Ethereum`. The average = total
payment across the sweep ÷ number of NFTs bought.

## The WETH gotcha
Marketplace (Seaport) fills usually settle in **WETH**, so `tx.value == 0`.
Using native `tx.value` alone would print a wrong `~0 ETH avg`, so the payment
must be attributed from the WETH the buyer sends OUT.

`classify_evm_receipt()` in `app/backend/services/wallet_radar.py` computes
`payment_eth_wei` per tx:
- `tx.value > 0` → that value (ETH-settled fill), else
- sum of the wallet's outgoing non-NFT transfers where
  `contract == WETH_BY_CHAIN[chain]` (WETH is 1:1 with ETH), else
- `0` (unknown settlement token → the alert omits the avg entirely).

## WETH addresses (WETH_BY_CHAIN, wallet_radar.py)
- ethereum: `0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2`
- robinhood: `0x1111111111111111111111111111111111111111`

Verify via an `eth_call` to `name()`/`decimals()` if ever in doubt — the
Robinhood address returns name `"WETH"`.

## Flow to the message
1. `classify_evm_receipt` → event field `payment_eth_wei`.
2. `process_evm_receipts` copies it into the alert event it hands to
   `drain_events()`.
3. `record_event` in `wallet_radar_alerts.py` aggregates it across the sweep
   window (sums into `total_eth_wei`), persisted in the
   `entity_alerts.total_eth_wei` column (auto-migrated by
   `AlertStore.initialize` via `ALTER TABLE ... ADD COLUMN`).
4. `format_discord_message` renders `(~{_fmt_eth(avg)} ETH avg)` where
   `avg = total_eth_wei / 1e18 ÷ quantity`, only for `kind == "nft_buy"` and
   when `total_eth_wei > 0`. `_fmt_eth` trims trailing zeros.

## Tests
- `tests/unit/test_wallet_radar_evm_tokens.py`:
  `test_nft_buy_settled_in_weth_attributes_eth_equivalent_payment` — WETH
  settlement (tx.value 0) → `payment_eth_wei` from the WETH transfer.
- `tests/unit/test_wallet_radar_alerts.py`:
  `test_nft_buy_with_payment_shows_average_eth`,
  `test_nft_buy_without_payment_omits_average_eth`,
  `test_record_event_aggregates_eth_wei_across_sweep`,
  `test_nft_buy_multiple_purchases_reports_average_eth`.

`wallet_radar.py` events also carry `payment_wei` (the raw `tx.value`) which
is written to the `activities.value_wei` column and used by the board — keep
both fields, they serve different consumers.
