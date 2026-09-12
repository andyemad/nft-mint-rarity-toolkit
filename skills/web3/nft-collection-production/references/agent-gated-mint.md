# Agent-Gated Mint (the agent IS the mint key)

the user's preferred paid-mint mechanism (2026-08-19): a collection that cannot be
minted by a plain wallet click. `mint()` reverts unless the caller presents a
valid **agent-signed permit**. The off-chain agent (your signing server) is the
ONLY key that gates token issuance. The hook ("you need an agent to mint")
replaces hype-driven marketing with a true gate.

This is distinct from the earlier "pin ALPHA token + guaranteed buy-back floor"
mechanic in the parent skill — that one set expected value; this one is about
ACCESS control as the selling point.

## How it works (3-party flow)

1. Wallet signs its intent (its address + a nonce).
2. **Agent (off-chain server)** validates rules (one-per-wallet, supply room),
   signs an EIP-712 `MintPermit(minter, nonce, chainId)`, returns the signature.
3. Wallet submits `mint(nonce, signature)` with value → `_safeMint`.

Contract only mints if `ecrecover(digest, sig) == agent`. No signature from the
correct agent key = reverts. This is exactly the SeaDrop signed-mint pattern but
with the signing role held by a server you run rather than a marketplace.

## Contract essentials (still works with OZ 5.x / solc 0.8.26)

- Roles: `agent` = off-chain signer (the mint key), `owner` = creator admin
  (can rotate agent, withdraw, reserve genesis).
- EIP-712 domain: `EIP712Domain(name, version, chainId, verifyingContract)`.
  Digest = `keccak256("\x19\x01" || domainSeparator || structHash)`, struct =
  `MintPermit(minter, nonce, chainId)`. `block.chainid` in the struct AND domain
  so a permit minted for one chain fails on another.
- `usedNonces[nonce]` mapping = one permit per nonce (no replay).
- `balanceOf(msg.sender) == 0` = strictly one token per wallet.
- Track supply with your OWN `uint256 _supply` counter + `_supply++` — OZ ERC721
  does NOT expose `totalSupply()` publicly, so `totalSupply()+1` throws
  `DeclarationError: Undeclared identifier`. Keep a counter.
- `reserveGenesis()` mints token #1 to owner (sets `_supply = 1`).
- Two mint entry points (pick per UX):
  - `mint(nonce, sig)` — wallet pays gas, presents permit (self-serve).
  - `agentMint(to)` — `onlyAgent`, gasless for user; the agent submits on the
    user's behalf, reinforcing "you need the agent."
- Always `withdraw()` for the creator's accrued mint value.

## Off-chain agent gateway (Python, eth-account)

A tiny local HTTP server signs permits. Flow: agent key (fresh, never linked to
the user) → `POST {"minter": "...", "nonce": N}` → returns `{signature, r, s, v}`.

KEY GOTCHAS hit 2026-08-19 (newer eth-account):
- `eth_account.messages.encode_structured_data` was RENAMED to
  `encode_typed_data`. Import `from eth_account.messages import
  encode_typed_data as encode_structured_data` or just use the new name.
- `encode_typed_data` requires the FULL EIP-712 spec dict passed by KEYWORD:
  `encode_typed_data(full_message=data)` where data has `types` / `primaryType`
  / `domain` / `message`. Passing it positionally throws
  `Invalid domain key: 'types'`. Signature is
  `(domain_data, message_types, message_data, full_message)` — use full_message.
- `Account.sign_message(...)` returns `.signature.hex()`, plus `.r/.s/.v`.
- Recover the OTHER way to TESET the permit issues correctly:
  `Account.recover_message(encode_typed_data(full_message=data), signature=...)`.
  It must equal the agent address — if it does, the contract's `ecrecover`
  check passes too. Verify this BEFORE proposing deploy.
- Older web3 property `tx.rawTransaction` is `.raw_transaction` in current web3
  (`AttributeError: 'SignedTransaction' object has no attribute
  'rawTransaction'`).
- RH-chain gas is ~0.02 gwei; a deploy is ~1.6M gas ≈ $0.00006, a plain
  transfer 21k gas. To outrun the base fee bump, push `gasPrice = int(1.5 *
  eth.gas_price)` — the RPC returns `max fee per gas less than block base fee`
  if you quote stale gas.

## Honest framing

An agent-gate is a great mechanism but it still needs a room to mint. The gate
is not distribution. Pair it with the competitor-launch forensics / X channel
playbook — the gate makes the mint feel exclusive, it does not conjure buyers.
Keep one-per-wallet so scarcity + the gate work together, and never fund the
agent's deploy wallet from any wallet linked to the user (see parent skill's
Anonymity rule — same trace applies to the agent key funding).

## Files (2026-08-19 working build, ~/Projects/mint-page/)

- `contract/StillUpAgentGated.sol` — verified compile, 17,582 bytes, 51 ABI.
- `agent/agent_gateway.py` — local permit-signing server (localhost only;
  never public-internet it with a real key — add auth/rate-limiting for live).
- Mint page + manifest in the same project dir.
