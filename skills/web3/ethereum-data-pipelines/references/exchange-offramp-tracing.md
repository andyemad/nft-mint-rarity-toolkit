# Exchange off-ramp tracing — confirmed addresses & workflow notes

Gathered 2026-08-11 while tracing off-ramps from `0x2222222222222222222222222222222222222222` (Ethereum mainnet). These labels were verified by parsing the Etherscan address page title / Public Name Tag, NOT by keyword grep (the sidebar pollutes every page with Coinbase/Gate/etc.).

## Confirmed labeled addresses (Ethereum mainnet)

| Label | Address | Role seen |
|---|---|---|
| Coinbase: Deposit | 0x078fd53afea3d22fbb1377016d268147ce6e75ab | per-user deposit; forwards to Coinbase 23 / Coinbase 44 / unlabeled a9d1e0 |
| Coinbase 23 | 0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740 | hot wallet |
| Coinbase 33 | 0x3cd751e6b0078be393132286c442345e5dc49699 | hot wallet |
| Coinbase 44 | 0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511 | hot wallet |
| Coinbase 54 | 0xeb2629a2734e272bcc07bda959863f316f4bd4cf | hot wallet |
| Coinbase: Miscellaneous | 0xa090e606e30bd747d4e6245a1517ebe430f0057e | hot wallet |
| ChangeNOW: Hot Wallet 4 | 0xeba88149813bec1cccccfdb0dacefaaa5de94cb1 | hot wallet |
| Binance 14 | 0x28c6c06298d514db089934071355e5743bf21d60 | hot wallet |
| KuCoin 13 | 0xd89350284c7732163765b23338f2ff27449e0bf5 | hot wallet |
| TradeOgre 1 | 0x4648451b5f87ff8f0f7d622bd40574bb97e25980 | hot wallet |

## Deposit-gateway chains observed (wallet → gateway → hot wallet)

- Coinbase: 0x1c3e5007…/0xbd38813f…/0x0abf04e1…/0x256ae10d… → Coinbase 54; 0xecf1fed8…/0xc12eab7c…/0x08b2c1c1… → Coinbase Misc; 0x46aeb5ea… → Coinbase 33; 0x348bb2fc… → Coinbase 44; 0xda17fae9… → Coinbase 23.
- ChangeNOW: 0xd9ece6a0…/0x9ca5f67e…/0xdb6464a7… (+ tiny 0xef02cf02…, 0xf8ef55d3…) → ChangeNOW Hot Wallet 4.
- Binance: 0x1adda1f0… → 0x556fce60… → Binance 14 (same-day forwarding).
- KuCoin: 0xc7dd0d7f… → KuCoin 13.
- TradeOgre: 0xc59c5214… (18 deposits) → TradeOgre 1.

## Unlabeled consolidation nodes (likely instant-exchange, unconfirmed)

- 0x077d360f11d220e4d5d831430c81c26c9be7c4a4 — receives many small per-user deposits (0.1–2 ETH) and forwards; classic ChangeNOW-style gateway. ~6.5 ETH traced from one wallet. No public label → report as unconfirmed.
- 0xa9d1e0859b52d05e4e0dabf13c7c6956658d64f1 — contract (RouteScan txlist empty, eth_getCode = code) receiving from multiple gateways incl. a Coinbase Deposit forward; identity unconfirmed.
- Other unlabeled bulk forwarders: 0x2b3726c7…, 0x0db1273c…, 0x33ed6610…, 0x6ec794ca…, 0x90cee21b…, 0xf60c2ea6… .

## Not off-ramps (easy to misclassify)

- Reservoir: Relay Receiver 0xa5f565650890fba1824ee0f21ebbbf660a179934 — NFT marketplace payment processor (buy-side).
- Recipients that return most funds to the origin wallet = the user's own second wallet (e.g. 0x0fd04957… returned 22.5 of 24.4 ETH).
- DUMMY: Deployer 0x749d02b2… — label of a scam-fake project deployer, not an exchange.

## Workflow notes

- Attribute off-ramp value by the direct sent amount to the gateway, capped at what the gateway forwarded (gateways carry multiple users).
- ETH→USD at deposit date: join to Yahoo daily closes (`https://query1.finance.yahoo.com/v8/finance/chart/ETH-USD?period1=…&period2=…&interval=1d&events=history`).
- RouteScan `txlistinternal` returns empty for contracts — do not rely on it; use outer-tx traces or a different indexer for internal transfers.
- Same-day two-hop forwarding (gateway→hot wallet) is a strong exchange-deposit signal even when the gateway is unlabeled.
