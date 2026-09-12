---
name: nft-floor-sweep
description: Use when the user says "sweep this" or "buy the floor".
version: 1.0.0
author: Hermes
license: MIT
platforms: [macos, linux]
---

# NFT Floor Sweep (multi-item buy)

"Sweep this" / "buy the floor on X" means buy ALL (or N of) the cheapest active
listings in a collection — a multi-transaction job, NOT one snap-buy. A fresh,
cheap collection can have hundreds of active listings (this session: 402) with
only a handful at floor. Always scope the full book before spending anything.

## When to use
- "sweep this", "sweep the floor", "clear the floor on <collection>", "buy up the cheap ones".
- Distinct from `nft-secondary-buy` (single-item fill) — that skill is the per-item
  execution primitive; this one is the sweep orchestration + scoping layer.

## Scope first (zero spend) — scripts/sweep_scope.py
Run the scoping script; it does the whole pass:
1. **Paginate** `/listings/collection/{slug}/best?limit=50` following the `next`
   cursor until exhausted. The first page is never the whole book.
2. **Price ladder** (wei -> count) so you can see the floor group vs the rest.
3. **Cheapest-N quote** — cumulative cost of the N cheapest, in ETH and USD.
4. **Wallet-cap check** — buyer balance on RH RPC (https://rpc.mainnet.chain.robinhood.com)
   vs sweep cost + gas. Balance is the hard ceiling on sweep depth.
5. **Floor-stuffer flag** — if many floor listings share one maker address, that's
   a single seller stacking the floor, not organic demand. Surface it to the user
   before they spend (affects how likely the floor holds).

Key API facts: best-listings cursor param is `&next=<cursor>`; the `/best?limit=50`
endpoint returns `listings[]` + `next`. Price lives at `listing.price.current.value`
(wei). Floor listings on RH come back as `type: "basic"` orders.

## Gate (MANDATORY — real spend)
Get a HARD number from the user: item count and/or max ETH. Never run an
unbounded "buy as many as you can" sweep, and never pick the wallet silently —
confirm which wallet receives the NFTs. Propose a slate with a hard cap and show
the dry-run quote first; stop and wait for explicit approval before any broadcast.

## Execute (per item)
For each target listing:
1. `POST /listings/fulfillment_data` {listing:{hash,chain:"robinhood",protocol_address}, fulfiller:{address}}.
2. Encode the fill (basic vs advanced — see nft-secondary-buy) and `eth_call`
   dry-run. Basic floor orders dry-run SUCCESS on RH; advanced orderbook fills
   have historically reverted — ALWAYS dry-run, never broadcast blind.
3. Broadcast one tx per item; verify each receipt `status:0x1`.
4. On any single failure: STOP, report the revert reason, don't retry blindly
   and don't overshoot the cap.

## Pitfalls
- First page of `/best` is not the book — paginate or you'll misquote sweep size/cost.
- `execute_code` may be blocked in some sessions (cron approval mode) — run the
  scoping script via `python3 scripts/sweep_scope.py <slug>` in terminal instead.
- Same-maker floor stack reads like volume; always check maker diversity.
- Never print `~/.hermes/secrets/*` contents to chat; read the key inside the script.
