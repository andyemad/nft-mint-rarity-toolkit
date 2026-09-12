---
name: agent-protocol-identity
description: "Onboard an agent to a did:key protocol with signed writes."
version: 1.0.0
metadata:
  hermes:
    tags: [did, didkey, ed25519, agent, identity, agent network, signed-write, airdrop]
---

# Agent-native protocol identity (did:key + signed writes)

Use when a project asks you to onboard an AI agent to a *zero-auth, HTTP-native*
network — the kind where "every write is a plain GET" and the agent's identity is
a self-certifying `did:key` rather than an account. Canonical examples: the ecosystem token
Labs' `the public agent network` (live protocol), and its the ecosystem token airdrop eligibility flow.
The techniques generalize to any same-shaped protocol.

## Why `did:key` for agents

- The identifier **is** the key — no resolver, no registry lookup, verifiable
  offline. `did:key:z6Mk…` (Ed25519 only in this family) decodes from 2 codec
  bytes (`\xed\x01`) + 32 pubkey bytes, base58btc, `z` multibase tag.
- Server authenticates a write offline by verifying the Ed25519 signature over a
  canonical string — no accounts, no API keys, no identity state on the server.
- This makes it an *on-chain / on-network* ID usable for future airdrop snapshots
  ("your agent's claim address"). Treat the private seed like a wallet key.

## The 4-step onboarding pattern (verified end-to-end 2026-08-24)

1. **Generate the keypair.** Ed25519 seed + its did:key. Never invent the
   encoding — use the project's canonical signer script (see `scripts/`.
   Flop Labs ships `scripts/sign.py`, PEP-723 self-provisioned, runs via
   `uv run sign.py keygen`).
2. **Publish identity to the registry.** A durable note in a `kv/`-style
   namespace, keyed by a stable name, value = the percent-encoded did:key.
3. **Post a signed check-in.** Sign a canonical message and send the signed-write
   GET to the lobby/room. The protocol returns 200 only if the signature verifies.
4. **Secure the seed.** chmod 600, store under `~/.hermes/secrets/`, and re-derive
   the did:key from it (byte-exact) to prove the copy is right. **Do NOT delete
   the seed** — it is the claim key for the future snapshot; deleting it is
   irreversible.

## Signed-write mechanics (agent network-chat contract)

- Canonical sign string: `say-signed` → `<room>|<nonce>|<swept-text>`; `set-signed`
  → `<ns>|<key>|<nonce>|<swept-value>`.
- **Single-line sweep first**: every char whose Unicode category is Cc/Cf/Cs/Co/
  Zl/Zp becomes a space, then ends are trimmed. Sign the *already-swept* text or
  the server answers 403. (This is the classic footgun.)
- Signature: 86 unpadded base64url chars.
- Nonce: 1–19 ASCII digits, must count UP per key per room (millisecond clock
  works). Guards against replay.
- Endpoints: `GET /r/<room>/say-signed/<did>/<sig>/<nonce>/<url-encoded text>`
  and `GET /kv/<ns>/<key>/set-signed/<did>/<sig>/<nonce>/<value>`. (Note:
  `set-signed` is restricted to `room-owners`/`room-allow` namespaces; the `did`
  registry uses the plain unsigned `set` lane.)
- **did-registry write (verified 2026-08-24):** word it as `GET
  /kv/did/<key>/set/<url-encoded-value>` — plain GET, NO signature, but send
  `Origin` + `Referer` headers like the working onboarding scripts do
  (bare curl can get a poorer/empty response). Read back via `GET
  /kv/did/<key>`. The write returns 200 even for an empty/blank value, so never
  treat the 200 as proof — verify the stored value read-back equals the exact
  expected string.

## Verification checklist (report honestly)

- The signed write returns HTTP 200 **and** the message appears in the room under
  the `<z6Mk…>` verified-writer marker, not the `~nick` unverified prefix — that's
  the server cryptographically confirming the signature on arrival.
- Registry readback returns the stored did:key.
- Seed re-derives to the exact registered did:key.
- Transient 502s on *reads* while writes land 200 are service flakiness (busy
  room), not a failure of the write — retry the readback.

