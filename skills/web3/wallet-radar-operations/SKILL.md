---
name: wallet-radar-operations
description: Use when operating, debugging, or changing Wallet Radar wallets, classifiers, alerts, valuation, delivery, or its live daemon.
---

# Wallet Radar Operations

Emad runs a live wallet-monitoring tracker ("Wallet Radar") that watches a set
of wallets and posts NFT mint/buy + shitcoin/token-buy alerts to the Calm
Discord **#👣tracker** channel (id `1542733535717363763`, guild
`967228425112813629`). This skill covers ADDING / REMOVING wallets and
restarting the daemon.

## Where things live — READ THIS FIRST (session 2026-09-01 pitfall)
> **2026-09-01 misroute:** an add was executed against the predecessor
> `~/Projects/wallet-radar` via `POST https://wallet-radar-rh-alpha.vercel.app/api/wallets`
> — it returned 200 and looked successful, but it does NOT feed `#👣tracker`.
> The **only** system that posts to `#👣tracker` (`1542733535717363763`) is
> `~/Projects/wallet-radar-rebuild` via its launchd daemon. Treat the Vercel
> predecessor as archived — never use its API for tracker adds unless Emad
> explicitly asks for the old dashboard.

- Active system: `~/Projects/wallet-radar-rebuild` (NOT the older Next.js
  `~/Projects/wallet-radar`, which is a predecessor dashboard).
- Config source of truth: `app/data/wallet_radar_entities.json` — an entity
  model. Each wallet belongs to an entity `{id, label, color, wallets:[{chain_family,
  address}]}`. `color` is an uppercase six-digit RGB hex string, must be unique
  across entities, and is rendered as the Discord embed color. Allocate an unused
  color whenever a new entity is approved; a new wallet added to an existing entity
  retains that entity's color.
- Daemon: launchd job `com.hermes.wallet-radar` (KEEPALIVE) → runs
  `app/scripts/run_wallet_radar_loop.sh`, which sources secrets and launches
  `wallet_radar_daemon.py loop --config data/wallet_radar_entities.json --db
  data/wallet_radar.db --lock data/wallet_radar.lock --poll-interval 15
  --enable-delivery`.
- Secrets (sourced by the run script): `~/.hermes/secrets/
  wallet_radar_discord_webhook_url` and `~/.hermes/secrets/opensea_key`.

## CRITICAL guardrail — always update BOTH
`from_paths()` in `app/backend/services/wallet_radar_daemon.py` loads the entity
config with `validate_entity_config(..., exact=True)` (the DEFAULT). That
requires the JSON to EXACTLY match `EXPECTED_ENTITIES` in
`app/backend/services/wallet_radar.py`. If you edit only the JSON, the daemon
crashes on restart with a ValueError. So when adding a wallet:
1. Edit `wallet_radar_entities.json` (add the entity).
2. Edit `EXPECTED_ENTITIES` in `wallet_radar.py` (add the matching entry).
3. Restart the daemon (see below).

An EVM wallet entry is monitored on **both Ethereum and Robinhood**; do not describe
that as two separately added wallets. Solana is also supported, but it requires a
separate `chain_family: "solana"` address because an EVM address cannot identify a
Solana account.

The exact match also pins `evm_chains == ["ethereum","robinhood"]`,
`solana_cluster == "mainnet-beta"`, `delivery.enabled == false`, and
`delivery.discord_channel_id` — leave those untouched. Delivery is armed ONLY
by the `--enable-delivery` CLI flag + webhook env var, never by the config file.

## Add a wallet (step by step)
1. Back up `app/data/wallet_radar_entities.json` and
   `app/backend/services/wallet_radar.py` (e.g. `cp ... /tmp/...bak.$(date +%s)`).
2. Add the entity to the JSON (append before the `]` of the entities array):
   ```json
   {"id": "anonymoux", "label": "anonymoux", "color": "2D9CDB",
    "wallets": [{"chain_family": "evm", "address": "0x..."}]}
   ```
   Pick a color not already assigned to any entity.
3. Add the matching entry to `EXPECTED_ENTITIES` in `wallet_radar.py`:
   ```python
   "anonymoux": ("anonymoux", "2D9CDB", (("evm", "0x..."),)), 
   ```
