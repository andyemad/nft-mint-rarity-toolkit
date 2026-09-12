# Wallet-farm lifecycle for multi-wallet mints (2026-08-22 session)

Pattern: create N fresh EVM wallets → fund gas from a treasury wallet → mine one
PoW nonce per wallet in parallel on Modal GPUs → broadcast mints → sweep leftover
gas back when the mint closes (or mints out). All steps verified live; scripts
referenced below lived in /tmp during the session.

## Wallet factory

- `Account.from_key("0x" + secrets.token_hex(32))` — no extra deps beyond eth_account.
- Store each key as a plain hex file chmod 600 under ~/.hermes/secrets/, plus a
  JSON registry `{name: {address, keyfile}}` also chmod 600. Never echo keys.
- **Pitfall**: background terminal shells may resolve a different python than the
  interactive one. On this Mac, eth_account worked interactively but background
  runs hit a broken pydantic_core (arch mismatch in user site-packages). Don't
  fight PYTHONPATH — sign with coincurve instead (below), which has no pydantic dep.

## Signing without eth_account (coincurve + hand-rolled RLP)

When eth_account is unavailable/broken, legacy txs can be signed with coincurve +
pycryptodome only:

- RLP encode fields `[nonce, gasPrice, gas, to, value, data, chainId, 0, 0]`
  (EIP-155), keccak the encoding, `pk.sign_recoverable(digest, hasher=None)`,
  v = recid + 35 + 2*chainId.
- Address derivation: last 20 bytes of keccak(uncompressed pubkey[1:]).
- **Critical RLP bug to avoid**: integer 0 encodes as `0x80`, NOT empty bytes.
  A `if item == 0: return b""` branch in the encoder silently corrupts every tx
  containing a zero field (chainId tail, empty data). Symptom: node reports a
  completely different recovered sender address. Test the encoder against known
  vectors first (`rlp(0)==80`, `rlp(128)==8180`, `rlp([1,2])==c20102`).
- gasPrice must exceed block base fee — multiply eth_gasPrice by ~1.2 or txs
  reject with "max fee per gas less than block base fee".

## Funding N wallets without nonce races

Naive loop that calls eth_getTransactionCount(pending) per tx races itself:
half the sends fail with result=None (replacement/underprined at same nonce).
Fix: sequential send-then-wait-for-receipt before the next send, and make each
run idempotent by checking balances first and only topping up wallets below
target. ~12 wallets × 0.0003–0.0004 ETH ≈ $0.50 total gas float.

## Sweep-back (mint closed / minted out)

- For each fresh wallet: balance − (21000 × gasPrice×1.3) → send remainder to
  treasury. Sequential with receipts, same as funding. All 12 confirmed 0x1.
- Check ERC721 balanceOf per wallet before declaring done — NFTs do NOT move
  with an ETH sweep (moving them needs safeTransferFrom calls per token).
- Kill all Modal jobs FIRST so no miner spends credit against a dead mint.

## Mint-out race realism

On a hot free mint (4200 supply, ~50/hr burn at peak), a 12-wallet parallel
batch takes: fund (~5 min) + mine (~4 min/wallet, parallel ≈ 5 min) + broadcast
(~1 min) ≈ 15 min door-to-door if everything is pre-built. This session's batch
was built AFTER the user said go and missed the close by that margin. If the
goal is max-mint-before-out, build the wallet set and fund it BEFORE the mint's
final hours, not after.

## Multi-agent division of labor (user-directed)

User explicitly asked for parallel workstreams: one agent continues minting/
infrastructure while another builds UI features. Use delegate_task for the UI
build; keep signing/minting in the primary session (keys never leave it).