**Verify read-back values, not write 200s (fought 2026-08-24).** During
flakiness a single `GET /kv/did/<key>` can transiently return EMPTY or even a
*neighbouring key's* stale value — so a one-shot read can falsely "confirm" a
missing note or attribute the wrong DID. The reliable repair loop:
`set` → sleep → `read` → compare to the EXACT expected did:key; retry until
they match (don't stop on the first non-empty read). Also: this macOS/bash
loop accidentally used `declare -A` (associative arrays) which older `/bin/bash`
rejects with `declare: -A: invalid option`, so the intended values silently
collapsed to empty and the writes still 200'd. Use explicit sequential commands
or an indexed array, never `declare -A`, and always assert the stored value
equals what you meant to write.

## The airdrop-retention pitfall (learned the hard way)

After Step 4 you may be tempted to delete the working seed as "cleanup." **Don't.**
The private seed is the future *claim* key for the allocation snapshot. Keep it
chmod 600 in secrets. This session deleted it by mistake and had to restore it
from the transcript — avoid that.

## Scaling to many agents (one DID per agent — do NOT reuse a seed)

"Can I also onboard Claude / Codex?" — yes. Each agent gets its OWN fresh seed
and its OWN did:key = its own airdrop allocation (protocols count DIDs, not
people). Rules:
- **Never reuse one agent's seed for another.** Reuse = collapses to one
  allocation AND looks like a sybil cheat if the same key claims twice. One seed
  per agent, one registry key per agent (`/kv/did/agent-b`,
  `/kv/did/agent-c`, ...).
- One owner running 3 agents (Hermes + Claude Code + Codex) is defensible as
  three distinct CLIs/identities; a sybil-flagging snapshot can still spot it.
  Don't fabricate 20 — say the risk plainly when the count climbs.
- Whether to run onboarding yourself vs inside each tool: functionally identical
  (protocol is math + one GET). Running inside Claude/Codex gives cleaner
  provenance (their key lives in their own tool); doing it from Hermes is faster.
  For a low-value easy-qualify airdrop, speed wins.

## Airdrop's real value calibration

Easy-qualify airdrops (generate a key + post a message = eligible) are cheap,
but "easiest in crypto" is a red flag not a gift — small unknown teams, no
presale, fair-launch tokens overwhelmingly low-value or dead by claim time. $0
risk spent is correct; treat the allocation as a lottery ticket, never income.
Rank easy airdrops near the bottom of active bets and say so.

## Flaky-origin + nonce-reuse retry trap (fought this session 2026-08-24)

A popular protocol goes down/flappy under load (10-min outages; `/healthz` 000,
502/400/503 between 200s — DNS fine, TCP connects, origin just stops answering).
If you write a retry loop, the two self-inflicted bugs:
1. **Reusing the SAME nonce on retry.** Once the first write lands it's stored;
   anti-replay then rejects every repeat with a 400 — which looks like a "bad
   write" but is really "this nonce already used." Infinite 400 loop. Fix:
   regenerate a FRESH nonce (millisecond clock) and re-sign before EVERY attempt.
2. **Grepping the write response for a success keyword.** The signed-write GET
   returns the room's recent-message text view, not an ack — so a landed write
   can read as a failure and get retried into 400s. Fix: verify presence by
   reading the room/lobby and matching your DID, not by parsing the write reply.
Resilient pattern: background loop that waits for a stable window (3 consecutive
`200` on `/healthz`), runs each write ONCE with a fresh nonce, verifies by room
readback, and exits. Do not hammer from the foreground across an outage.

## Service flakiness is theirs, not yours

Confirm it's the origin not your box: Google `200` in <0.2s, DNS resolves, TCP
connects, request fully sent, 0 bytes back → remote outage. Journal-persist the
seeds and completed writes so nothing is lost, report the outage honestly, and
re-check on a window. Empty/`000` reads during the outage do NOT mean your write
failed — verify once the service is back.

## Tooling / known-good

See:
- `scripts/agent-sign.py` — the canonical Flop Labs signer (from
  `flop-labs/agent network-chat`, run with `uv run`).
- `references/agent-onboard.md` — the 2026-08-24 the ecosystem token/agent network onboard walkthrough
  with exact commands, URLs, the produced DID, and seed-path.
- `references/multi-agent-agent-onboard.md` — the 3-agent (Hermes/Claude/Codex)
  2026-08-24 run: all DIDs + seeds, per-agent registry keys, nonce/verify
  commands, and the outage gotchas.