4. Restart: `launchctl kickstart -k gui/$(id -u)/com.hermes.wallet-radar`
   (KeepAlive respawns it; do NOT kill the pid by hand — let launchd manage
   it). This is the wallet-radar daemon, safe to restart. NEVER restart the
   Hermes gateway. If Hermes' in-process command guard mistakes this
   `com.hermes.*` LaunchAgent for the gateway, execute the same `launchctl`
   command from a separate Terminal `.command` file, then verify from the
   lock file, `ps`, and SQLite; do not weaken or bypass the guard.
5. Verify **ingestion and delivery separately**:
   - Exact-validate the config:
     `cd app && .venv/bin/python -c "import json,sys;sys.path.insert(0,'backend');from services.wallet_radar import validate_entity_config;validate_entity_config(json.load(open('data/wallet_radar_entities.json')))"`
   - DB watchlist active: `sqlite3 data/wallet_radar.db "SELECT
     address,label,active FROM watchlist WHERE address='<lowercase addr>';"`
   - Runtime list regenerated in `data/wallet_radar.wallets.json` (from_paths
     writes it from the entity config on startup).
   - Confirm the PID is stable and each configured chain's cursor advances on
     **two reads**. A running PID plus one fresh cursor timestamp proves only that
     the loop started; it does not prove continued scanning.
   - Inspect `alert_outbox` grouped by status and compare latest `delivered_at`
     against recent `entity_alerts.timestamp`. **Never call Wallet Radar working or
     verified from PID/watchlist/cursors alone.** Delivery is verified only by a
     successful new outbox row (`status='delivered'`) and authoritative readback of
     the actual Discord message. If no organic event occurs, propose one clearly
     labeled test message and wait for approval before sending it.
   - A wallet-add test suite validates configuration, not live delivery. Report
     those scopes separately rather than saying broadly that “the tracker is
     verified.”

See `references/entity-config-and-guardrail.md` for the exact-match comparison
and the full config schema. See `references/channel-routing-and-predecessor-pitfall.md` for the 2026-09-01 misroute — why `wallet-radar-rh-alpha.vercel.app` does NOT feed `#👣tracker` and how to verify the correct rebuild.

## Alerts, purchase semantics, and valuation
Alerts are formatted by `format_discord_message()` in
`app/backend/services/wallet_radar_alerts.py`; receipt classification lives in
`app/backend/services/wallet_radar.py`. Webhook payloads include a one-color
Discord embed for the entity. Keep transaction URLs compact in user-facing
messages: use Markdown links (`Tx: [Tx](url)`, or numbered Tx links for a batch),
not exposed raw explorer URLs.

**Every NFT mint alert must carry an OpenSea link.** Prefer the verified
collection page when token-level enrichment resolves a slug. If enrichment is
not ready yet, link the exact item instead:
`https://opensea.io/item/{opensea_chain}/{contract}/{token_id}` (Robinhood uses
`robinhood-chain`; Ethereum uses `ethereum`). Do not fall back to a transaction-only
mint alert when contract and token ID are known. NFT buys may still use the
transaction fallback when safe collection attribution is unavailable.

**Every NFT alert with an OpenSea link must also carry its transaction link.**
Use `Tx: [Tx](...)` for a single transaction and numbered links for a batch
(up to three, then `+N more`). If the primary fallback is already the transaction,
do not duplicate it. This lets the channel show both the marketplace destination
and receipt-level evidence instead of forcing the user to choose between them.

### Mint versus proxy-mint semantics
The production receipt classifier calls an NFT a real mint only when the transfer
into the watched wallet is directly from the zero address. A route such as
`zero address -> intermediary/proxy -> watched wallet` is **not** explicitly
classified as a proxy mint and must not be described as though the tracker has a
separate proxy-mint label. Today, the final proxy-to-wallet transfer is suppressed
unless verified marketplace fill plus payment evidence makes it an NFT buy.
When asked whether proxy mints are distinguished, answer precisely: direct mints
are recognized; most proxy-forwarded mints are prevented from being mislabeled as
real mints, but they are filtered rather than surfaced as their own category.
Add a dedicated proxy-mint category only from full receipt path evidence, with
regression fixtures for direct mint, proxy-forwarded mint, marketplace buy, and
ordinary transfer.

