---
name: ethereum-wallet-operations
description: Use when creating, backing up, or sending assets from EVM wallets. Handles local keys, verification, and safe transfers.
---

# Ethereum Wallet Operations

When to use: the user asks to create or back up a wallet, send native currency/tokens/NFTs, or operate bot-wallet assets. This includes bulk ERC-721 transfers, recipient and ownership verification, transaction preflight, bounded gas, signing, broadcast, and receipt verification.

## Core recipe (no installed EVM tooling needed)

Prefer the re-runnable generator: `uv run --quiet --with eth-account python3 ~/.hermes/skills/web3/ethereum-wallet-operations/scripts/create_wallet.py <name>` — it does steps 1–5 below and prints address/path only. Manual equivalent (macOS ships no eth-account / eth_keys / cast; `uv run` gives an ephemeral env, PEP 668-safe):

```bash
uv run --quiet --with eth-account python3 - <<'EOF'
import os
from eth_account import Account
acct = Account.create()
path = os.path.expanduser('~/.hermes/secrets/<name>_key')
with open(path, 'w') as f:
    f.write(acct.key.hex() + '\n')
os.chmod(path, 0o600)
acct2 = Account.from_key(open(path).read().strip())
print("ADDRESS:", acct.address)
print("MATCH:", acct.address == acct2.address)
EOF
```

Steps:
1. Generate locally with `Account.create()` — secure RNG, key never leaves the machine.
2. Write key hex to `~/.hermes/secrets/<name>_key` with `chmod 600`. That directory is the established convention (existing files: bot_wallet_key, opensea_key, agentmail_api_key …).
3. **Re-derive the address from the saved file and assert match** — proves the backup file is correct before reporting success.
4. Verify on-chain with balance checks (below). A fresh wallet reads 0 balance on both chains.
5. **Never print the private key to chat** — address + file path only.

## On-chain verification (public RPC balance check)

`eth_getBalance` (address, latest). Verified endpoints, 2026-08-18:

