# monitor + alerts module architecture (established 2026-08-13)

Two new dirs built as pure-logic, provider-injected modules with no crypto/network deps.

## src/lib/monitor/

### challenge.ts — AP-01 (signature auth challenge)
- `buildAuthChallenge(input)` -> `{ challenge, message }`. `message` is the canonical
  signable string: `JSON.stringify([domain, uri, chain, account, nonce, issuedAt, expiresAt])`.
- `canonicalChallengeMessage(challenge)` — the deterministic serialization; tampering any
  field changes the message, so recovery of a tampered challenge yields a different address.
- `verifyChallenge({ signature, challenge, recoverAddress, expectedDomain, nowMs?, used })`
  -> `{ ok:true, account } | { ok:false, reason: "malformed"|"wrong-domain"|"expired"|"replayed"|"wrong-account" }`.
  Order matters: malformed -> wrong-domain -> expired -> replayed -> recover+compare.
  Nonce is consumed ONLY on success (`used.add`) so a failed verify doesn't burn the nonce.
- Injectable `RecoverAddress = (message, signature) => string | Promise<string>` (async seam —
  viem's recovery primitives are async). `verifyChallenge` returns
  `Promise<VerifyChallengeResult>`. `NonceStore = { has, add }`.

### recover.ts — AP-01 production provider (real secp256k1)
- `recoverAddress(message, signature): Promise<string>` — the real EIP-191 recovery, built on
  viem's `recoverMessageAddress`; this is the production impl passed into `verifyChallenge`'s
  `recoverAddress` seam. `verifyMessageSignature(address, message, signature): Promise<boolean>`
  wraps viem's `verifyMessage`.
- viem v2.x API (verified against node_modules, not training data): `recoverMessageAddress` /
  `verifyMessage` are async top-level `viem` utilities (NOT client actions); `privateKeyToAccount`
  is from `viem/accounts`. Recovery round-trips because both `signMessage` and
  `recoverMessageAddress` apply the EIP-191 personal-sign prefix.

### monitors.ts — AP-02/03/04/08 (wallet monitor CRUD + limits + identity + sessions)
- `MonitoredWallet { id, chain, address, label, settings, createdAt, updatedAt }`.
  `id` is a monotonic `m1`, `m2`, ... (NOT derived from chain+address, so `edit` can change chain).
- `WalletSettings { categories: string[], threshold: string | null }` — threshold is integer base-unit.
- Pure fns: `createEmptyMonitorState`, `listMonitors`, `getMonitor`, `addMonitor`, `editMonitor`,
  `removeMonitor` — all return `{ result, state }` with immutable state.
- `MAX_MONITORS_PER_OWNER = 100`. 101st add -> code `"limit-reached"` (state unchanged); delete frees a slot.
- Multi-chain identity: `(chain, address)` unique per owner; same hex on ethereum + robinhood are
  distinct. Malformed address / unsupported chain -> `"invalid"`; same-chain dup -> `"duplicate"`.
- `createMonitorRepository()` — owner-scoped in-memory store. Security posture: cross-owner read of
  an id returns `"not-found"` (identical to a missing id, so existence is not inferable);
  unauthenticated (null/empty account) -> `"forbidden"` (403).
- `createSessionRegistry()` — `{ issue, authenticate, revoke, revokeAll }`. AP-08: `revoke` makes
  `authenticate(token)` return null immediately; re-issuing a new token for the same account still
  sees the same repository data (monitors are keyed by account, not session).

### history.ts — AP-06 (alert history)
- `AlertHistoryEntry { id, category, subject, triggerValue, channel, result, dedupeKey, deliveredAt, read }`.
  `result: "delivered" | "failed" | "suppressed"`.
- `appendAlertHistory` -> `{ entry, state }`; `markAlertHistoryRead`; `listAlertHistory(state, order)`
  with `"oldest-first" | "newest-first"`.
- `serializeAlertHistory` / `deserializeAlertHistory` round-trip losslessly (deserialize validates shape).

### activity.ts — AP-05 (join activity to monitored addresses)
- `joinWalletActivity({ monitored, mints?, sales?, transfers? })` -> `WalletActivityEvent[]`.
  `direction: "incoming" | "outgoing" | "mint" | "sale"`. Only canonical events whose
  counterparty (minter, seller/buyer, from/to) matches a monitored `(chain, address)` are
  returned; unrelated addresses and non-canonical events are excluded. A monitored seller AND
  buyer on the same sale each emit their own event (same id, different address). Result is
  sorted by observedAt then id (deterministic). Addresses are normalized before matching;
  malformed monitored/activity address or unsupported chain throws `Error`.

### background.ts — AP-07 (background tracking semantics)
- `evaluateBackgroundTracking({ scope, authenticated })` -> `{ mode, persistsAfterBrowserClose, reason }`.
  `scope: "worker" | "local"`. worker -> `mode:"background"` (persists after browser close);
  local + unauthenticated -> `mode:"non-background"`; local + authenticated -> background.
  Unknown scope throws. `isBackground(mode)` helper.

## src/lib/alerts/

### categories.ts — AP-10/11 (six categories + enablement)
- `ALERT_CATEGORIES = ["new-upcoming","ten-minutes-before","live","trending-threshold","runner-sales-threshold","tracked-wallet-activity"]` (`as const`).
- `isAlertCategory` type-guard; `createDefaultCategoryPolicy()` (all enabled); `setCategoryEnabled`
  (immutable, records `{ category, action, changedAt }` to `history`); `evaluateCategoryDelivery`
  -> `{ deliver, reason: "enabled"|"disabled" }`. Disabled => zero deliveries, policy-history only.

### config.ts — AP-12 (threshold config)
- `THRESHOLD_METRICS` + `THRESHOLD_WINDOWS` (`1m/5m/15m/1h/24h`) as const unions.
- `validateThresholdConfig({ metric?, window?, value?, cooldown? })` -> `{ ok:true, config } | { ok:false, errors }`.
  Rejects negative/NaN/decimal value (regex `/^\d+$/`), wrong window, bad cooldown (must be finite
  non-negative integer). Aggregates ALL field errors in one pass.

### dedupe.ts — AP-18 (delivery dedupe)
- `buildDedupeKey({ category, subject, triggerValue })` = fields joined with `\u0000` — stable across
  retries (never derived from attempt number).
- `noteDeliveryAttempt` (increments attempts, updates lastAttemptAt), `markDelivered`,
  `shouldDeliver` -> `{ deliver, reason: "ok"|"already-delivered" }`. Attempt audit survives delivery.

### retry.ts — AP-19 (capped backoff / no infinite retry)
- `computeBackoffDelay(attempt, config)` = `min(base * 2^(attempt-1), maxDelayMs)`.
  `DEFAULT_RETRY_CONFIG { baseDelayMs:1000, maxDelayMs:60000, maxAttempts:5 }`.
- `scheduleRetry({ state, key, nowMs, error, config? })` -> `{ state, outcome: "scheduled"|"permanent"|"max-attempts" }`.
  Permanent error or attempts > maxAttempts cancels the schedule. Re-scheduling a key REPLACES the
  prior schedule (obsolete schedule cancelled). `cancelRetry`, `isRetryDue`. Fake clock via `nowMs`.

### sound.ts — AP-13/14/15 (sound presets / volume / preview)
- `DEFAULT_CATEGORY_SOUNDS` per-category `SoundPreset` (`chime|ping|pop|alert|none`).
- `clampVolume` (clamps to [0,1], NaN -> 0); `setSoundVolume` clamps on set.
- `setCategorySound` overrides a preset immutably; `soundPresetForCategory` reads it.
- `previewSound(settings, category, play)` — calls injected `play(preset, volume)` EXACTLY once,
  never produces a delivery or history entry (structurally can't: only takes settings + player).

### preferences.ts — AP-20 (versioned local preference store + migration)
- `AlertPreferences { version, chain, filters, windows, sort, volumeUnit, language, sound, volume, blockedProjects }`.
  `CURRENT_PREFERENCES_VERSION = 2`. `migratePreferences(raw)` validates each known key
  INDEPENDENTLY: valid keys preserved, invalid keys reset to default AND recorded in
  `resetKeys`; unknown/secret keys dropped. `volume` clamps to [0,1] (NaN/non-number resets).
- `serializePreferences` / `deserializePreferences` emit only known keys — secrets never persist.

### notification.ts — AP-17 (notification permission state machine)
- `readNotificationPermission(provider)` never calls `provider.request()` (no prompt on load).
  `requestNotificationPermission({ state, provider, userGesture })` -> outcome
  `"requested" | "blocked-no-gesture" | "already-decided"`. Only requests on an explicit gesture
  while in `default`; never re-prompts an already-decided state. `notificationStatus(state)`
  maps `default/denied/granted` to distinct statuses `not-enabled/blocked/enabled`.

### telegram.ts — AP-16 (encrypted credential, injectable cipher)
- `setTelegramDestination({ state, chatId, token, encrypt, configuredAt })` encrypts the token
  and returns only a non-secret `TelegramDestinationView`; `telegramDestinationView` never
  carries the secret. `verifyTelegramDestination({ state, decrypt, verifiedAt })` is the explicit
  action that decrypts but returns only `{ state, ok }`. `removeTelegramDestination()` discards
  the credential. `Cipher = { encrypt, decrypt }` injected — no crypto imports.

## AP acceptance-point map
| AP | File | Concern |
|----|------|---------|
| 01 | monitor/challenge.ts + monitor/recover.ts | signature auth challenge (single-use, replay/expiry/domain/account/tamper; real secp256k1 via viem) |
| 02 | monitor/monitors.ts | monitor CRUD (add/edit label+chain+settings/list/remove) |
| 03 | monitor/monitors.ts | 100-wallet limit (stable code, delete frees slot) |
| 04 | monitor/monitors.ts | multi-chain identity + malformed/wrong-chain rejection |
| 05 | monitor/activity.ts | join mint/sale/transfer activity to monitored addresses (direction + chain) |
| 06 | monitor/history.ts | alert history (round-trip + ordering) |
| 07 | monitor/background.ts | background tracking (worker-scoped vs unauthenticated local-only) |
| 08 | monitor/monitors.ts | session revocation (revoke immediate; re-auth sees prior data) |
| 10 | alerts/categories.ts | six alert categories (typed) |
| 11 | alerts/categories.ts | category enable/disable |
| 12 | alerts/config.ts | threshold config validation |
| 13 | alerts/sound.ts | per-category sound preset |
| 14 | alerts/sound.ts | volume clamp |
| 15 | alerts/sound.ts | preview (one audio call, zero deliveries/history) |
| 16 | alerts/telegram.ts | encrypted credential (injectable cipher; secret never leaves the view) |
| 17 | alerts/notification.ts | notification permission state machine (gesture-gated request) |
| 18 | alerts/dedupe.ts | delivery dedupe |
| 19 | alerts/retry.ts | retry + cleanup |
| 20 | alerts/preferences.ts | versioned prefs + per-key migration (drops secrets) |
| DS-18 | app/api/status/route.ts | per-chain status observability (injectable StatusRepository) |
