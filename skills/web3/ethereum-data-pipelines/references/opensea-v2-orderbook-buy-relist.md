# OpenSea V2 Orderbook — Fully-Automated Buy + Relist (Robinhood/EVM chains)

Validated 2026-08-18 building a buy-misprice → relist-flip bot for a Robinhood-chain
collection (BUNKER Genesis Artifacts). All endpoints require an API key (X-API-KEY header;
keyless coverage on RH is name/image only). This is the READ path for orders, the BUY path,
and the RELIST path — distinct from the events-feed monitor.

## API key
Store at `~/.hermes/secrets/opensea_key`, send as `X-API-KEY` on every call. OpenSea V2
orderbook + fulfillment endpoints return `401 Missing an API Key` without it.

## Endpoints (all verified live)
- `GET /api/v2/listings/collection/{slug}/best?limit=50` — live orders incl. FULL signed order
  (each item has `order_hash`, `protocol_data.parameters`, `protocol_address`, `price.current.value`,
  `asset.identifier`, `asset.traits[]`, `status`). Sort by price to find cheapest live.
- `GET /api/v2/orders/chain/{chain}/protocol/{protocol_address}/{order_hash}` — single order, full data.
- `GET /api/v2/events/collection/{slug}?chain=...&event_type=listing&limit=50` — listing events;
  has `order_hash` + `asset.traits` (rarity filter here). **Paginate with the `next` cursor — the
  `after` param returns HTTP 400.** Sweep several pages so cheap listings can't age out of the
  newest-50 window.
- `POST /api/v2/listings/fulfillment_data` — builds the BUY transaction. Body:
  `{"listing": {"hash": <order_hash>, "chain": "robinhood", "protocol_address": <protocol_address>},
    "fulfiller": {"address": <wallet>}}`. Response `fulfillment_data.transaction` has
  `function` (exact ABI signature string), `to`, `value`/`value_hex`, `input_data` (STRUCTURED
  Seaport order — NOT raw calldata), `calldata_suffix`.
- `POST /api/v2/listings/actions` — builds a RELIST order. Body:
  `{"address": <seller>, "items": [{"chain","contract","token_id","quantity":1,
   "price":{"amount":"<eth>","currency":"0x0000...0000"}}]}`. Response `steps[0].createListingsAction`
  has `signatureRequest.message` = EIP-712 JSON (`types`,`primaryType`="OrderComponents","domain",`message`).
- `POST /api/v2/orders/{chain}/seaport/listings` — submit a signed relist. Body:
  `{"parameters": <message.message>, "protocol_address": <domain.verifyingContract>, "signature": <hex>}`.

## BUY path (Seaport fulfillAdvancedOrder) — CRITICAL PITFALLS
1. **The correct function selector is keccak256 of the EXACT `function` string OpenSea returns**,
   e.g. `fulfillAdvancedOrder(((address,address,...),uint120,uint120,bytes,bytes),(uint256,uint8,uint256,uint256,bytes32[])[],bytes32,address)`
   → `0xe7acab24`. **Do NOT use `calldata_suffix` (0xcdb44011) as the selector — it is misleading
   and reverts (0/49 fills).** The computed-sig selector gave 6/6 eth_call SUCCESS.
2. `input_data` must be ABI-encoded with the arg types. Define types:
   - `ORDER_PARAMS = "(address,address,(uint8,address,uint256,uint256,uint256)[],(uint8,address,uint256,uint256,uint256,address)[],uint8,uint256,uint256,bytes32,uint256,bytes32,uint256)"`
   - `ADV_ORDER = f"({ORDER_PARAMS},uint120,uint120,bytes,bytes)"`
   - `CRITERIA_RESOLVER = "(uint256,uint8,uint256,uint256,bytes32[])"`
   - `FUNC_TYPES = [ADV_ORDER, f"{CRITERIA_RESOLVER}[]", "bytes32", "address"]`
   - advancedOrder = [order_params(offerer,zone,offer[],consideration[],orderType,startTime,endTime,
     zoneHash,salt,conduitKey,totalOriginalConsiderationItems), numerator, denominator,
     bytes(signature), bytes(extraData)]
   - criteriaResolvers, conduitKey, recipient from `input_data`.
   - calldata = selector + ABI-encode(FUNC_TYPES, args).
3. **Verify BEFORE broadcasting (mandatory safe test, no spend):** construct the tx
   `{from: wallet, to, data, value: value_hex, nonce, gasPrice}` and call `eth_call` on the RPC.
   A `result` key (even all-zero) = it would fill. `execution reverted` = wrong encoding or
   order already taken. Fix the encoding before any live eth_sendRawTransaction.
4. Broadcast: sign with `eth_account.Account.from_key(priv).sign_transaction(txobj)` then
   `eth_sendRawTransaction`. RH RPC needs `User-Agent: Mozilla/5.0` (urllib 403s without it).
   **TWO broadcast gotchas that silently kill EVERY buy if missed (2026-08-18):**
   - **GOTCHA A — `to` must be EIP-55 checksummed.** `eth_account.sign_transaction` refuses
     to sign a tx whose `to` is not a valid checksummed address. The Seaport address
     `0x0000000000000068f116a894984e2db1123eb395` is NOT checksummed →
     `eth_utils.to_checksum_address(to)` it first. Without this, every buy dies with
     `TypeError: Transaction had invalid fields: {'to': ...}` BEFORE broadcast — it looks
     like "buy failed" on the daemon log with no RPC error. Root cause of 11/11 silent failures.
   - **GOTCHA B — raw tx needs a `0x` prefix.** `signed.raw_transaction.hex()` returns hex with
     NO `0x`; `eth_sendRawTransaction` rejects it
     ("cannot unmarshal hex string without 0x prefix into Go value of type hexutil.Bytes").
     Prepend `"0x"` before sending.
