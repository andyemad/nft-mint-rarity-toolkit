# Seaport Buy Path on Robinhood Chain — verified working primitive

Status as of 2026-08-24: fulfillment encoding VERIFIED on a live the test collection order —
`eth_call` dry-run of `fulfillAdvancedOrder` returned `0x1` (would fill cleanly,
no spend) on token #1081 @ 0.0135 ETH. This upgrades the earlier THE POOL
`eth_estimateGas` evidence (08-22) to a full zero-spend simulation on a second,
different collection, and proves the **advanced-order path specifically** works on
RH (not just basic orders). Real broadcast still gated behind a clean live fill +
the user approval before any permanent auto-buy arms.

## The big post-mortem correction

the sniper project's buy path reverted 49/49 and the standing theory was "hand-rolled Seaport
encoding is broken." WRONG. This session re-tested the same encoder against a fresh
live order: it simulates clean. The 49/49 failures were order-state (orders already
filled/cancelled/dead), not encoding. Lesson: before rewriting a "broken" encoder,
simulate against an order you just fetched seconds ago.

## Speed note for the reveal snipe (2026-08-24)

- Ranking source that beats on-chain+IPFS: OpenSea paged list
  `GET /chain/<c>/contract/<ca>/nfts?limit=200` + `next`. limit=200 yields 0.2s/page
  → ~25 pages for 5000 tokens ≈ 5s total. (The SKILL body records limit=50 at
  3.5s/600; 200 is meaningfully faster for a reveal window.)
- A live, fresh order is the only reliable simulation input: re-pull
  `fulfillment_data` immediately before each fill so the order is still valid.
- Full auto-buy daemon reference: `~/Projects/sniper/clay_sniper.py`
  (guarded: eth_call dry-run before every broadcast, hard caps 3 buys /
  0.010/buy / 0.030/day / 0.050 reserve).

## Working pipeline (per buy)

1. **Get fulfillment calldata** — POST `/listings/fulfillment_data` (OpenSea API key,
   `~/.hermes/secrets/opensea_key`) with `{listing: {hash, chain: "robinhood",
   protocol_address}, fulfiller: {address}}`. Returns tx template (`to`, `value`,
   `input_data`, `function` signature string).
2. **Encode calldata** from `input_data`. Two shapes:
   - `input_data.parameters` = basic order → encode `fulfillBasicOrder_efficient_6GL6yc`
     with the BASIC tuple type (see buy.py). NOTE: this function's selector is literally
     `0x00000000` (known Seaport Yul quirk) — do not "fix" it.
   - `input_data.advancedOrder` = advanced path → fulfillAdvancedOrder with
     `(AdvancedOrder, CriteriaResolver[], bytes32, address)` types.
   Selector = keccak of the EXACT function-signature string OpenSea returns in `tx.function`
   (the `calldata_suffix` field is misleading; bunker proved this 6/6 via eth_call).
3. **Simulate FIRST, always** — `eth_estimateGas` with from=buyer, to/value/data. A reverting
   buy must die here, never on broadcast. Sanity-check the RPC isn't rubber-stamping by
   occasionally sending garbage calldata (it correctly returns "execution reverted").
4. **Guards** (enforced in code regardless of caller): per-buy ETH cap, daily cap persisted
   to a state file, hard absolute cap.
5. **Sign + broadcast** — eth_account sign_transaction; EIP-55 checksummed `to` or signing
   silently fails; gas = estimate + 50000 headroom; fresh nonce; eth_sendRawTransaction.

## Code locations

- Reusable guarded module: `~/Projects/mint-control-room/scripts/buy.py`
  CLI: `buy.py simulate <order_hash>` / `buy.py buy <order_hash> --max 0.0015`.
- Bunker origin (same encoder): `~/Projects/sniper/autoflip.py` lines ~150-230.
- Run with: `PYTHONPATH= ~/Projects/sniper/.venv/bin/python3 …`
  (empty PYTHONPATH is required — see SKILL.md gotcha).

## Key facts

- RH Seaport protocol: `0x0000000000000068f116a894984e2db1123eb395` (Seaport 1.6).
- Listings discovery: GET `/api/v2/listings/collection/<slug>/best` (API key) returns up
  to 48 best listings incl. full protocol_data.parameters. The
  `/api/v2/orders/{chain}/seaport/listings` endpoint now returns 405 Method Not Allowed —
  don't use it.
- Listing "price" trap: last consideration item is the FEE, not total. Buyer pays the SUM
  of all consideration amounts; fulfillment_data's `tx.value` already equals that sum.
- seaport-js (`@opensea/seaport-js`) installs fine and its bundled ABI works for
  getOrderStatus etc., but has no orders() view — the API-key path above is simpler.
- Bot wallet 0x1111…1111 funded (~0.0325 ETH at writing); key `~/.hermes/secrets/bot_wallet_key`.

## Buying policy (never violate)

Buying is ALWAYS a separate explicit the user approval, even inside a snipe workflow he asked
for. Auto-buy mode requires: UI-authorized bounds (price cap/token, rank cutoff, daily cap)
AND one clean confirmed test fill first.
