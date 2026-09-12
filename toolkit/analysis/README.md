# Analysis

Answer "what really happened here" from on-chain data, with no API keys.

| File | Question it answers |
|---|---|
| `collection_volume.py` | All-time secondary volume for a collection, from public RPC logs. |
| `minter_legitimacy.py` | Mint versus secondary classification, recipient and submitter concentration, payment mix by real `tx.value`, and wash-ring tells. |
| `sweep_scope.py` | Zero-spend scoping pass over a collection's listings. |

```bash
python3 collection_volume.py <contract> [blocks_back] [rpc_url]
python3 minter_legitimacy.py <contract> <deploy_block>
python3 sweep_scope.py <opensea_slug> [--usd <eth_price>]
```

`collection_volume.py` and `minter_legitimacy.py` scan `eth_getLogs` from deploy
to head. Run them in the background for wide ranges, and expect 429s from any
public RPC on a large span.

## Sale heuristic (and its limits)

A secondary `Transfer` (`from != 0x0`, `to != 0x0`) inside a transaction carrying
native value counts as a sale, and `price = tx.value`. This is deliberately
simple and it is honest for native-ETH sales. It **misses**:

- WETH-denominated sales (no native value on the tx)
- protocol-mediated purchases where the wallet only receives a residual or a
  refund while a semantic event records the full purchase
- bundles and sweeps, where one tx carries many tokens. Collapse them into one purchase, or
  you will invent volume)
- account-abstraction / relay mints whose outer `tx.value` is zero

When a collection's money flow is mediated by a protocol, read the protocol's own
event before valuing anything from raw transfers.

## Wash-ring and bot tells

- one submitter address relaying mints for many recipients
- recipients concentrated in a handful of wallets, with the same cap fingerprint
- free or near-free mints dominating "volume"
- round-number self-trades at a fixed price between two wallets that only ever
  trade with each other
- a difficulty/floor that collapses to maximum within hours of opening (bot farms)

## Rules of evidence

- **Label provenance.** Separate what you *read*, what you *computed*, and what
  you *inferred*. "Contract says X", "I derived Y from logs", "this suggests Z".
- **One source is not corroboration.** Cross-check a number against a second
  source before publishing it. When a first number was wrong, keep the
  correction in the write-up. That is the useful part.
- **Never publish** local paths, keys, session metadata, private chat identifiers
  or third-party wallet labels.