**Resolve OpenSea collections by `(chain, contract, token_id)`, never by contract alone.**
Shared ERC-721 contracts such as Art Blocks host multiple OpenSea collections;
contract-only resolution can label a real purchase as the wrong project. Use
OpenSea's `/api/v2/chain/{chain}/contract/{contract}/nfts/{token_id}` response
and read `nft.collection`. Cache by all three values. Keep contract lookup only
as a fallback for legacy events without a token ID. Regression coverage must
include two token IDs from different collections on the same contract.

**Do not equate the wallet's final inbound ERC-20 transfer with the amount
bought.** Routers, vaults, strategy contracts, and games may acquire tokens
internally, consume most of them, and return only a remainder to the wallet.
For a trusted protocol event that explicitly reports the purchased amount,
decode that semantic field and let it override the transfer-derived quantity
only under tightly verified conditions: exact event signature, chain, token
contract, and purchaser/holder topic. Never apply an observed multiplier to
other transactions.

Token-buy alerts value the semantic purchased quantity using Dexscreener price
and on-chain decimals. NFT sweeps with fully attributable settlement now show
total ETH, approximate total USD using the wrapped-native quote, and ETH/NFT;
omit unsafe totals/averages for partial or multi-collection attribution. For
Seaport, decode the real `OrderFulfilled` ABI layout and consideration rather
than assuming gross `tx.value`, because excess native value may be refunded.

### Shared-contract NFT collections
Never resolve an OpenSea collection slug from the NFT contract alone. Art Blocks
and other shared ERC-721 contracts host multiple projects under one address, so
a contract-level lookup can return a valid but unrelated collection. Resolve the
slug using `(chain, contract, token_id)` from OpenSea's NFT/event data. For a
sweep, verify every purchased token resolves to the same project before emitting
one collection link; if projects differ or token-level resolution fails, omit the
collection slug or link individual assets rather than guessing.

When a user reports that an alert's purchase is absent from the linked OpenSea
page, independently verify two questions:
1. **Was it a purchase?** Read the transaction and receipt: successful status,
   buyer-funded marketplace call, settlement value, and ERC-721 transfers from
   sellers to the watched wallet.
2. **Which project was purchased?** Query OpenSea account sale events for the
   exact transaction hash and inspect each event's token-level `nft.collection`.

A correct purchase count/value with the wrong project link is a resolver bug,
not a false purchase classification. See
`references/shared-contract-collection-resolution.md` for a verified Art Blocks
case and compact reproduction checklist.

Every production correction needs a real transaction fixture that fails before
the fix, the focused Wallet Radar suite, lint/compile/diff checks, activation,
and authoritative readback of both the daemon and any edited Discord message.
Previously delivered alerts are not corrected by a daemon restart; edit them
separately only with approval. Likewise, never bulk-reset `dead` outbox rows after
an outage: that can flood the channel with stale alerts. Keep the backlog dead
until Emad explicitly approves a bounded replay policy.

For the 2026-09-05 outage pattern—uint256-to-SQLite overflow crash loops, invalid
color-only Discord embeds, outbox diagnosis, and the required end-to-end recovery
gate—read `references/outage-diagnosis-and-delivery-verification.md`.

See:
- `references/alert-message-building-and-usd-enrichment.md` for quote enrichment.
- `references/alert-avg-eth-payment-attribution.md` for settlement attribution.
- `references/purchase-semantics-and-alert-corrections.md` for protocol-event overrides, production-message correction, and activation verification.

`test_exact_entity_config_contract` now expects the live 16-entity intake
(czar, gmoney, vanta, reaper, tma, degen-1..4—with `degen-4` labeled aldan—,
anonymoux, safz, barry, qwerty, otto, pransky, cole). It contains 23 wallet
entries: 22 EVM and 1 Solana. `scripts/check_wallets.py` pins the same totals
and must also be updated whenever the intake grows. Update all counts whenever
`EXPECTED_ENTITIES` grows.

