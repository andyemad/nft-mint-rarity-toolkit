# Shared-contract collection resolution

## Verified failure mode (2026-09-02)

the wallet watcher reported that `anonymoux` bought five NFTs and linked the OpenSea
collection `marfamesh-by-harvey-rayner`.

- Transaction: `0x084864cf63a1da316161d78c436aff2f4bb0ea6b5002f29d048c45a14bb3c39f`
- Watched buyer: `0xbec69dfce4c1fa8b7843fee1ca85788d84a86b06`
- NFT contract: `0x942bc2d3e7a589fe5bd4a5c6ef9727dfd82f5c8a`
- Marketplace: Seaport 1.6 at `0x0000000000000068f116a894984e2db1123eb395`
- Call selector: `0x87201b41` (`fulfillAvailableAdvancedOrders`)
- Receipt status: success
- Settlement: `41999999000000000` wei
- Purchased token IDs: `27131`, `14009`, `18657`, `7405`, `25445`

The purchase classification and total were correct. The collection link was
wrong because the Art Blocks contract hosts multiple projects. OpenSea account
sale events for the exact transaction resolved all five tokens to
`friendship-bracelets-by-alexis-andre`, each at approximately `0.0084 ETH`.

## Diagnostic checklist

1. Locate the delivered alert in `entity_alerts` and extract `tx_hashes`, asset
   contract, watched wallet, quantity, and total.
2. Fetch `eth_getTransactionByHash` and `eth_getTransactionReceipt` from a live
   Ethereum RPC.
3. Verify receipt success, transaction sender/value/marketplace target, and one
   ERC-721 `Transfer` into the watched wallet per reported token.
4. Query OpenSea `GET /api/v2/events/accounts/{wallet}?event_type=sale&limit=50`.
5. Filter events by exact transaction hash.
6. Compare every event's `nft.identifier`, `nft.contract`, and
   `nft.collection` against the receipt transfers.
7. Treat `(chain, contract, token_id)` as the collection-resolution key. Do not
   cache a single slug for a shared contract unless project homogeneity is
   independently proven.

## Implementation and test requirement

Add the real transaction as a regression fixture. The failing assertion should
show that contract-only resolution chooses the wrong slug; the passing assertion
should require `friendship-bracelets-by-alexis-andre` for all five identifiers.
Also test a same-transaction sweep across two projects on one shared contract:
the formatter must not emit one misleading collection link.
