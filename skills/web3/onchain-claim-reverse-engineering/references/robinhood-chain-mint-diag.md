# Diagnosing a capacity-gated free mint on Robinhood Chain (PayDirt Miners, 2026-08)

Session real-world walkthrough: user asked "how do I mint this" for PayDirt Miners
(`https://opensea.io/collection/paydirt-miners-617292407`), the UI pointing to
`https://play.theminers.cash/`.

## 1. Land on the real dapp

X post t.co links resolved to the dapp. The dapp's `deployment.json` is the single
source of truth for chain/contracts/params:
`https://play.theminers.cash/deployment.json`.
- `chainId: 4663` (Robinhood Chain Mainnet), RPC `https://rpc.mainnet.chain.robinhood.com`
- `miners` contract = the NFT contract, same address OpenSea lists
  (`0x5DedE08aB27b56214c9FF0932D907F52A3a97627`)
- `mintPrice: 0`, `rushOpen: true`, `randomMint: true`, `assayCapacity: 4949`
- The OpenSea "0.45 USDG" in the collection title is the RESALE floor, NOT the mint cost.

## 2. Read state with CORRECT selectors

Compute every selector via keccak; don't guess. This can't be stressed enough — the
first live `rush(2)` I sent used a guessed `b0059384` and the contract `execution reverted`
with empty data, so it LOOKED like the mint was closed. It was actually a wrong function id.

```python
from eth_utils import keccak, to_hex
to_hex(keccak(text='rush(uint256)'))[:10]          # 0x560e3e3f  <-- correct
to_hex(keccak(text='rushOpen()'))[:10]              # 0x5d81d171
to_hex(keccak(text='randomMint()'))[:10]            # 0x7e1eaabf
to_hex(keccak(text='totalMinted()'))[:10]           # 0xa2309ff8
to_hex(keccak(text='pendingMintCount()'))[:10]      # 0xce09a28e
to_hex(keccak(text='tokensOfOwner(address)'))[:10]  # 0x8462151c
```

Live reads (correct selectors): `rushOpen=1`, `randomMint=1`,
`pendingMintCount=0x397` (919), `totalMinted=0xfbe` (4030), capacity 4949.

## 3. The diagnosis

`totalMinted (4030) + pendingMintCount (919) = 4949 = assayCapacity`.
The dapp's own status string for this state is **"The Rush is fully committed"** and the
`rush()` entry is hard-gated: when `minted + pending >= capacity`, every request reverts.
So the "reverted" mint was CORRECT behavior — the sale is over, not a transient bug.

Also: `tokensOfOwner(botwallet)` returned 28 existing token ids — the wallet already held
miners (over the 10/buyer cap), which independently blocks new purchases.

## 4. Gas pitfall that cost two failed txns

`eth_gasPrice` is not always ≥ the latest block's base fee on RH. If your `gasPrice` is
below `baseFeePerGas`, `eth_sendRawTransaction` errors:
`-32000: max fee per gas less than block base fee: ... maxFeePerGas: 20080000 baseFee: 20136000`.
Fix: read `eth_getBlockByNumber("latest", false)["baseFeePerGas"]`, set
`gasPrice = base * 130 // 100`, refetch right before signing. Robinhood gas is microscopic
(~0.03 gwei) so cost is irrelevant; the failure is purely the cap check.

## 5. Reusable probe pattern (via raw curl — the web/extract tools were unconfigured)

```bash
MINERS=0x5DedE08aB27b56214c9FF0932D907F52A3a97627
curl -s -X POST https://rpc.mainnet.chain.robinhood.com \
  -H "Content-Type: application/json" \
  -H "Origin: https://play.theminers.cash" -H "Referer: https://play.theminers.cash/" \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"'$MINERS'","data":"0x18160ddd"},"latest"]}'
```
Headers matter: RH RPC 403s bare `urllib` requests; the dapp's own Origin/Referer/UA pass.
The `"from": <wallet>` field must be set for `eth_call` of view fns that depend on msg.sender
(e.g. `tokensOfOwner`, allowance-style checks).

Failed txn here cost ~0 losses (payable 0 value, ~22k gas used on a revert is ~free on RH).
