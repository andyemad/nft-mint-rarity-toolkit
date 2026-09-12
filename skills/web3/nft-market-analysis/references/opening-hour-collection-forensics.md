# Opening-hour NFT collection forensics

Use this reference when secondary trading begins while claims/mints are still active and marketplace state is changing minute by minute.

## Identity collision check

Do not trust a project-name search or the first matching marketplace slug. Projects can have old, disabled, migrated, or same-name collections.

1. Read the official mint/site configuration and its marketplace link.
2. Resolve the marketplace collection metadata to chain + contract.
3. Confirm the mint contract, marketplace contract, official URL, and verified explorer source all agree.
4. Explicitly reject any legacy/same-name collection discovered during the check.

For Next.js mint sites, contract and marketplace constants may be present in current client chunks even when absent from server-rendered HTML. Treat those constants as discovery clues, then verify them independently on the marketplace and explorer.

## Marketplace order normalization

OpenSea collection endpoints have two important launch-market traps:

- `ACTIVE` listings can already be non-executable because the NFT transferred away while marketplace indexing lagged.
- Collection-offer endpoints can mix collection criteria offers, token-specific offers, and multi-quantity offers.

### Listings

- Paginate `/listings/collection/{slug}/all`.
- Deduplicate by token ID, retaining the lowest ask.
- For the lower book, verify `ownerOf(tokenId) == protocol_data.parameters.offerer`.
  - **Address-width trap:** the `ownerOf` eth_call result is **66 chars** (`0x` + 64 hex, 24 leading zero-byte padding) while `offerer` is **42 chars** (`0x` + 40 hex). Compare `owner[-40:].lower() == offerer[-40:].lower()` — NEVER the full strings. The full-string compare always fails and makes the ENTIRE lower book look stale (caught 2026-08-31 on Argonauts: all 50 cheapest listings flagged "STALE" as a false negative; fixing the comparison to `[-40:]` re-validated 57/60 as VALID). Labeling everything stale is the wrong conclusion — verify the address widths before reporting a dead floor.
- The first seller-owned order is the validated floor.
- Remove stale-owner orders from depth counts.
- If owner checks are rate-limited, report exact depth only through the last completely checked price band. Label all higher depth as raw marketplace book, not executable depth.

### Offers

- Paginate `/offers/collection/{slug}/all`.
- For a true collection offer, require `asset.identifier is null` (or equivalent collection criteria), rather than mixing token offers into the collection bid.
- Multi-quantity offers expose total WETH in `price.value`. Compute unit bid as:

```text
unit_bid = price.value / 10**price.decimals / nft_consideration.startAmount
```

Do not divide by `remaining_quantity`; partially filled orders retain original total consideration and original NFT amount in protocol data.
- Deduplicate each maker to its highest active unit bid before describing bid depth.

## Supply-in-motion snapshot

When claims remain open, one supply read is not enough.

- Read `totalSupply`, allocation constants, claimed counters, claim status, pause status, reveal state, and metadata-freeze state directly from the contract.
- Record supply at the beginning and end of analysis.
- State both values if supply changed materially.
- Compute unclaimed allocated overhang from contract constants/counters, not from marketplace supply alone.
- Do not extrapolate a short claim rate into a confident completion ETA.

## Participation and tape

For opening-hour markets, compare sequential 30-minute bins rather than pretending 6h/24h windows have mature history. Report:

- median, p10/p25/p75, count, volume;
- buyers, sellers, top-five concentration;
- multi-item transaction share;
- fast buy→resell sequences;
- repeated buyer/seller pairs and direct self-sales.

High bundle share and rapid flips indicate speculative churn, not automatically wash trading.

## Decision framing

A tight bid/ask spread and rising median prove real immediate demand, but do not erase:

- low winner/mint cost basis;
- still-unclaimed allocated supply;
- unrevealed metadata;
- team/reserve concentration;
- resale fee hurdle.

Use a validated floor, verified unit collection bid, fee-adjusted break-even, and explicit claim-overhang conditions before recommending a market buy or breakout entry.

## Archive output pattern

When the user requests an Argonauts-style `/chat/` presentation, produce a fixed transcript archive rather than an editorial dashboard:

- line numbers;
- exact copy button;
- raw `.txt` download;
- historical snapshot timestamp;
- clear “not live” warning;
- source list;
- desktop and 390px mobile QA.

Keep source/calculated/interpreted values distinct, and never expose local paths, API keys, wallet secrets, session metadata, or private chat identifiers.
