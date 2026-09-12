# NFT transfer discovery and preflight

Read-only techniques verified during a Robinhood Chain bulk-transfer preparation in September 2026. No live batch-signing or transfer completion was verified in that work.

## Diagnose endpoints, not just transport success

- Parse API error bodies before treating a missing `nfts` list as an empty wallet. The OpenSea account-NFT endpoint returned `errors: ["Missing an API Key, which is required for this request."]` even though collection metadata was keyless.
- The same account request succeeded with an existing locally stored OpenSea API key passed as `X-API-KEY`. Load the key locally without printing it or including it in logs. Do not assume credentials exist on another host.
- Route: `/api/v2/chain/robinhood/account/{source}/nfts?collection={slug}&limit=50`. Filter every returned NFT against the exact collection contract, not just its name.
- Preserve successful HTTP headers when moving from curl to Python. A `User-Agent: Mozilla/5.0` retry made previously rejected RPC/signature-directory requests succeed. This is a retry technique, not a guarantee of endpoint availability; respect rate limits and avoid high-fanout signature queries.

## Quantity-limited selection versus complete inventory

- When the user permits any N tokens, an indexed page can supply N candidates. Deduplicate IDs in code, verify the exact contract, then verify `ownerOf` on-chain for every candidate. Disclose the actual selection rule, e.g. first indexed page sorted by token ID; do not call these the wallet's globally lowest IDs.
- Save the selected manifest before additional work. Assert the unique selected count equals N. Pagination is required for complete-inventory claims, but not to choose N currently verified tokens when arbitrary selection was authorized.
- For each selected token, simulate or estimate the exact `safeTransferFrom(source, recipient, id)` from the source. Persist token ID, calldata, recipient, contract, chain, and estimate incrementally so an interruption does not lose the verified preparation.
- Read native balance and gas quote, and calculate aggregate costs with tools. Label the sum of individual estimates as the individual-transaction route—not a batch estimate.

## Evidence boundary

Fifty successful individual transfer simulations prove those individual calls were executable in the simulated state. They do not prove a helper's operator authorization, wallet batch-call support, atomic batch execution, sufficient total funds, final signatures, or completed transfers. Final completion still requires receipts and recipient ownership checks for every approved token.
