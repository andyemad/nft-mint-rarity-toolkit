# OpenSea Seaport order normalization

Use this when turning OpenSea V2 order payloads into an executable floor or collection bid.

## Listing gross price

A Seaport listing’s `consideration` can split payment among the seller, marketplace, and creator. The first native/ERC-20 consideration item is commonly the seller’s net proceeds, not the buyer’s gross ask.

For the displayed/executable listing price:

1. Read `protocol_data.parameters.consideration`.
2. Keep payment items (`itemType` 0 for native currency or 1 for ERC-20).
3. Sum every payment item’s `startAmount` (or the correct time-adjusted amount for a dynamic order).
4. Convert by the payment token’s decimals.
5. Do not report the first payment component as the floor; that can understate the ask by marketplace and creator fees.

For a static order:

```python
payments = [c for c in consideration if int(c["itemType"]) in (0, 1)]
gross_wei = sum(int(c["startAmount"]) for c in payments)
```

## Item versus criteria offers

Seaport item types matter:

- `2` / `3`: specific ERC-721 / ERC-1155 item.
- `4` / `5`: ERC-721 / ERC-1155 criteria offer, typically collection- or trait-wide.

Do not classify a collection bid only by a null or zero token identifier. First require criteria item type 4/5, then inspect its criteria/root. Exclude item types 2/3 from collection-floor support even if their price is much higher.

## Multi-quantity collection offers

A payment amount can cover several NFTs. Normalize to per-NFT price using the NFT consideration’s original `startAmount`, not `remaining_quantity`:

```python
quantity = int(nft_consideration["startAmount"])
per_nft = int(payment_offer["startAmount"]) / quantity
```

Example: 2.25 ETH offered for 15 collection NFTs is 0.15 ETH/NFT, not a 2.25 ETH collection bid.

## Owner validation

OpenSea `ACTIVE` is not enough during fast launches. For the cheapest unique asks:

1. Extract token ID and offerer.
2. Call `ownerOf(tokenId)` at current chain tip.
3. Remove any order whose owner differs from its offerer.
4. Continue until the first owner-valid ask is found.
5. Record how many lower asks were rejected and identify the first verified token.

Revalidate immediately before freezing the report because the owner and order book can change within seconds.

## Fast-launch refresh discipline

A full crawl can become stale while the report is being designed. Before publication, refresh at minimum:

- authoritative stats floor;
- first active listing page, using gross consideration sums;
- first active offer page, using criteria item types and per-NFT normalization;
- short sales windows;
- supply/claim counters;
- `ownerOf` for the lowest asks.

If the refreshed regime changes materially, rewrite the report and its scenario probabilities rather than publishing the earlier snapshot. Label the artifact as a fixed timestamp, not live monitoring.
