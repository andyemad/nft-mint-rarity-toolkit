# Ethereum raffle-entry operations

Use this reference when a mint link is actually a refundable-entry raffle rather than a normal immediate ERC-721 mint.

## Early classification and wallet/network check

Before probing stored keys or building calldata, establish all four facts:

1. Destination chain and contract from the site bundle and live API.
2. The wallet/network the user is actually using or just bridged from.
3. The funded destination address on that chain.
4. Whether the quoted ETH is an immediate purchase, a deposit, or a maximum exposure.

A user saying “I’m on Robinhood” may mean the wallet is still connected to Robinhood Chain even when the site requires Ethereum mainnet. Check this before treating a site error as a contract failure. If the user stops or says they will do it manually, halt immediately; do not continue broadcast preparation.

## Recon pattern

1. Fetch the page and its Next.js chunks. Extract the contract, chain, public RPC, ABI and authoritative API endpoints.
2. Prefer the project’s live snapshot endpoint when available, then cross-check on-chain. Capture phase, pause state, exact entry price, close time, total entries, supply, claims state and contract address.
3. Identify the exact payable function. Common raffle shape: `enterRaffle(uint256 quantity)` with `msg.value == entryPrice * quantity`.
4. Distinguish deposit mechanics from final economic cost. Record when losing/unallotted entries become refundable, who must claim, any settlement timeout and refund-expiry window. Never present a project’s refund promise as a Hermes guarantee.
5. Estimate current odds when useful. For `q` entries, `K` allocations and `N` entries after the user joins, the probability of at least one allocation under uniform sampling without replacement is `1 - product((N-K-i)/(N-i), i=0..q-1)`. Label this as a current estimate because later entries dilute it.

## Deterministic preflight

Immediately before approval and again immediately before signing, require:

- chain ID, contract, method, quantity and exact value match;
- live phase, not paused, and before close time;
- funded signer address matches the intended local key;
- `eth_call` succeeds from that address with the exact value/calldata;
- `eth_estimateGas` succeeds;
- balance covers value plus the approved gas ceiling;
- transaction nonce is read from `pending`;
- EIP-1559 fee settings cannot exceed the approved gas-spend ceiling.

Abort on any mismatch. Never silently lower quantity, change contract, overpay, or move to another wallet.

## Approval slate

The slate must name:

- full source wallet and contract;
- chain, function, quantity, exact ETH value;
- hard gas ceiling and maximum total debit;
- irreversible confirmation semantics;
- deposit/refund timing and claim-window caveat;
- current odds or expected allocation when material;
- automatic-abort conditions.

A broad earlier request such as “do it for me” is not the final broadcast approval. Present one exact slate, stop, and consume the approval only after the user’s direct answer.

## Broadcast and verification

- Sign in-process from the approved local key; never print the key or raw signed transaction.
- Broadcast once. Persist the returned transaction hash immediately, without secrets.
- If the receipt is pending, do not resend blindly. Query `eth_getTransactionByHash`, the receipt and current base fee. A same-nonce replacement is only appropriate when still within the explicit slate; otherwise request a new approval.
- Completion requires an authoritative successful receipt plus a contract-level post-state read such as `entriesOf(wallet)` showing the requested quantity.
- Record block number, actual gas cost, post-state and explorer URL. Never call a hash alone “confirmed.”
