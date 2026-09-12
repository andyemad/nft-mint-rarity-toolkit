# HOOD MFERS (robinhood-mfers) reveal watch — 2026-08-23

Session-specific detail for the rhoodmfers reveal watcher. Facts verified
live 8/23; the collection was still pre-reveal at session end.

## Collection facts
- Name: HOOD MFERS, OpenSea slug `robinhood-mfers`
- Contract: `0xe27e38bb149674a568d16d04ce91b063b51c0eff` (Robinhood chain)
- Supply: 6969 (totalSupply on-chain; OpenSea total_supply says 6967 — trust chain)
- Pre-reveal URI shape: per-token paths under one base CID —
  `ipfs://QmNSUpFqwgkrsJdCG4EqhHvoWogQ4fcXpeRgKAUsiZm9rZ/<tokenId>`
  (NOT exact-shared like Clay StonKz). Reveal detection must use
  `uri.startswith(BASE + "/")`, not equality.

## Watcher
- Script: `~/.hermes/scripts/rhoodmfers_reveal_watch.py` (verified: silent
  tick pre-reveal, exit 0, no state file written until reveal).
- Cron job name: `rhoodmfers-reveal-watch`, every 4 min, deliver origin,
  no_agent. One-shot alert: prints "ROBINHOOD MFERS REVEALED" + top-20 ranks,
  iMessage backup to +1<operator-phone-redacted>, sets alerted state, silent forever after.
- On reveal it sweeps all 6969 tokenURIs (12 threads), fetches metadata via
  gateways in order `gateway.pinata.cloud` → `nftstorage.link` (pinata first
  per 8/22-8/23 gateway behavior), ranks by OpenRarity info-content
  (-log2(count/total)), and writes:
  - `~/.hermes/rarity/rhoodmfers/scores.json` (ranked list w/ trait breakdowns)
  - `~/.hermes/rarity/rhoodmfers/images.json` (tokenId → image URI for Mint Room /rarity)

## Approval note
The original "yes" for this cron died with a gateway crash mid-turn; the
concierge gate required re-proposal after recovery. Lesson: an approval spoken
before a crash is not consumable after it — re-propose verbatim rather than
executing on the old transcript.

## Update 2026-08-23 ~04:00
Cron `cafb9710f834` recreated as a NO-AGENT script job (the original agent-mode
job errored every tick on the provider messages[0].content bug). Runtime copy:
`~/.hermes/scripts/rhoodmfers_reveal_watch.py`; identical repo copy:
`~/Projects/rh-mint-command-center/scripts/rhoodmfers_reveal_watch.py`. Simplified contract vs earlier sweep
version: samples 8 tokenURIs, prints ONLY the single line "ROBINHOOD MFERS
REVEALED — open Mint Room /rarity and hit Scan" on divergence, then best-effort
`hermes cron disable/remove rhoodmfers-reveal-watch` + state-file one-shot
guard at ~/.hermes/cron/output/rhoodmfers_reveal_state.json. Rarity sweep/rank
on reveal is Mint Room /rarity Scan's job (per Emad's revised spec).
Pitfall: testing main() end-to-end WILL fire disable_cron_job() against the
live job — stub STATE_FILE AND the disable step in tests. (It actually fired
8/23 and removed cafb9710f834 mid-test; had to re-create it — see SKILL.md
"Arm watchers as NO-AGENT script jobs" section for the jobs.json restore path.)
