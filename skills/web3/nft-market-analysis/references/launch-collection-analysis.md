# Launch collection analysis worked example: Argonauts

Use this as a method example, not as timeless market data. All quoted market values were live on 2026-08-27.

## Sources that worked

- OpenSea API v2:
  - `/collections/{slug}`
  - `/collections/{slug}/stats`
  - `/events/collection/{slug}?event_type=sale&limit=100&next=...`
  - `/listings/collection/{slug}/best?limit=100&next=...`
  - `/chain/{chain}/contract/{contract}/nfts/{tokenId}`
- Routescan Etherscan-compatible API (keyless verified source and creation):
  - `https://api.routescan.io/v2/network/mainnet/evm/1/etherscan/api?module=contract&action=getsourcecode&address={contract}`
  - same base with `action=getcontractcreation&contractaddresses={contract}`
- Blockscout v2 holder endpoint:
  - `https://eth.blockscout.com/api/v2/tokens/{contract}/holders`
- Official project pages for terms, allocation snapshot, and mint price.
- Read-only Ethereum RPC for live view calls.

## Market calculations

Pull multiple OpenSea event pages and normalize each sale to ETH using payment quantity/decimals. For rolling windows, calculate count, volume, median, and percentiles. In this example the 24h median was 0.2725 ETH, 2h median 0.1777, 1h median 0.1895, and latest 30m median 0.1945: a crash followed by a bounce.

The key signal came from 30-minute participation:
- Capitulation: 210 sales near a 0.174 median.
- Next interval: 72 sales near 0.188.
- Latest: 29 sales near 0.1945.

Price rose while participation shrank, so the bounce was classified as relief rather than confirmed reversal.

For listings, deduplicate by token ID and retain the cheapest active order. The raw endpoint returned duplicate orders for individual IDs; counting them would have overstated depth. Unique-token depth was 6 asks ≤0.20, 19 ≤0.21, 32 ≤0.22, 76 ≤0.25, and 169 ≤0.30.

## Supply and holder analysis

The official snapshot stated:
- 9,999 artworks.
- 7,208 public-sale pool.
- Remaining IDs allocated to free claims and artist/owner reserves.
- Claims open for one month; unclaimed works stay with the Facktory.

OpenSea showed 9,024 minted, leaving up to 975 unminted (10.8% of then-current supply). Treat zero-basis free claims as overhang even after a public sellout.

Blockscout showed 2,274 holders, an owner ratio near 25% and about 3.97 NFTs per holder. The artist held 413 (4.6%); top five held about 11.5%; top 50 held 2,700 (29.9%). Contract/vault holders must be labeled separately from ordinary wallets.

## Churn versus wash trading

In 2,500 recent sales:
- Zero direct self-sales.
- 1,045 fast round-trip resales under 24h.
- 320 addresses appeared as both buyer and seller.

This supported “heavy speculative churn and bot flipping,” not a definitive wash-trading accusation. Require stronger wallet-linkage or funding evidence before saying wash trading.

## Contract findings

Verified source showed:
- Non-proxy ERC-721, max artwork ID 9,999.
- Public pool and trait chunks freeze after pool setup.
- Fully on-chain tokenURI/SVG rendering.
- Owner can still replace the renderer and site contracts, set sale/claim signers, toggle sale/claims, set price, mark prints claimed, and mint predesignated owner-reserved IDs.

Lesson: describe it as non-upgradeable with frozen trait data, but not fully immutable presentation because `setRenderer(address)` remains owner-controlled.

## Fee correction

A generic 10% royalty + 1% marketplace assumption produced a wrong break-even. Verified source did not implement ERC-2981, and OpenSea collection data reported a 1% required fee. At a 0.197 entry, fee-only break-even was approximately `0.197 / 0.99 = 0.199 ETH`, plus gas—not 0.22+.

Always inspect contract royalty support and live marketplace fee data before calculating break-even.

## Trait/right inspection

The project attached a signed physical print right to each token until the on-chain `Print` attribute becomes `Claimed`. Buying the NFT later does not transfer an already-claimed print. Inspecting the 30 cheapest listings showed all were `Print: Unclaimed`, so the generic floor still included the redemption right.

Lesson: collection floors can split into economically different sub-floors based on redemption status. Sample cheap listings before treating every floor item as equivalent.

## Workflow correction from the user

When asked “is this a buy?” in a fast launch market, analysis-only is insufficient. If the entry is attractive, concurrently choose one exact active listing, run a read-only fulfillment simulation, and prepare the purchase-approval slate. This preserves safety without losing the entry window.

Also state whether the work is a one-time snapshot. A promise to act faster next time must not sound like a watcher was already created.