# Chain-mismatch-first triage

Use this reference when a mint site accepts a link but the user reports wallet errors.

## Proven case: Blokyz public raffle (2026-08-28)

The user was attempting the mint while their wallet was on Robinhood Chain. The site was Ethereum Mainnet:

- page metadata: “official Original Blokyz public raffle on Ethereum”;
- live API snapshot: `chainId: 1`;
- frontend chain config: Ethereum RPC and Etherscan explorer;
- bundled error copy: “Switch to Ethereum Mainnet to continue.”

The correct first answer was simply to switch the wallet network to Ethereum Mainnet. Contract and price recon was useful, but inventorying unrelated locally stored wallets and calculating raffle odds before surfacing the chain mismatch was unnecessary.

## Reusable order of operations

1. Read visible metadata and live API state for explicit chain identity.
2. Inspect the bundle for chain ID, RPC, explorer, and wrong-chain error text.
3. Compare that chain with the chain the user says they are on, when known.
4. If mismatched, give the one-step network fix immediately.
5. Continue contract simulation or signer discovery only if the user still wants agent execution after switching.

This rule is diagnostic prioritization, not permission to connect, sign, spend, or broadcast. Those remain separately approval-gated.
