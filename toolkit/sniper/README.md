# Sniper

Buy from the secondary market programmatically — and diagnose exactly why a fill
fails before spending anything.

## Files

| File | What it does |
|---|---|
| `buy_secondary.py` | OpenSea V2 buy path: locate the listing, fetch `fulfillment_data`, encode, eth_call simulate, then sign and broadcast. Dry-run by default; `--live` spends. |
| `probe_fill.py` | Read-only diagnostic: fetches a live listing's fulfillment data with full HTTP error bodies, encodes it, and eth_call dry-runs it to capture the exact revert reason. |
| `seaport_encode.py` | ABI-encodes an OpenSea `fulfillment_data` transaction object into raw `fulfillAdvancedOrder` calldata. Test harness for encoding bugs. |

```bash
python3 buy_secondary.py <collection_slug>                     # dry-run, no spend
python3 buy_secondary.py <collection_slug> --target-eth 0.001  # only under this price
python3 buy_secondary.py <collection_slug> --live              # spends — approval first
```

## The path

```
events feed  ->  /listings/fulfillment_data  ->  ABI-encode  ->  eth_call  ->  sign  ->  send
   find it         get the calldata              build tx      PROVE IT     EIP-1559   broadcast
```

1. **Find live listings on the events feed**, not the orders endpoints. On
   Robinhood Chain the orders/listings "best" endpoints return 404/empty even
   with a valid key; `/api/v2/events/collection/{slug}?event_type=listing` works.
2. **Fetch fulfillment data** for the specific listing hash and chain.
3. **Encode and simulate.** `eth_call` from the *funded* address. If it reverts,
   read the revert data — an encoding bug, a stale order, a taken order, and a
   wrong-chain order all look identical until you decode.
4. **Only then sign and broadcast**, with the fee fields set from live
   `baseFee`/`maxPriorityFee`, and a hard cap on what you are willing to pay.

## Guardrails that actually held

- **Simulate every single buy before broadcast.** Orders disappear and prices
  move between planning and sending; an `eth_call` gate is what stops a batch of
  49 reverts.
- **Check `isApprovedForAll(owner, Seaport)` (`0xe985e9c5`) before listing
  anything.** Without operator approval, `POST /listings/actions` fails with an
  opaque HTTP 500 for the whole collection.
- **Cap per-buy, per-day and keep a reserve**, as constants in the script
  (`MAX_PER_BUY_ETH`, `DAILY_CAP_ETH`). An uncapped sniper is a liquidation
  mechanism pointed at your own wallet.
- **Deep discounts only.** A sniper that buys at market is just a slow market
  order with extra steps.

## Pitfalls

- **Selector derivation:** use the keccak of the exact `function` signature. The
  `calldata_suffix` field OpenSea returns is not the function selector.
- **Listings on a wrapped/native mix:** on Ethereum mainnet settlement can be
  native ETH *or* WETH; do not assume one.
- **`next` cursors are opaque base64** and must be passed as `&next=` — appending
  them as a standalone URL parameter set silently returns page 1 forever.
- **A revert is not always an error in your code.** A missing operator approval,
  a taken order and a restricted-zone transfer rule (ERC-721-C) all present
  differently on-chain; identify which one you have before rewriting the encoder.
  Some collections (ERC-721-C with a transfer-security registry) reject *all*
  operator/helper/conduit transfers no matter who signs — only an owner-initiated
  transfer can pass, which makes an automated flip impossible by design.
