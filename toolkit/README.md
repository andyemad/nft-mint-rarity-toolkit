# toolkit — runnable code

Grouped by the job to be done. Each directory has its own README with usage,
verified constants and the failure modes that were actually hit.

| Directory | Job |
|---|---|
| [`rarity/`](rarity/) | Rank a collection by rarity (OpenRarity information content), detect reveals, render a dashboard |
| [`mint/`](mint/) | SeaDrop multi-wallet public mint; local signer/broadcaster for value-zero mints |
| [`pow/`](pow/) | Proof-of-work nonce miners — CPU (OpenMP), CUDA, Metal; FAB4200- and Hashcats-style preimages |
| [`sniper/`](sniper/) | Secondary-market buys via Seaport, plus a read-only fill diagnostic that shows the real revert |
| [`wallets/`](wallets/) | Wallet creation/key handling and multi-chain NFT P&L reconstruction |
| [`analysis/`](analysis/) | Secondary volume, minter legitimacy, sweep scoping — all keyless |
| [`contracts/`](contracts/) | Solidity drop mechanics (reset-on-mint decaying price) |
| [`did/`](did/) | did:key agent identity + signed writes |

## Conventions

- **Python standard library only** unless a docstring or README says otherwise.
  Signing paths need `eth-account`, `coincurve`, `pycryptodome`.
- **Config lives at the top of each script** as module-level constants
  (`CONTRACT`, `SUPPLY`, `RPC`, `BASE`, caps). Copy a script and edit the
  constants; they were written as templates.
- **Read-only by default.** Anything that can spend requires an explicit
  `--send` / `--fire` / armed flag, and simulates (`eth_call`) before it sends.
- **Keys are file paths, never arguments; addresses are printed, keys are not.**
- **State is cached on disk** so reruns are cheap (`~/.hermes/rarity/…`,
  `.runtime/…`, `dashboard_out.html`).

## Before you run anything that spends

1. Read the README in the directory you are about to use.
2. `eth_call` simulate. A clean simulation is required, not optional.
3. Confirm the wallet's real balance on-chain and cap your spend against it.
4. Confirm the chain you are pointed at (Robinhood Chain is `4663`).
5. Remember a free mint is still an irreversible public transaction.

Nothing here is financial advice. Every strategy in this toolkit has a real loss
mode documented next to it, and several of the skills exist specifically to
record a method that failed.
