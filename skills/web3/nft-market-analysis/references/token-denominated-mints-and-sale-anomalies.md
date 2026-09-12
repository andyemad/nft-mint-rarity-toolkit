# Token-Denominated Mints and Sale Anomalies

Use when an NFT mint charges or sinks an ERC-20 instead of a fixed native-token amount, or when the sales tape contains an extreme event.

## Identity matrix

Record separately: NFT contract and chain, payment-token contract, project-site contract, marketplace slug/editor, social handle, and any established same-name projects. A shared name/ticker is not affiliation.

## Reflexive mint economics

Calculate:

1. `spot_mint_cost_usd = token_amount × token_price`
2. `spot_mint_cost_native = spot_mint_cost_usd ÷ native_price`
3. `secondary_break_even = floor ÷ (1 - actual_seller_fee_rate)`
4. unminted overhang as a share of maximum and current supply
5. payment-token sink/burn from NFT mints as a share of token supply
6. current and fully diluted floor capitalization

Inspect direct-pair liquidity and slippage, not only market cap or aggregate routed liquidity. Interpret both directions: payment-token strength raises new-NFT cost; weakness lowers the dilution barrier; mint demand can sink tokens and feed back into price.

## Fee decomposition

For live Seaport asks, sum all native/ERC-20 consideration items for buyer gross. Classify recipients into seller proceeds, platform fee, and creator royalty. Executable order consideration overrides a generic fee assumption or an “optional” royalty label in collection metadata.

## Holder fallback

For moderate sequential supplies:

1. Read live `totalSupply()` or verified minted counter.
2. Batch `ownerOf` across the minted range.
3. Validate every response; retry unknowns singly.
4. Normalize to the final 20 address bytes.
5. Compute top-1/5/10/25/50 and single-token-holder shares.
6. Reconcile with marketplace owners and timestamp both.

Never classify RPC errors as burned/missing tokens.

## Extreme-sale reconciliation

If a raw event is orders of magnitude above the normal tape:

1. Verify transaction, payment token, decimals, buyer, and seller.
2. Check whether marketplace aggregate sales/volume includes it.
3. Check repeated pairs and immediate round trips.
4. Exclude it from floor medians and volume conclusions unless independently validated.
5. Label it an anomaly or wash-risk proxy unless evidence proves wash trading.

Marketplace exclusion from recognized volume is strong reason not to use the event as a price comp, but it does not prove intent.
