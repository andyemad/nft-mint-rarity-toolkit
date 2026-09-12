# Stablecoin and threshold accounting notes

Use this when reconstructing outbound USDC/USDT or when a user asks to count every round-number transfer regardless of destination.

## Canonical Ethereum contracts

- USDC: `0xA0b86991c6218b36c1d19d4a2e9Eb0cE3606eB48`, 6 decimals.
- USDT: `0xdAC17F958D2ee523a2206206994597C13D831ec7`, 6 decimals.

Never trust `tokenSymbol` alone. A wallet-history review found a second token named "Tether USD" with symbol `USDT` and 6 decimals at a noncanonical contract; counting symbols produced a false extra $500. Contract-address filtering reduced verified USDT from $1,000 to $500.

## Two distinct user questions

1. **How much was off-ramped?** Requires exchange attribution or gateway-routing evidence.
2. **How much was sent out in transfers of at least $X?** Requires exhaustive threshold enumeration, regardless of recipient type.

Do not answer question 2 with question 1's filters. A MetaMask swap-spender transfer is not an off-ramp, but it belongs in gross outbound threshold accounting if it meets the threshold.

## Threshold extraction

For each outgoing canonical token transfer:

```python
amount = Decimal(row["value"]) / (Decimal(10) ** int(row["tokenDecimal"]))
if amount >= threshold:
    keep(row)
```

Produce:

- date/time;
- canonical token;
- decoded amount;
- full destination;
- transaction hash;
- recipient classification;
- transfer count;
- unique destination count;
- totals by destination and token;
- grand total.

When the user gives examples such as "$550, $500, $1,000," interpret the obvious default as `>= $500` unless their wording establishes a finite exact-value set. State that threshold once.

## Routing evidence

- Same-token forwarding shortly after receipt to a label-verified exchange is strong gateway evidence.
- Attribute only the user's first-hop amount; never add the forwarding hop.
- A transfer's round amount alone is not exchange evidence.
- Keep named exchanges, probable unlabeled gateways, swaps/commerce, likely personal wallets, and fake tokens in separate, mutually exclusive buckets.
- If the user excludes an exchange, remove it from both the details and headline total—not merely from the narrative.

## Reporting discipline

Avoid silently changing definitions between turns. Label each figure as one of:

- confirmed exchange deposits;
- probable gateway deposits;
- gross qualifying outbound transfers;
- excluded/noncanonical tokens.

Gross qualifying outflow is not the same as fiat withdrawn.
