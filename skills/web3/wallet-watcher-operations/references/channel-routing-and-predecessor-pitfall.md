# Channel routing + predecessor pitfall (2026-09-01)

## What happened
- Request: `add 0x97C87D4352a6058232eE94dd0258Def30d6959B7 as safz` intended for `#👣tracker` (`1542733535717363763`).
- Agent executed `POST /api/wallets` against `https://wallet-radar-rh-alpha.vercel.app` (predecessor `~/Projects/wallet-radar` with Upstash Redis).
- API returned `{"ok":true}` with 5 wallets — looked verified, so agent reported success.
- User correction: "wrong project, this is for <#1542733535717363763>" — that channel is fed ONLY by `wallet-radar-rebuild`, not the Vercel app.

## Correct routing
| Channel | Project that feeds it | Config source | How to add |
|---|---|---|---|
| `#👣tracker` `1542733535717363763` (Tools) | `~/Projects/wallet-radar-rebuild` (launchd daemon `com.hermes.wallet-radar`) | `app/data/wallet_radar_entities.json` + `EXPECTED_ENTITIES` in `app/backend/services/wallet_radar.py` | Edit BOTH JSON and python, then `launchctl kickstart -k gui/$(id -u)/com.hermes.wallet-radar`, verify via `validate_entity_config` + `sqlite3 data/wallet_radar.db` |
| `mod-only/wallet-tracker` `1224746301099610302` | (separate, bot lacks VIEW_CHANNEL) | Do not assume — ask/audit | — |
| `~/Projects/wallet-radar` / `wallet-radar-rh-alpha.vercel.app` | Predecessor dashboard (archived) | Upstash `wr:wallets` | POST `/api/wallets` — does NOT affect `#👣tracker` |

## Guardrail for future sessions
1. Before any wallet add, `skill_view(wallet-watcher-operations)` and check "Where things live — READ THIS FIRST".
2. Never treat a 200 from `wallet-radar-rh-alpha.vercel.app` as proof for `#👣tracker`. Verify in the rebuild: `cat app/data/wallet_radar_entities.json` and `sqlite3 data/wallet_radar.db "SELECT ... FROM watchlist"`.
3. If a misroute already happened, revert: `DELETE` from the predecessor API AND add correctly to rebuild (or vice versa) — don't leave a ghost entry.
4. Acknowledge wallets tersely, but route-check trumps terseness when the channel context is ambiguous.

## Fix still pending as of skill write (2026-09-01)
- `safz` (`0x97c87d4352a6058232ee94dd0258def30d6959b7`) remains only in predecessor Upstash; needs correct addition to `wallet-radar-rebuild` via entity config (id `safz`, label `safz`, family `evm`) + EXPECTED_ENTITIES update + daemon restart. Remove from predecessor with `curl -X DELETE` if cleanup desired.
