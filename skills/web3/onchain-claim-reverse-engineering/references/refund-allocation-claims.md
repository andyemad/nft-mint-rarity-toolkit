# Refund/allocation claims when the frontend lies

Use when a raffle/claim site says a wallet "did not enter," "not eligible," or shows no allocation even though the user believes they paid.

## Source-of-truth sequence

1. Read the original transaction and receipt from the chain:
   - receipt `status`;
   - exact `from`, `to`, and `value`;
   - decoded function selector/arguments;
   - emitted entry/deposit events.
2. Call the contract's live entry/allocation getters from the exact transaction sender. A successful transaction plus nonzero `entriesOf(sender)` overrides misleading frontend copy.
3. Verify the connected wallet address. A correct allocation queried for the wrong browser wallet commonly renders "did not enter."
4. Inspect the frontend's claim/allocation endpoint and client logic. Query the endpoint using the exact checksum/lowercase sender address if necessary.
5. Read finalized contract state: allocation root, claims-open flag, claimed/refunded status, and NFT/refund amount.
6. Independently verify any Merkle allocation against the on-chain root. Do not trust an API proof merely because it returned HTTP 200.
7. ABI-encode the exact claim call and run `eth_call` plus `eth_estimateGas` from the claimant address. A refund-only allocation should be represented explicitly as `nftAmount = 0`, nonzero refund, proof.

## Safe execution

Before approval, report separately:

- entry transaction outcome;
- raffle result (NFT allocation count);
- exact refund amount;
- whether the Merkle proof matches the chain root;
- whether the claim simulation succeeds;
- value sent by the claim transaction (normally zero) and estimated/max gas.

Use one bounded approval slate for one claim transaction. Hard-cap gas; send no ETH value unless the verified ABI requires it. Read the existing key from its chmod-600 secret file without printing it.

After approval:

1. Re-fetch allocation and claimed status to prevent replay/stale-proof errors.
2. Simulate again immediately before signing.
3. Sign and broadcast once.
4. Poll a real receipt and require `status == 1`.
5. Verify contract claimed/refunded getter, NFT count, and wallet balance delta.
6. Record transaction hash, exact refund, and exact gas spent. Never report success from a broadcast hash alone.

## Worked pattern: Blokyz raffle refund

The frontend displayed "This wallet did not enter the raffle," but Ethereum showed a successful `enterRaffle(9)` transaction with exactly 0.27 ETH and `entriesOf(sender) == 9`. The project API returned an allocation of zero NFTs and a full 0.27 ETH refund with a 15-node Merkle proof. The proof matched the live allocation root; the exact refund-only claim passed `eth_call` and gas estimation. After approval, one zero-value claim transaction confirmed with status 1, `refundClaimedOf(sender) == true`, zero NFTs claimed, a 0.27 ETH balance increase before gas, and exact gas accounting. The bug was frontend/wallet-state messaging, not missing funds.
