# Security

## What is in this repository

Playbooks and scripts. **No secrets.** Specifically, none of the following ship
here:

- private keys, seed phrases, mnemonics, keystore files
- API keys, OAuth tokens, session cookies
- webhook URLs (Discord/Slack), agent inbox addresses
- personal identifiers (email, phone, government ID, case numbers)
- the operator's wallet addresses, or any third party's wallet addresses

Wallet addresses that appear in the code are **placeholders**
(`0x1111111111111111111111111111111111111111`,
`0x2222222222222222222222222222222222222222`, `0x1111…1111`). They are not real
accounts and hold nothing. Contract addresses, event topics and transaction
hashes are public chain data and are kept deliberately — they are the evidence
the skills cite.

## The key-handling convention used throughout

Keys live outside any repository, in a dedicated directory, readable only by the
owner, and are referenced by path from code:

```bash
mkdir -p ~/.hermes/secrets && chmod 700 ~/.hermes/secrets
printf '%s' 'YOUR_KEY' > ~/.hermes/secrets/opensea_key
chmod 600 ~/.hermes/secrets/opensea_key
```

Rules the code follows:

1. Read the key from a file path at runtime. Never accept a key as a CLI
   argument (it lands in shell history and in `ps`).
2. Never print key material. Print the derived **address** and the file **path**.
   Re-derive the address from the saved file to prove the backup is readable.
3. Reject key files that are not regular files, or whose permissions include a
   group/other bit (`(mode & 0o077) !== 0`).
4. Bind signing helpers to one expected address where possible, so a swapped key
   file fails loudly instead of signing with the wrong wallet.
5. If a key is ever pasted into a chat or a log, treat it as burned: move funds,
   rotate, never reuse.

## Before publishing any change

Run the audit. It fails loudly on key material, credentials, tokens, webhooks,
personal identifiers and unknown 64-hex strings:

```bash
python3 tools/secret_audit.py            # exit 1 on any hard-fail hit
```

The audit's hard-fail patterns cover: raw 64-hex private keys, PEM blocks,
seed/mnemonic assignments, GitHub/Slack/Google/OpenAI-style tokens, Discord
webhooks, keyed RPC URLs (Alchemy/Infura/QuickNode/Moralis), agent-inbox and
social-intelligence API keys, personal identifiers, absolute home paths, and
operator/third-party wallet prefixes.

### Triage, don't delete

A 64-hex scan produces **false positives you must triage rather than strip**:

- event topic hashes (`Transfer`, `PublicDropUpdated`, `SeaDropMint`, …)
- transaction hashes cited as evidence
- function selectors padded to 32 bytes (e.g. `0xc87b56dd00…`)
- test/placeholder values such as `0xaaaa…`

A real private key lives in a key file or an env var, not inline next to the word
`keccak`. The audit keeps an explicit allowlist of the public constants it
expects and reports everything else for human review, so a genuine key cannot
hide behind a "it's probably fine, it's hex" judgement call.

### Other things that leak

- `git log --all --diff-filter=A --name-only | grep -iE '\.env|secret|key'`
- `.pyc` files and build output (this repo ships a `.gitignore` for them)
- screenshots of terminals containing keys or balances
- example configs copied from a live environment (`.env.example` should contain
  placeholder values only)

## Reporting

If you find key material or a personal identifier in this repository, open an
issue marked **security** without pasting the value, and it will be rotated and
removed.
