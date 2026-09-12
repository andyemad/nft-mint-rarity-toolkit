# Entity config schema + exact-match guardrail

## Config file (`app/data/wallet_radar_entities.json`)

Source of truth for the watchlist. Schema:
```json
{
  "entities": [
    {"id": "czar", "label": "czar", "wallets": [
      {"chain_family": "evm", "address": "0x..."}
    ]},
    {"id": "vanta", "label": "vanta", "wallets": [
      {"chain_family": "evm", "address": "0x..."},
      {"chain_family": "solana", "address": "<base58>"}
    ]}
  ],
  "evm_chains": ["ethereum", "robinhood"],
  "solana_cluster": "mainnet-beta",
  "delivery": {"enabled": false, "discord_channel_id": "1542733535717363763"}
}
```
- `chain_family` is `evm` or `solana` only.
- EVM addresses are lowercased by `normalize_address`.
- The delivery block is the pinned channel; `enabled` MUST stay `false` in the
  file — delivery is armed ONLY by `--enable-delivery` + the webhook env var.

## Exact-match comparison (`validate_entity_config`, `exact=True`)
`from_paths()` in `wallet_radar_daemon.py` calls
`validate_entity_config(json.loads(...))` — which defaults to `exact=True`. It
builds `{entity_id: (label, tuple((family, address) for each wallet))}` and
compares it to `EXPECTED_ENTITIES` in `services/wallet_radar.py`. It ALSO
asserts:
- `evm_chains == ["ethereum", "robinhood"]`
- `solana_cluster == "mainnet-beta"`
- `delivery.enabled is False`
- `delivery.discord_channel_id == "1542733535717363763"`

So editing ONLY the JSON makes the daemon throw ValueError on startup.
Update both the JSON and `EXPECTED_ENTITIES` together. `UnifiedWalletWatcher`
`__init__` re-validates with `exact=False` (already normalized by then), so the
strict check happens only at load time in `from_paths`.

## `EXPECTED_ENTITIES` entry shape
```python
"safz": ("safz", (("evm", "0x97c87d4352a6058232ee94dd0258def30d6959b7"),)),
"anonymoux": ("anonymoux", (("evm", "0xbec69dfce4c1fa8b7843fee1ca85788d84a86b06"),)),
# key = entity id; value = (label, tuple of (family, address) tuples)
# Live as of 2026-09-01: 10 entities (czar, gmoney, vanta, tma, degen-1..4, aldan, anonymoux, safz) — 18 wallets total (17 EVM + 1 solana)
```

## Overlap note
`~/Projects/wallet-radar` (Next.js + Upstash) is a predecessor dashboard; its
`src/lib/default-wallets.ts` / `/api/wallets` POST is a DIFFERENT older config
tracked in Upstash Redis. The active system under Emad is
`~/Projects/wallet-radar-rebuild` with the launchd daemon. Don't edit the old
one unless asked.