5. **RH chain speed reality:** deep-discount orders get snapped by other bots within seconds.
   A 2-min poll loses the screamers; a tight 5–10s loop wins far more. Set expectations honestly.

### Seaport 1.6 basic orders + eth_call simulation (validated 2026-08-31, ETH-mainnet Argonauts)
- **`fulfillment_data` must be `POST`.** `GET /api/v2/listings/fulfillment_data?listing_hash=...` returns 405. POST body:
  `{"listing":{"hash":<order_hash>,"chain":<chain>,"protocol_address":<protocol_address>},"fulfiller":{"address":<wallet>}}`. Response `fulfillment_data.transaction` carries `function`, `to`, `value`/`value_hex`, `input_data.parameters`, `calldata_suffix`.
- **Seaport 1.6 may return a *basic* order** — `function: "fulfillBasicOrder_efficient_6GL6yc(…)"`. Its keccak selector genuinely starts `0x00000000` (verified live; a real if unusual selector). Do NOT "correct" a leading-zero selector to the canonical `fulfillBasicOrder` (`0xfb0f3ee1`) — use the exact string OpenSea returns, exactly as the `fulfillAdvancedOrder` rule above.
- **`eth_call` fill-simulation needs a funded `from`.** A zero-balance/fake `from` reverts BEFORE the calldata runs with `-32000 insufficient funds for gas * price + value: address … have 0 want <value>` — even though `eth_call` is read-only and moves nothing. Use a genuinely funded address as the simulated `from` (e.g. a whale or the collection owner) to pass the node's funding check and actually exercise the Seaport logic. Sanity-check the keccak method against a known selector (`transfer(address,uint256)` → `a9059cbb`) before trusting a computed selector.
- **Ultra-fast churn: a freshly-fetched floor order may already be swept** by the time you simulate — an `execution reverted` on a just-fetched floor listing is often "already taken," not a wrong encoding (here the quote floor moved 0.176 → 0.195 within ~40 min). Re-fetch and re-pin the floor immediately before simulating/buying; never conclude a broken buy path from one revert in a hot collection.

## RELIST path (verified: signature recovers to wallet)
1. `POST /listings/actions` → `signatureRequest.message` (EIP-712 JSON string).
2. Sign with `encode_typed_data(full_message=json.loads(msg))` then
   `Account.from_key(priv).sign_message(enc)`.
3. Submit `{"parameters": msg["message"], "protocol_address": msg["domain"]["verifyingContract"],
   "signature": sig.hex()}` to `POST /orders/{chain}/seaport/listings`.
4. Verify by recovering: `Account.recover_message(enc, signature)` == wallet.

## Environment
- Robinhood chain: chainId 4663, gas ~0.02 gwei, Seaport 0x0000000000000068f116a894984e2db1123eb395.
- Use `eth-account` + `eth-abi` + `pycryptodome` (keccak) in a venv (`uv venv`, `uv pip install ...`).
- `opensea-py` pip package (0.0.2) is a stub with no usable module — don't rely on it.

## User expectations (Emad)
Deep-discount-ONLY snipes (well under floor, e.g. 0.001 vs 0.0038 Epic floor); NO at-floor noise.
Alert threshold must be a real misprice, not the floor itself. Strict per-buy + daily caps
(0.0015/0.02). Mandatory non-broadcast safe test shown before any live money. He notices both
spam (too many useless alerts) and silent-miss (cheap one not flagged) — fix both.

## Detection strategy — pitfalls that cost this session (2026-08-18)
- **The event feed is LAGGED history, not a live orderbook.** `event_type=listing` returns
  orders that faster bots already filled seconds earlier. A sniper detecting from the event
  feed yields ghost candidates that ALL fail with "Order not valid" at fulfillment. To win
  races, watch the LIVE orderbook (`/best`) and react to fresh entries; the event feed is
  only useful for monitoring/alerting, not as a buy source.
- **`/best` and `/all` listing assets carry NO traits** — you cannot read Rarity from the
  orderbook endpoints (every item shows `rarity '?'`). To filter by trait (e.g. only buy Epic)
  you must join token IDs back to per-token metadata
  (`chain/{chain}/contract/{addr}/nfts/{id}`) or pull traits from the event feed. A live
  sniper must resolve traits at race speed — prefetch/pin hot-token metadata or accept it can't
  filter by trait live.
- **Never verify the buy path by grabbing "cheapest active order".** That bought a NON-RARE
  floor token with the user's money. The safe-test/verification target must carry the SAME
  trait filter the bot enforces (verify on an Epic if the bot only buys Epics).
- **Never let a dry-run pollute the production state file.** Running `--dry-run` or `--simulate`
  against the same `state.json` the live daemon reads marks snipes "seen" without buying them
  → the live loop then silently SKIPS real Epics forever (logged `candidates=0` while snipes
  sat unblocked). Use a separate test-state file/flag for any non-live run.
- **eth_call dry-run SUCCESS is necessary but NOT sufficient** — it proves calldata encodes
  correctly, but real broadcast still failed 3 separate times this session (checksum `to`,
  missing `0x` prefix, then a revert). Proof-of-life = a real `eth_sendRawTransaction` that
  returns a txid AND `eth_getTransactionReceipt` status=1 with the NFT transferred. Only then
  arm an auto-buyer that spends the user's money.
- **Kill discipline with a supervisor:** a supervisor cron that restarts a "fast loop" shell
  wrapper must be PAUSED (not just the daemon killed) to fully stop a buying bot — otherwise it
  resurrects. When the user says stop, pause every cron that touches the bot AND kill the daemon.
