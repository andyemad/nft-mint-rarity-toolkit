# Intraday NFT trade reconstruction on EVM chains

Use this for a wallet-level review of buys, mints, sales, gas, realized P&L, and open inventory. This was validated on Robinhood Chain with Blockscout v2, Seaport, RelayRouterV3, SeaDrop, and account-abstraction transactions.

## Data sources

Fetch and paginate both datasets independently:

- `GET /api/v2/addresses/{wallet}/transactions`
- `GET /api/v2/addresses/{wallet}/token-transfers?type=ERC-721%2CERC-1155`

Then fetch each relevant hash:

- `GET /api/v2/transactions/{hash}`
- `GET /api/v2/transactions/{hash}/internal-transactions`
- `GET /api/v2/transactions/{hash}/state-changes`

Use the chain's local date boundary requested by the user. State the timezone and cutoff time explicitly.

## Classification

### Buy

The NFT moves from another holder to the wallet. For a direct Seaport purchase initiated by the wallet:

- acquisition payment = outer transaction `value`
- transaction cost = successful transaction gas
- token identity = NFT transfer in the same hash

Relay routers can combine currency conversion, marketplace execution, fees, and refunds. Correlate the NFT transfer with native/ERC-20 flows and the wallet's state change instead of treating every token transfer in the receipt as an NFT.

### Mint

Require NFT transfer from the zero address. Decode the mint call where possible:

- quantity from call input or count of zero-address ERC-721 transfers
- mint payment from transaction value
- basis = mint payment + gas
- per-token basis = total basis / quantity

Keep unsold mints as unrealized inventory. Do not mix them into realized flip P&L.

### Sale

The NFT moves from the wallet to another address. The transaction sender is often the buyer, a relayer, or an account-abstraction bundler—not the seller. Therefore, do not require `transaction.from == wallet` to recognize a sale.

Seller proceeds should come from:

1. internal native transfer to the wallet, or
2. wallet balance increase in `/state-changes`, or
3. canonical ERC-20 transfer to the wallet.

Marketplace payouts are usually net seller proceeds after royalties and protocol fees. Do not subtract those fees again. Seller-side gas is zero when the buyer or relayer submitted the sale transaction; only attribute gas when the wallet actually paid it.

A single marketplace transaction can contain multiple NFT orders. Attribute only the proceeds corresponding to the wallet's token. Do not assign the outer transaction value or every internal payment to one seller.

### Robinhood Chain specifics (WETH settlements + state-changes)

On Robinhood Chain, NFT sales settle in **WETH** (wrapped ETH, contract `0x1111111111111111111111111111111111111111`), not native ETH. Consequences:

- `internal-transactions` shows **zero native ETH** for these sales. Do not read empty internal ETH as "the seller was not paid" — it is a WETH settlement.
- `/transactions/{hash}/state-changes` is the authoritative source: it lists the wallet's native `coin` change (gas) and its `token` (WETH) balance change together, with `balance_before` / `balance_after`. Sum the positive WETH `change` rows for the wallet to get seller proceeds.
- A later `withdraw` (WETH → native ETH, to the WETH proxy) is a wrap-out, not a new trade.

**Address case-sensitivity:** Blockscout returns checksummed addresses (e.g. `0xeE3829…`). Comparing against a lowercase string silently matches nothing (observed: WETH in/out both computed as zero while real transfers existed). Normalize both sides with `.lower()` before any `==` comparison.

**Break-even for paid mints:** before coaching a paid-mint flip, compute break-even as `mintPrice ÷ (1 − royalty% − marketplaceFee%)`. On Robinhood with 10% creator royalty + 1% OpenSea fee that is `÷ 0.89` — a 0.001 ETH mint needs ~0.00113 ETH gross to break even. Selling below that is a loss by construction. This is the single most useful number to surface when a trader "fumbled" a flip by dumping at or below cost.

### Failed order

A reverted purchase creates no position but still costs gas when the wallet submitted it. Include that gas in session-level trading costs and, if analyzing one collection strategy, its collection-level basis.

### Approval

Collection approvals cost gas but do not buy or sell an NFT. Include approval gas in strategy-level costs when it was created for that trading session. Report `setApprovalForAll` separately because it grants broad operator authority; recommend revocation after trading unless continued use is intentional.

## Matching and P&L

Match acquisitions and disposals by `(chain, contract, token_id)`. For each realized token:

- basis = purchase/mint payment + attributable buy gas
- proceeds = net payment received by wallet
- profit = proceeds - basis
- ROI = profit / basis

Allocate one-time collection approval gas across the collection or report it once at collection level. Never charge it once per token.

For an aggregate session:

- include successful buy/mint gas
- include failed-order gas
- include approval gas
- include seller gas only when actually paid by the wallet
- separate realized profit from remaining inventory basis

Use decimal integer arithmetic in base units. Convert to ETH only for presentation.

## Verification safeguards

- Verify transaction status before classifying a fill.
- Confirm every NFT transfer against contract address and token ID.
- Do not confuse ERC-20 entries returned in a mixed receipt with NFT transfers.
- Account-abstraction sales can appear under `handleOps`; follow internal transfers and state changes.
- Router swaps can return dust/refunds to the wallet; do not mistake refunds for sale proceeds.
- Compare token-transfer chronology with transaction chronology and identify every unmatched acquisition or disposal.
- State whether figures include gas, approvals, marketplace deductions, and failed transactions.
- USD conversion is approximate unless historical execution-time prices are sourced. Present native-token P&L as primary.

## Coaching output

Report:

1. What the wallet did, in chronological or collection-level form.
2. Realized P&L with transparent inclusions.
3. Open inventory and its basis.
4. Execution strengths.
5. Specific improvements: stale-order checks, approval revocation, liquidity/position-size limits, and a minimum sample before scaling.

Do not overrate percentage returns on tiny capital. Show both ROI and absolute native/USD profit. A profitable handful of flips is evidence of a good session, not proof of a durable edge.

## Multi-week / cross-chain profitability

For "is this wallet profitable over N weeks", the honest approach is: sum current liquid balances across every active chain, subtract verified bridge/deposit inflows over the window, add back verified withdrawals, then state that a precise figure still requires matching every buy/sell pair and valuing open NFT inventory. Explorer transaction offsets cap how far back the visible window reaches — a high-frequency wallet can burn an `offset=1000` pull in a few days, so visible history may be far shorter than the requested window (e.g. a 2-week request surfaced only ~5 days). Report the direction (net inflows, active sale proceeds on both chains) and flag the precision limit rather than inventing a P&L number.