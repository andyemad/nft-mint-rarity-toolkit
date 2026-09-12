# Wallets

Create wallets, and reconstruct what a wallet actually did.

| File | What it does |
|---|---|
| `create_wallet.py` | Generates a fresh EVM wallet locally, writes the key to `~/.hermes/secrets/<name>_key` (`chmod 600`), and re-derives the address **from the saved file** to prove the backup is readable. Prints address + path, never the key. |
| `wallet_recon.py` | Multi-chain NFT trading P&L: every acquisition (mint/buy) and disposition (sell/transfer), exact amounts, FIFO matching, realized P&L, open inventory at cost basis, total gas. No API keys. |

## Usage

```bash
uv run --quiet --with eth-account python3 create_wallet.py <name>

python3 wallet_recon.py <address>
```

## Conventions this code enforces

- **Keys are files, not arguments.** Key material in an argument lands in shell
  history and in `ps`. Read it from a path at runtime.
- **Print the address, never the key.** After writing a key, re-read the file and
  derive the address again — if that fails, the backup is worthless.
- **`chmod 600` and a `700` directory.** Anything looser is a finding, not a
  preference.
- **Never import a user's existing wallet key into a script just to move
  tokens.** Simulation and address discovery need no private key; the wallet
  owner does the final signing.

## P&L reconstruction notes

- **WETH is the cleanest money-flow source** on Ethereum: exact gross ERC-20
  transfers with no gas entanglement. Use it when the trade is WETH-denominated.
- **On Robinhood Chain, use the state-change coin delta**, not the
  internal-transfers endpoint — that endpoint *misses* Seaport sweep proceeds and
  silently understates every bundle purchase.
- **Mints are not buys.** A token received for free or for gas only is not a
  market purchase; conflating the two inflates cost basis and destroys the P&L.
- **Gas is a real cost.** Report it separately and include it in the verdict; on
  a 0.001 ETH trade it can exceed the trade.
