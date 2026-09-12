# Wallet Radar alert message building + token-buy USD enrichment

## Where the Discord alert text is built
- Alerts are formatted by `format_discord_message()` in
  `~/Projects/wallet-radar-rebuild/app/backend/services/wallet_radar_alerts.py`.
- Flow: EVM scanner (`wallet_radar.py`) emits events → daemon
  `run_once()` calls `alerts.record_event()` → `AlertStore` groups/sweeps →
  `OutboxDispatcher` POSTs to the Discord webhook. Do NOT edit the Next.js
  `~/Projects/wallet-radar` (a predecessor dashboard) for alert text.
- Event dict keys (from `drain_events()`): `chain, wallet, kind, asset
  (= token/collection contract), quantity (raw uint256), timestamp, tx_hash,
  token_id`. `classify_evm_receipt()` emits `kind` of `nft_mint / nft_buy /
  token_buy`.
- Three formats exist: NFT → `**label** bought/minted N NFT(s) on X` +
  OpenSea or Transaction link; token buy → Market + Tx links.

## Token-buy USD enrichment (shipped 8/31)
Token buys now read `**czar** bought ~$1.80 of CACHE on Robinhood` instead of
`bought 505007715001129979998 tokens on Robinhood`.
- `resolve_token_quote(chain, asset, rpc_fn, client)` in `wallet_radar_alerts.py`
  returns `{price_usd, symbol, decimals}` or `None`.
  - **price**: `https://api.dexscreener.com/latest/dex/tokens/{asset}`, pick
    the highest-liquidity pair. `priceUsd` is the **base token's** price →
    ONLY trust pairs where `baseToken.address == asset` (the bought token)
    so the price matches the asset. If the asset only appears as
    `quoteToken`, return None (don't guess a wrong USD).
  - **decimals**: on-chain `eth_call` `0x313ce567` (`decimals()`) on the
    token contract, via the daemon's `evm.rpc`. Requires BOTH price and
    decimals; if either is missing return `None` → `format_discord_message`
    falls back to the raw-quantity line. Never print a guessed USD.
  - USDC 6-dec, most ERC-20/ETH (incl. WETH, RH tokens like CACHE / QUOTRON)
    18-dec confirmed.
- `AlertStore.__init__` takes a `quote_resolver`; the daemon wires
  `partial(resolve_token_quote, rpc_fn=evm.rpc)` in `from_paths()`. Only
  resolved for `kind == "token_buy"` on EVM chains; quote cached per
  `(chain, asset)`.
- `_fmt_usd()` formats `$1,234.56` (>= $1) or `$0.0045` (< $1).

## dexscreener gotcha (cost me a wrong probe)
The alert's `Market: <https://dexscreener.com/robinhood/0x…>` slug is the
**PAIR** address, not the token contract. Calling
`/latest/dex/tokens/{pairAddr}` returns `{"pairs":null}`. Query the token with
the token contract (`asset`), or hit `/latest/dex/pairs/{chain}/{pairAddr}` for
a pair. Both return `priceUsd` + `baseToken.symbol`.

## Tests
- `~/Projects/wallet-radar-rebuild/app/tests/unit/test_wallet_radar_alerts.py`
  (run: `cd app && .venv/bin/python -m pytest tests/unit/test_wallet_radar_alerts.py -q`).
  Covers USD formatting, quote resolution via mocked dexscreener + fake rpc_fn,
  and raw-quantity fallback.

## Known pre-existing unrelated test failure
`tests/unit/test_wallet_radar_evm_tokens.py::test_exact_entity_config_contract`
asserts the entities config has **8** entities, but the live
`app/data/wallet_radar_entities.json` has **9** (a 9th entity was added
without updating that contract test). Not caused by alert changes; don't treat
it as a regression.

## Note
Robinhood RPC throttles this IP with 429 (`eth_blockNumber`/`eth_getLogs`
errors in `wallet_radar.err.log`). A single `decimals()` eth_call still
works; on failure the quote returns None and the alert degrades to raw, which
is safe. This is an environment condition, not a code bug.
