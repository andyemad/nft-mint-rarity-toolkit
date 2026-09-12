# Protocol-semantic wallet alert valuation

Use this when a wallet tracker reports a token purchase that looks materially smaller than the transaction actually executed.

## Core rule

A transfer **to the wallet** is not always the purchased quantity. Strategy, mining, vault, hedge, and position-controller transactions can buy an asset inside a protocol, retain most of it in a controller, and return only a residual amount to the holder. A wallet-delta classifier can therefore be transport-correct but economically wrong.

Before publishing USD for an unfamiliar protocol-mediated transaction, reconcile four layers:

1. Direct ERC-20 transfers to and from the watched wallet.
2. Swap events and their signed input/output amounts.
3. Protocol semantic events (`RunStarted`, `PositionOpened`, `Deposit`, etc.).
4. Native/WETH payment and market-price evidence.

If a verified semantic event exposes the protocol's full purchased quantity, prefer that field for the alert. Keep the direct wallet transfer as a separate wallet-delta fact.

## Verified Robinhood example: CacheFlow `RunStarted`

A Wallet Radar alert reported Czar bought about `$2.67` of CACHE in transaction:

`0xb409c0dc0dfdece7beb61c3f318ef04498efe49e14d5cbd754737266f705b5b1`

The wallet received only:

- `589206489986897238596` raw CACHE
- `589.206489986897238596 CACHE` at 18 decimals

But the transaction emitted:

```text
RunStarted(
  uint256 indexed runId,
  uint256 indexed tokenId,
  address indexed holder,
  uint256 basisWei,
  uint256 cacheBought,
  uint256 hedgeWei,
  uint64 endsAt
)
```

Topic 0:

`0x645b4f5f88428c5c127b208e436b960a1343baf1fce8732f7268a02b16e6da75`

For that event:

- `holder`: watched wallet `0x1f00…0364` (indexed topic 3)
- `cacheBought`: `63268550935528854354582` raw
- full amount: `63,268.550935528854354582 CACHE`
- wallet-return amount was only 1/107.38 of the purchase

The semantic event—not the final transfer to the wallet—was the correct source for the alert quantity.

## Safe classifier pattern

Use a narrow protocol-aware override:

1. Require the exact verified event signature.
2. Require the expected chain and token contract.
3. Decode and match the indexed holder to the watched wallet.
4. Validate data length before reading words.
5. Decode `cacheBought` from non-indexed data word 1 (byte offset 32).
6. Perform ordinary transfer classification and same-token coalescing first.
7. Override only the matching token-buy event after coalescing.
8. If the event is malformed, belongs to another holder, or lacks a matching token buy, do not override.

Do not globally treat every protocol event field as wallet ownership. Label the semantic quantity as the protocol purchase and retain wallet balance deltas separately when the product exposes detailed activity.

## Regression discipline

Build a fixture from the real ABI layout, not an invented shortened payload. The regression must prove that:

- the old classifier returns the direct wallet residual;
- the fixed classifier returns the semantic full purchase;
- an event for another holder cannot modify the watched wallet's alert;
- malformed/truncated event data cannot create a quantity;
- ordinary swaps without the protocol event remain unchanged.

Then run the focused classifier test, the complete wallet-tracker suite, lint, compilation, and a replay of the actual receipt before activation.

## Data-access fallback

When a direct explorer API request is WAF-blocked, a validated alternative is to scrape the known Blockscout JSON endpoint through Firecrawl with `formats:["rawHtml"]`, `maxAge:0`, and an automatic proxy. The returned `rawHtml` can be the literal JSON body. Parse it as JSON and preserve the endpoint URL as provenance. This is a retrieval fallback, not a reason to weaken receipt validation.