- Ethereum mainnet: `https://eth.merkle.io` — worked. (cloudflare-eth.com → `-32603 Internal error`; ethereum-rpc.publicnode.com → timeout; eth.llamarpc.com → HTTP 521; 1rpc.io → 503; ankr → requires key. Fail over, don't fight one endpoint.)
- Robinhood Chain: `https://rpc.mainnet.chain.robinhood.com` — worked. (rpc.arrowrpc.com → `error code: 1033` that session; the official RPC is rate-limited — fine for a single balance check, not for bulk scans.)

```bash
curl -s -m 12 -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_getBalance","params":["<ADDR>","latest"],"id":1}' \
  https://eth.merkle.io
```

## Pitfalls

- **The terminal tool rejects heredocs containing `&`** as "backgrounding": e.g. `os.stat(path).st_mode & 0o777` inside a `python3 - <<'EOF'` block fails the command before it runs ("Foreground command uses '&' backgrounding"). Avoid `&` in heredoc code — print perms with `oct(os.stat(path).st_mode)[-3:]` instead, or write the script with write_file and run it.
- Plaintext key file is standard for bot/test wallets but only as safe as the Mac itself. For anything holding real funds, offer an encrypted JSON keystore (`Account.encrypt`, passphrase) or a hardware wallet. State it plainly once; don't lecture.
- Losing the key file = wallet gone forever. Offer a second backup copy whenever the wallet matters (e.g. encrypted keystore alongside the plaintext file).
- Public wallets attract spam airdrops — never interact (see `ethereum-data-pipelines` wallet-recon notes).
- A fresh EOA can receive NFTs or native currency without holding gas funds. It needs native gas funds to initiate ordinary transactions; funding requires the user (or an approved send from an existing wallet). Do not ask users to fund a recipient merely to receive NFTs.
- **Funding from an owned wallet permanently breaks anonymity.** If the wallet is meant to be anonymous (anonymous mint/launch — see `nft-collection-production`), never seed it from the bot wallet or any wallet linked to the user: that funding tx is a permanent, public on-chain trace back to them (owner → deploy wallet → contract). Anonymous wallets must be funded from an unrelated source (exchange withdrawal to a brand-new wallet, fresh fiat on-ramp, or a wallet with no prior link to the user).

## Signing & sending: durable pitfalls

- **eth-account v6 EIP-712 API changed.** `encode_structured_data` no longer exists.
  Use `encode_typed_data(full_message=<spec_dict>)` (keyword arg, not positional).
  The full spec dict is `{types, primaryType, domain, message}`. Recovery is
  `Account.recover_message(encode_typed_data(full_message=...), signature=...)`.
  Symptom of the old call: `ImportError: cannot import name 'encode_structured_data'`
  or `Invalid domain key: 'types'`.
- **Verify EIP-712 signatures against the contract's own digest, not just
  sign-then-recover with the same library.** If the gateway signs with eth-account
  and the contract recomputes the digest from its own struct hash + EIP-712 domain,
  a library-vs-contract mismatch is invisible to a same-toolbox round-trip. Recompute
  the digest by hand (from the contract formulas) and assert it equals the gateway's.
- **EIP-1559: set gasPrice above the live base fee, or the tx is rejected.**
  Symptom on RH chain:
  `max fee per gas less than block base fee ... maxFeePerGas: X baseFee: Y`.
  Fix: push `gasPrice = int(web3.eth.gas_price * 1.5)` rather than the bare quote
  (the quote can be lower than a base fee that ticked up). For a full wallet drain,
  `send = balance - 21000*gasPrice - 1` (keep the dust, never send more than held).
- **Robinhood / Arbitrum L2: do not hardcode 21000 gas for ETH transfers.**
  `eth_estimateGas` returned `0x5309` (21257) and `0x5246` on this chain; sending
  with `gas=21000` reverts `intrinsic gas too low` even when `maxFee` is correct.
  Always `eth_estimateGas` the exact transfer (and the `safeTransferFrom`) and use
  that value for the signed tx. Buffer `maxFeePerGas` to `max(baseFee*1.2, baseFee+10 gwei)`
  — a bare `baseFee*2` pinned to 0.7 gwei still failed when `baseFee` ticked up
  between estimation and broadcast. See `references/robinhood-l2-gas-and-sweep.md`.
- **Time-sensitive mints: bundle mint+transfer in one approval slate.**
  The user funded the Kuantom bot (`0xD572…5553`) for 4 more mints and said
  "mint with remainder and send back" — splitting that into mint-approval then
  transfer-approval burned the mint window while approvals round-tripped. When the
  user funds for a remainder, propose one slate covering `puzzle→solve→voucher→sign→submit`
  (batch where supported) plus the subsequent `safeTransferFrom`(s) and ETH sweep,
  with exact costs and dust, so a single YES executes the whole intent.
- **web3 sign: attribute is `.raw_transaction`** on `SignedTransaction`, not
  `.rawTransaction` (snake_case in current web3).

## User-held browser wallets

- Establish which address is the source and which is the recipient, and where the source is accessible. Creating a recipient in Rabby does not itself establish access to the source.
- Keep existing user keys in Rabby or their current wallet. Do not default to exporting keys or importing them into a bot application merely to perform bulk transfers. Public-address discovery and simulation do not require a private key; the user handles wallet unlock and final signing.
- When the user narrows a multi-recipient request to one recipient “first,” prepare only that first batch. Once they say “any 50,” use a disclosed deterministic selection without asking again about rarity or token preferences.
- Distinguish verified holdings from transaction readiness: a balance check alone does not establish selected token IDs, successful simulations, sufficient aggregate gas, or a working signing flow. Do not describe a browser transfer route as verified until its actual controls and transaction preview have been inspected.

## Bulk-transfer requests: solve the signing bottleneck

- When the user asks to mass-send NFTs, do not substitute a one-by-one marketplace tutorial, ask him to hunt for selection checkboxes, or repeatedly request screenshots of a flow he has already said cannot batch. The task is to remove repetitive transfer work, not explain the manual workaround.
- Resolve the signing route early, alongside read-only discovery. Distinguish an automated queue of individual transactions from a true on-chain batch and from wallet batch signing: these can require very different numbers of user confirmations. Do not promise one confirmation merely because a page queues many calls.
- Verify the exact chain, deployed contract/source, wallet capability, and full transaction preview before recommending a batch service. An ERC-721 contract, an arbitrary multicall deployment, or a wallet brand name alone does not prove safe batching support.
- Check source native balance and aggregate gas early. Estimate the actual chosen route, including any helper deployment, operator approval, transfer, and revocation. Independent transfer estimates are not proof of the batch route's cost or success.
- Keep progress factual and short: selected IDs, simulations passed, actual remaining blocker. A running research/build subagent is not a completed transfer tool. Never present an untested helper or unresolved batch-signing experiment as an established workflow.
- A newly deployed helper or operator approval adds external consequences: include its scope and maximum total spend in the consolidated approval. Never silently deploy or grant approvals just to satisfy a demand to hurry.

Verified read-only discovery/preflight techniques are in `references/nft-transfer-discovery-preflight.md`; these do not establish a working batch-signing route.

## Bulk ERC-721 transfers

For deterministic token discovery, recipient checks, per-token simulation, gas ceilings, sequential broadcast, and post-transfer verification, use `references/bulk-erc721-transfers.md`.

For Robinhood Chain bulk transfers without exporting Rabby keys, see `references/robinhood-opensea-bulk-transfer.md`: bytecode-verified OpenSea TransferHelper/conduit route, correct chain-specific key, and approval caveats. **IMPORTANT:** this helper/conduit route REVERTS on ERC721-C collections that use a transfer-security registry — only owner-direct `transferFrom` passes then. Detect via `getTransferValidator()`; see the ERC721-C section in `references/bulk-erc721-transfers.md` before choosing any operator batch route.

## Related

- Read-side analysis, P&L recon, Seaport fills, RPC failover details: `ethereum-data-pipelines` (scripts/wallet_recon.py, references/robinhood-chain-nft-mint-data.md).
- Multi-wallet mint kits already build wallet factories and fund them at ~3c each: `ethereum-data-pipelines` → `references/seadrop-multi-wallet-mint-sniper.md`.
