# Pre-purchase Buy Dispatch Gate (buying NFTs with user's funds)

Trigger: user points at a collection and says "buy as many as you can" (or otherwise asks
you to spend ETH buying tokens in a collection). This is a real-money, irreversible,
external-consequence action — run this ENTIRE gate before any spend. Verified 2026-08-19
on "Robin Strategy" (robinstr, RH chain).

## 1. Identify the funding wallet AND confirm you hold its signing key
"from my minting wallet" / "the one that ends in 26b" is not enough by itself — resolve it
to a concrete address and confirm the private key is on disk (`~/.hermes/secrets/bot_wallet_key`
etc.) before promising execution.

## 2. Check the wallet's ACTUAL native balance on the target chain FIRST (source of truth)
Never trust the user's belief or "as many as you can" as a cap. Query on-chain:
```
curl -X POST https://rpc.mainnet.chain.robinhood.com -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":["<ADDR>","latest"]}'
```
2026-08-19 result: wallet 0x1111…1111 held only `0x105680575570db` wei = **0.0046 ETH (~$9.70)** on
Robinhood — about 5 floor tokens at 0.0008 floor. The real number is often the binding
constraint and it changes the whole plan. Report it plainly before talking strategy.

## 3. Turn "as many as you can" into a real cap
Unbounded spend is not something to take solo. If the user won't fix a budget, the confirmed
on-chain balance IS the natural ceiling — say so explicitly and get sign-off on that
interpretation.

## 4. Pull live floor / volume / owners (one keyed call)
With an OpenSea key (`X-API-KEY` from `~/.hermes/secrets/opensea_key` or `opensea_api_key`),
the stats endpoint is a single clean read (verified 2026-08-19 on robinstr):
`GET /api/v2/collections/{slug}/stats` → `stats.total.floor_price`,
`stats.total.floor_price_symbol`, `stats.total.sales`, `stats.total.num_owners`.
Without a key it returns 401; use the collection page `<title>` + GraphQL hydration instead.

## 5. Enumerate ACTUAL sellable listings before promising a count
Live sell orders for an RH-chain collection come from the **events feed**
(`/api/v2/events/collection/{slug}?...&event_type=listing`) — see
`opensea-live-listing-monitoring.md`. The `orders/.../sell/best` and
`listings/collection/{slug}/best` endpoints are NOT a reliable count for RH-chain
collections: 2026-08-19 they returned 404 / empty / `{"errors":[...]}` even keyed, for a
collection that clearly had 776 sales. If you cannot enumerate live orders, do NOT claim or
execute "buy as many" blind — that is the gap you fix via the events feed, not a reason to
guess a spend level.

## 6. Mandatory safe-test fill before any batch
RH-chain Seaport fill has a known revert history (BUNKER project: 49/49 `execution reverted`).
Money leaves only after ONE clean eth_call-previewed fill succeeds. Reuse the discipline in
`opensea-v2-orderbook-buy-relist.md`.

## 7. Approval gate
Buying is an external financial consequence: present one concrete slate (funding wallet,
hard cap, per-token max, buy strategy) and get approval before spending. A bare "buy as many
as you can" is instruction, not a budget or an approval of a specific amount.
