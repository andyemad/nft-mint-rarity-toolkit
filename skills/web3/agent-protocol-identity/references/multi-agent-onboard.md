# Multi-agent the ecosystem token/the agent network onboard — 2026-08-24 walkthrough

Onboarded THREE agent DIDs to the @flop_labs the ecosystem token airdrop on `the public agent network`
(Hermes + Claude Code + Codex) so each counts as a separate allocation at the
Q4 snapshot. Exact record for reuse / debugging.

## The three DIDs + their seeds

| agent | did:key | registry key | seed file |
|---|---|---|---|
| Hermes | z6Mkj2xybrhtTCbStYAr8i6kG6KZYb6PPodKADK78AvCDZi2 | `/kv/did/agent-a` | `~/.hermes/secrets/agent_seed` |
| Claude | z6Mkwb9avpsf5TNGH6PP6W49PLU7RciUVusWEaHtccpDi2DV | `/kv/did/agent-b` | `~/.hermes/secrets/flop_claude_seed` |
| Codex | z6MkmjVcKQdGvR2F7uaanQ3ZrVopaw7QJ4xS9t2TytQ6xTj4 | `/kv/did/agent-c` | `~/.hermes/secrets/flop_codex_seed` |

All seeds chmod 600, each re-derives to its exact DID (verified byte-exact).
Generated with `uv run sign.py keygen` (PEP-723 self-provisioned; installs
`cryptography` via uv). Project dir: `~/Projects/agent-public-identity/` with canonical
`sign.py` + onboard scripts + `onboard_retry.sh` / `codex_retry.sh` / `fun_content2.sh`.

## 4 steps per agent (with the actual commands)

1. Keygen:
   `uv run sign.py keygen` -> prints `seed:` (64 hex) and `did: did:key:z6Mk…`
2. Publish DID note (plain unsigned `set` lane — `set-signed` is restricted to
   room-owners/room-allow namespaces, so the `did` registry uses `set`):
   `GET https://the public agent network/kv/did/<name>/set/<percent-encoded did:key>`
   -> `ok did/<name> ….` + HTTP 200
3. Signed lobby check-in:
   `nonce=$(printf '%d' $(( $(python3 -c 'import time;print(int(time.time()*1000))') )))`
   `OUT=$(uv run sign.py say --seed "$SEED" lobby "$nonce" "<text>")`
   `SIG=$(echo "$OUT" | tail -1)`
   `GET https://the public agent network/r/lobby/say-signed/<did>/<SIG>/<nonce>/<url-encoded text>`
   -> 200 + message appears in `/r/lobby` under `<z6Mk…>` (verified writer), not `~nick`.
4. Secure seed: chmod 600; DO NOT delete (it's the Q4 claim key).

## Gotchas that cost time

- **nftstorage.link now 302s** (to ipfs.io which 403s from python) for rank/
  metadata fetching; gateway.pinata.cloud works but ~6s/req. Not used for the
  did:key work; only matters for the sibling rarity-sniper pipeline.
- The retries consumed real clock: the origin had ~40 min of hard outage
  (000/502/503) in one stretch, so foreground commands timed out. The resilient
  background loop (wait for 3× 200 on /healthz, run once, verify by room
  readback, exit) is the right shape — see SKILL.md "Flaky-origin + nonce-reuse".

## "Fun" posts made from Hermes DID

Lobby intro + an OpenRarity walkthrough (info-content rarity formula, no API
key) — safe public content, no wallets/positions/business. Rule that governed
this: agent network is PUBLIC + world-writable; never post wallets, holdings, P&L,
or business plans there. (Posts were stuck behind the same outage; keys were
never at risk.)
