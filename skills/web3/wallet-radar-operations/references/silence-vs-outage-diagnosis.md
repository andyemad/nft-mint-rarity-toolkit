# Wallet Radar silence vs outage diagnosis

Use when the user says the tracker is broken because alerts stopped.

## Evidence ladder

1. **Process:** `launchctl print gui/$(id -u)/com.hermes.wallet-radar`; a PID is necessary, not sufficient.
2. **Ingestion:** read `cursors` twice about 15–30 seconds apart. Compare with live `eth_blockNumber` for Ethereum and every Robinhood primary/fallback RPC. A current cursor that advances proves scanning; a stale cursor plus repeated errors is an outage.
3. **Delivery:** group `alert_outbox` by `status`; inspect latest `delivered_at` and `last_error`. Do not reset dead rows during diagnosis.
4. **Authoritative channel:** fetch recent Discord `#alerts` messages and match the latest webhook message timestamp to the delivered outbox row. Empty Discord `content` is normal because Wallet Radar uses embed descriptions.
5. **Activity audit:** inspect all watched-wallet activity since the last delivered alert and ask whether any receipt satisfies the production classifier.

## Qualifying vs intentionally silent

- Direct NFT mint: successful wallet-submitted receipt and NFT transfer `zero address -> watched wallet`.
- NFT buy: inbound NFT plus verified payment and marketplace-fill evidence.
- Token buy: inbound fungible token plus verified swap/payment semantics.
- Intentionally silent: outgoing NFT transfer, approval, burn, game/quest action, ordinary receive, proxy-forwarded mint without dedicated classification, ambiguous mixed-asset receipt.

A wallet can be highly active while generating zero valid alerts. Name the observed excluded action instead of saying merely “no activity.”

## Audit sources and limits

- Primary/exhaustive: bounded, position-specific `eth_getLogs` filters over the exact block interval, then fetch transaction + receipt and run `classify_evm_receipt()` against a regression fixture.
- Corroboration: Robinscan `GET /api/addresses/{wallet}/txs?page=N&pageSize=50`, then `GET /api/txs/{hash}` for `tokenTransfers`, method, value, and status.
- Robinscan address history is strong for wallet-submitted activity but can omit relayer-submitted transactions where the wallet appears only inside a token-transfer log. Never call it an exhaustive no-event proof by itself.
- Respect the active provider’s `eth_getLogs` range ceiling. If a large back-audit fails, shrink to the scanner’s proven block window and pace requests; do not reinterpret a range rejection as “no logs.”

## Decision

- **Healthy quiet period:** both cursors advance near heads; no failed/dead outbox; latest Discord message matches; receipt audit finds zero classifier-qualified events. Do not restart or modify code.
- **Ingestion outage:** cursor stalls behind head and RPC errors continue. Fix/fail over RPC, then verify two advancing reads.
- **Delivery outage:** qualifying rows exist but outbox/Discord disagree. Diagnose payload/webhook and preserve backlog until a bounded replay is approved.
- **Classifier false negative:** a concrete successful receipt meets intended semantics but `classify_evm_receipt()` returns none. Add that exact receipt as a failing fixture before changing classification.
