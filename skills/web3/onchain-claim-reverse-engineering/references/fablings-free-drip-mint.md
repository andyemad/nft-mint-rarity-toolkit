# FABLINGS free-drip mint — worked example (RH chain, 2026-08-19)

Free mint with NO queue: one global shared line, opens ~every 10s, first tx in the window
wins. Competing wallets claim it in milliseconds. This file records the real numbers and
the daemon pattern that works.

## Contract facts (verified on-chain)

- Items contract: `0xa185814414aa3D39c9A0B73A373E00C8C04Cb384` (RH chain, chainId 4663)
- Free mint fn: `mintFree()` — 0 ETH value, gas only
- Per-wallet cap: 10, read via `freeMinted(address)`
- Selectors (derive, never guess):
  - `mintFree()` → keccak
  - `freeMinted(address)`
  - `balanceOf(address)`, `tokenOfOwnerByIndex(address,uint256)`
  - `transferFrom(address,address,uint256)` for sweeps
- Gas: successful mint ≈ 214k gas; a lost-race revert ≈ 28.8k gas (~$0.001 @ 0.02 gwei)

## Observed race performance

- 5 successful mints out of ~25 broadcasts (~20% win rate) against live bots.
- Every loss mines as receipt status `0x0`, `logs: []` — a **mined revert**, not a failure
  to broadcast and not a minted NFT. Count progress by re-reading `freeMinted(wallet)` /
  `balanceOf(wallet)`, never by the daemon's BROADCAST line.
- Budget 2–3× theoretical gas: $0.10 funded only 5/10 mints. Wallet ran dry mid-batch
  (`insufficient funds for gas * price + value` on broadcast) — the fix is a top-up
  transfer from the funding wallet, then resume; the mint itself was still open.

## Daemon pattern (fast drip snatcher)

```
loop (poll ~1.3s):
    simulate mintFree() from target wallet via eth_call
    if clean: broadcast mintFree() (gasPrice = max(eth_gasPrice, baseFee*1.3), gas 300k)
              wait for receipt; re-read freeMinted; continue
    else:     sleep; continue
until freeMinted == cap or timeout
```

Slow crons (~30s+) miss the window almost entirely — the slot opens and closes inside one
poll interval. Use the fast daemon, and when the cap error `0x53353903` appears the wallet
is done (cap reached), not the collection.

## Sweep pattern (collect minted NFTs)

After minting, transfer tokens to a collector wallet (user's source-of-funds wallet):

```
for each tokenId in tokenOfOwnerByIndex enumeration:
    transferFrom(newWallet, collector, tokenId)   # gas only, ~$0.008 @ 0.02 gwei
```

Include sweep gas in the budget — 10 sweeps ≈ 10 gas txs on top of the mints.

## Wallet setup used

- Fresh burner created locally: `uv run --quiet --with eth-account python3` →
  `Account.create()`, key saved `~/.hermes/secrets/new_wallet_key` (chmod 600),
  address re-derived from the file to verify the backup matches.
- Funding: plain ETH transfer from the funding wallet; **RH RPC rejects gas=21000**
  ("intrinsic gas too low") — use gas=60000+ for plain transfers.
- RH RPC: `https://rpc.mainnet.chain.robinhood.com`; base fee from
  `eth_getBlockByNumber("latest", false)["baseFeePerGas"]`; gasPrice must clear baseFee.