Known pre-existing (NOT caused by any add): the WALLET leak-check test
`test_real_repo_tree_is_clean` fails because the repo has no .git so the
scanner falls back to a full tree scan that flags ~87 wallet/contract
constants in wallet_radar.py, the entities JSON, and test files that were
never added to sec/wallet_allowlist.txt. It fails identically with or
without a new wallet and is a MEDIUM warn — do not treat it as a regression
of a wallet add, and don't re-baseline WALLET-* findings away.

## Diagnostics

### Silence versus a real outage
A quiet Discord channel is not proof the tracker is broken. Use this evidence
ladder before restarting or changing code:
1. Read launchd state/PID and verify both chain cursors advance across two reads.
2. Compare each cursor with a live `eth_blockNumber` head; quantify lag.
3. Group `alert_outbox` by status and inspect the latest delivery timestamp/error.
4. Read back the latest actual Discord webhook message; DB `delivered` alone is
   not authoritative channel proof.
5. Audit watched-wallet activity since the last alert and separate qualifying
   inbound NFT mints/marketplace buys/token buys from intentionally excluded
   actions (outgoing NFT transfers, approvals, burns, game calls, plain receives).

When Emad says he “doesn't see anything” or “there are no transactions since
6-something,” interpret that first as a **timestamp/freshness complaint**, not as
a rendering complaint. State the timestamp of the newest qualifying alert and
check whether any later qualifying activity exists. Do not jump to changing
message formatting or proposing a test post unless he explicitly says existing
messages are blank/invisible. Discord `fetch_messages` may return `content: ""`
for webhook posts whose text lives entirely in an embed; that tool representation
does not prove the Discord client hid the message. Cross-check the message ID,
timestamp, author, and stored webhook payload before diagnosing embed visibility.

Do not promise a fix until the audit proves a failure. If cursors are current,
outbox has no failed/dead rows, Discord readback matches, and there are no
classifier-qualified events, report that the tracker is healthy and explain the
specific observed actions that were excluded. Robinscan
`/api/addresses/{wallet}/txs` plus `/api/txs/{hash}` is useful for auditing
wallet-submitted transactions and embedded `tokenTransfers`, but it is not an
exhaustive substitute for transfer-topic `eth_getLogs`: relayer-submitted inbound
transfers may not have the wallet as outer transaction sender/recipient. See
`references/silence-vs-outage-diagnosis.md` for the bounded audit recipe.

- `Wallet Radar RPC failed for <chain>/...: HTTPStatusError` may be a transient
  provider throttle, but **do not blindly ignore it** and do not assume another
  chain is unaffected. Compare each chain's cursor to its live head twice. Repeated
  failures plus a non-advancing cursor are an outage even when launchd shows a PID.
- Robinhood RPC is configured for per-request failover in `ChainConfig` and
  `WalletRadarService.rpc()`: `https://rpc.ordofi.network` is primary and the
  official `https://rpc.mainnet.chain.robinhood.com` endpoint is secondary.
  Each endpoint is tried before consuming another bounded retry. When changing
  providers, verify `eth_chainId == 0x1237`, a representative addressless
  `eth_getLogs` filter, fresh heads, and two advancing SQLite cursor reads; a
  successful `eth_blockNumber` alone is insufficient for this scanner.
- See `references/rpc-failover-and-mint-links.md` for the validated probes,
  regression expectations, and activation checklist.
- Repeated `OverflowError: Python int too large to convert to SQLite INTEGER` in
  `process_evm_receipts` means a token quantity exceeded signed 64-bit SQLite.
  Persist uint256 quantities through `_quantity_to_db()` (hex TEXT above
  `2**63-1`) and decode through `_quantity_from_db()`; cover the receipt path with
  a regression fixture, not only the older transfer-log path.
- A valid webhook GET does **not** prove payload POSTs are valid. Discord rejects a
  color-only embed (`{"embeds":[{"color":...}]}`). Use an embed containing the
  message as `description` plus `color`, or send content without an embed. Check
  `alert_outbox.last_error/status` and `delivery_ledger`, and preserve the HTTP
  status/body in sanitized delivery diagnostics so a generic “Discord delivery
  failed” cannot hide a 400 validation error.
- Address must be a real `0x` + 40 hex (lowercase; `normalize_address`
  lowercases). Malformed address → 400/ValueError.
- Acknowledge incoming wallets tersely and execute the add without asking
  mid-collection questions.
