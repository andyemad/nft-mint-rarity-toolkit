# Agent identity (did:key)

Give an autonomous agent a verifiable identity it can sign with, so a public
board can tell one agent's posts from another's.

`flop-labs-sign.py` derives a **did:key** from a local seed, signs payloads, and
posts them to a protocol's key-value store. Used in production to onboard three
separate agents (each with its own seed file) to a public agent protocol.

```bash
python3 flop-labs-sign.py did    --seed "$(cat ~/.hermes/secrets/<agent>_seed)"
python3 flop-labs-sign.py sign   --seed ... --payload '<json>'
```

## Why did:key rather than a wallet

- One seed file per agent, `chmod 600`, outside the repo, the same convention as
  everything else here.
- The identity is derived, not registered: no account, no email, no platform that
  can lock you out.
- Signatures are verifiable by anyone reading the board, so a reader can
  distinguish a real agent post from an impersonation.

## Rules when the surface is public

- **Treat the board as world-writable and permanent.** Anything signed is
  attributable to that DID forever.
- **Never post** wallet addresses, positions, P&L, business plans, personal
  identifiers, or anything an adversary could act on. Post capability write-ups,
  walkthroughs and fun content.
- **Keep each agent's seed separate.** Three agents sharing one key means three
  agents that cannot be told apart, which defeats the point.
- **Back up seeds before onboarding.** A DID you cannot re-derive is a DID you
  cannot use again; the identity is the seed.
