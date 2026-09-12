# Mint

Fire a public mint: multi-wallet SeaDrop kits, and a local signer/broadcaster for
value-zero PoW mints.

## Files

| File | What it does |
|---|---|
| `seadrop_fire.py` | SeaDrop public-mint toolkit: recon, fresh-wallet generation, funding poll, `eth_call` dry-run, broadcast, verify. |
| `send_mint_tx.py` | Signs and broadcasts a single `mint(nonce)` transaction (value 0, e.g. a PoW mint). Dry-run by default; `--send` to broadcast. |

## SeaDrop flow

The order matters. Every step is here because skipping it cost a real drop.

```bash
# 1. recon: is it open, price, cap, window, fee recipient, supply left
python3 seadrop_fire.py recon <collection>

# 2. generate N fresh wallets; prints each ADDRESS plus the exact amount to fund
#    (price*qty + gas buffer + margin). Stop and fund them yourself.
python3 seadrop_fire.py wallet <collection> 3

# 3. poll until funded
python3 seadrop_fire.py check-funded <collection> --wallets 0xA,0xB,0xC

# 4. pre-flight dry-run (eth_call), then broadcast
python3 seadrop_fire.py fire <collection> --keyfile ~/.hermes/secrets/x_key --quantity 1

# 5. confirm the token actually landed
python3 seadrop_fire.py verify <collection> <address>
```

Verified Robinhood-Chain selectors (get these wrong and you burn gas on a
revert):

| Call | Selector |
|---|---|
| `getPublicDrop(address,address)` | `0xbc6a629c` |
| `mintPublic(address)` | `0xa06cb719` |
| `PublicDropUpdated` topic0 | `0x8764214b5defe9caa9c5b38b36f0cc5e482a8ab15d78696659e61989e48e6e70` |

**Before any broadcast, always:** compare `totalSupply()` to `maxSupply()`. A
closed or sold-out stage is the most common reason a "working" mint script fails
and it fails after you have already paid for the attempt.

**Pre-sign at T-1, blast at T-0.** Signing inside the race costs the race. Keep
the signed raw transactions ready and submit the moment the window opens.

## Signing

`send_mint_tx.py` reads a raw-hex key from a file path (never from `argv`),
derives the address, estimates gas, prints the full cost breakdown, and only
broadcasts with `--send`. Reverting with `0xfcf93064…` on a PoW contract is a
*success* signal for the plumbing. It is the contract telling you the nonce did
not meet difficulty yet.

```bash
python3 send_mint_tx.py ~/.hermes/secrets/bot_wallet_key 1234567          # dry-run
python3 send_mint_tx.py ~/.hermes/secrets/bot_wallet_key 1234567 --send
```

Requires `pip install eth-account coincurve pycryptodome`.

## Pitfalls

- **Robinhood Chain RPC rate-limits per IP** (429 on reads and writes). Batch
  balance checks; do not poll a wallet list in a tight loop.
- **Python `urllib` needs a browser `User-Agent`** or the RPC and the OpenSea API
  answer 403 even with a valid key. `curl` hides this by sending one.
- **Fund the wallet you will actually mint with**, and re-check the balance right
  before the run. A dispatch gate that verified the on-chain balance first
  converted "buy as many as you can" into a correct, affordable plan.
- **Keys generated for a mint must be written `chmod 600`** and never printed.
  Print the address; re-derive it from the file to prove the backup works.
