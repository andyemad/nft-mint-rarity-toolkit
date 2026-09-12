# Read-only wallet and allowlist review

Use this procedure for no-key Ethereum wallet reviews tied to NFT mints or project allowlists.

## Evidence hierarchy

1. Query `eth_getBalance`, `eth_getTransactionCount`, and `eth_blockNumber` through two independent public RPCs. Agreement grounds the live native balance and nonce.
2. Fetch the explorer address page for account age, latest/first outgoing activity, total transactions, funding labels, token inventory, NFT inventory, and multichain portfolio. Explorer USD values are estimates at the displayed price and timestamp.
3. Treat unsolicited ERC-20 balances and unnamed NFTs as spam/dust unless a reputable market source assigns value. A large token count is not a large portfolio.
4. Compare native balance against the stated mint price and calculate the shortfall before gas. Never imply that holding exactly the mint price is sufficient.
5. For allowlists, retain the exact original submission evidence (`HTTP status`, response body, timestamp/address). A response such as `{"ok":true,"already":false}` proves registration at that moment only.
6. Re-check present eligibility using, in order: live project lookup API; deployed mint contract allowlist/Merkle proof endpoint; official mint UI read path. Historical receipts, reminders, memory, and prior chat are not current proof.
7. If the project API is unavailable, report: “previous registration verified; current membership could not be confirmed.” Do not translate downtime into either “still whitelisted” or “removed.”

## Useful explorer-page extraction

Etherscan’s address HTML can expose useful read-only data without an API key:

- Overview: native balance and displayed USD value.
- More Info: latest/first sent transaction and original funder label.
- Main transaction table: latest 25 transactions with direction, counterparty, method, value, and timestamp.
- Token dropdown: valued ERC-20 holdings versus zero-value/spam holdings.
- Asset/multichain table: chain, token, amount, and estimated value.
- NFT holdings: collection names/counts; do not assign value unless independently priced.

Parse semantic table rows rather than relying on brittle line numbers. Cross-check the native balance against RPC before reporting.

## Security framing

- Absence of recent outgoing transactions supports “no recent outgoing activity visible,” not “wallet is secure.”
- Old approvals may still be live; do not claim approval safety without reading current allowance/operator state.
- Never advise using an unofficial mint link when the project’s official domain is unavailable.
- Keep read-only review separate from signing, revoking, transferring, or funding actions; those require explicit approval and a verified target.
