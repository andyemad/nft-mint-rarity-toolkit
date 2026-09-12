# Robinhood Chain: sale settlement quirks and secondary-market assessment

Supplements `intraday-nft-trade-reconstruction.md` and `nft-mint-market-analysis.md` with
Robinhood-Chain-specific findings from a live intraday flip/session review (2026-08-13).

## Sale settlement quirks (Blockscout v2)

- **Sales often settle in WETH, not native ETH.** Canonical WETH on Robinhood Chain:
  `0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73` (18 decimals). A sale's native `value`
  field is frequently zero; the seller is paid via an ERC-20 WETH transfer in the receipt.
  Always scan the receipt's ERC-20 transfers for WETH before concluding "no proceeds".
- **Lowercase every address before comparing.** Blockscout returns checksummed (mixed-case)
  hashes. A `from`/`to` hash comparison against the wallet silently fails and zeroes
  IN/OUT totals unless both sides are `.lower()`-ed (bit once: WETH IN/OUT computed as 0
  until the case fix).
- **`internal-transactions` returns empty or all-zero for Seaport `matchAdvancedOrders` /
  `fulfillAvailableAdvancedOrders`.** When it does, read the wallet's native balance delta
  from `/transactions/{hash}/state-changes` (`type: "coin"`, `change`) instead. That is the
  reliable seller-proceeds source for Seaport fills.
- **Zero-address NFT transfers in a sweep are a display artifact, not a burn.** In a
  `fulfillAvailableAdvancedOrders` sweep, some of a seller's tokens show `to == 0x0000`
  while others show the buyer. The seller is still paid. Confirm by dividing the wallet's
  state-change proceeds by its token count in the receipt — a clean per-unit figure means
  the "burned" tokens actually sold through the conduit.
- **Seaport method semantics:** `matchAdvancedOrders` = the wallet matched an offer (sale);
  `fulfillAdvancedOrder` = one listing filled; `fulfillAvailableAdvancedOrders` = a buyer
  swept multiple listings (possibly across sellers). The transaction `from` is usually the
  buyer or a relayer, so seller-side gas is zero — do not attribute it to the wallet.

## Breakeven math for paid mints

Seller nets `gross × (1 - royalty - fee)`. With a 10% creator royalty and a 1% marketplace
fee, breakeven gross = mint / 0.89 ≈ 1.124 × mint — roughly a 12% floor move before a flip
makes anything. Compute this before minting, not after: a paid mint sold near cost can be a
guaranteed loss on every unit once royalties + fees are deducted.

## Assessing a specific collection's recent sales (OpenSea activity page)

Parse the embedded GraphQL hydration (no key):

- Locate `"collectionActivity":{"items":` and `json.JSONDecoder().raw_decode` from the opening `{`.
- Each item: `eventTime`, `__typename` (Sale), `type` ("SALE"), `price.token.unit` (native),
  `from.address`, `to.address`, `transactionHash`, `quantity`.
- The activity page shows ~32 events; paginate `?page=2` etc., then dedupe by item `id`.

Compute concentration — sales count alone exaggerates demand when buyers sweep:

- unique buyers vs sellers vs transactions vs total sales
- top-5 buyer and top-5 seller share of total sales
- items-per-transaction (bundle sweeps)
- price distribution (median vs floor vs min/max)

Manufactured-market / coordinated-momentum red flags (any cluster = speculative, not durable
demand):

- nearly all lifetime volume within ~1 hour (1h volume ≈ 24h volume)
- top-5 buyers >60% of sampled sales and/or top-5 sellers >60%
- synchronized bundle sweeps at near-identical prices
- low owner count relative to supply (e.g. <10%)
- unverified collection, centralized metadata (`metadataStorageLabel: CENTRALIZED`),
  contradictory supply descriptions
- floor 100×+ above mint with no established secondary history

Credibility-positive signals (still not a buy call):

- creator X account age + follower count + verification + "OpenSea verified creator since YYYY"
- prior collections with live secondary volume
- decentralized metadata; ownership distribution ~40%+ and listed fraction <15%

Framing: distinguish momentum liquidity (fast, concentrated, only present during the surge)
from durable collector demand. A floor rising during sweeps is not demand; the floor holding
AFTER sweep buyers stop is.

Creator-profile check (no key): `https://api.fxtwitter.com/{handle}` returns account age,
followers, verification, and bio. Collection stats come from the `"stats":` hydration fragment
(`ownerCount`, `listedItemCount`, oneDay/sevenDay/thirtyDay volume, `floorPrice`).

## Coaching pattern (this user)

For an experienced trader flipping tiny-capital Robinhood mints, the recurring failure is
exiting winners too early — dumping free/cheap mints at or below cost right before the floor
runs. Coach: on a zero-cost-basis mint, keep one or two runners; on a paid mint, do the
royalty+fee breakeven math first. Judge sessions by net dollars vs time/risk (Buford cost of
living), not by percentage return on ~$10 of capital.
