# Wallet Radar outage diagnosis and delivery verification

## 2026-09-05 incident signature

A launchd PID and an active DB watchlist looked healthy while the product was not
actually delivering alerts. Two independent failures were present:

1. **Scanner crash loop:** a fungible token purchase quantity exceeded SQLite's
   signed 64-bit INTEGER range. `process_evm_receipts()` inserted the raw uint256
   into `activities.quantity`, raising `OverflowError: Python int too large to
   convert to SQLite INTEGER`. Keep the schema compatible by writing values above
   `2**63-1` as hex TEXT via `_quantity_to_db()` and decoding with
   `_quantity_from_db()`. Exercise the receipt-classifier persistence path with a
   >64-bit regression value.
2. **Delivery rejection:** the last successful outbox payload had `content` only;
   every subsequent dead row had `content` plus a color-only embed. Discord webhook
   GET returned 200, but POST delivery failed because `{color}` alone is not a
   valid embed body. The valid color-coded shape is:

```json
{
  "embeds": [{"description": "<message>", "color": 5793266}],
  "allowed_mentions": {"parse": []}
}
```

The failed implementation stored only the generic text `Discord delivery failed`,
which hid the HTTP status/body. Delivery diagnostics should retain a sanitized
status and short response reason without ever logging the webhook URL/token.

## Fast evidence queries

Run these before claiming health:

```sql
SELECT chain, MIN(next_block), MAX(next_block),
       datetime(MIN(updated_at),'unixepoch','localtime'),
       datetime(MAX(updated_at),'unixepoch','localtime')
FROM cursors GROUP BY chain;

SELECT status, COUNT(*),
       datetime(MAX(COALESCE(delivered_at,available_at)),'unixepoch','localtime')
FROM alert_outbox GROUP BY status;

SELECT id, status, attempts, last_error, payload
FROM alert_outbox ORDER BY id DESC LIMIT 10;
```

Read cursors twice and compare them to live chain heads. Then compare the newest
`entity_alerts.timestamp` with the newest delivered outbox row. A new entity alert
with three failed attempts proves scanning works but Discord delivery does not.

## Recovery gate

1. Reproduce the exact failure with a focused test before changing production.
2. Fix one boundary at a time (DB encoding, then webhook payload validity).
3. Run the complete Wallet Radar unit suite.
4. Restart only `com.hermes.wallet-radar`.
5. Verify PID stability and cursor advancement on every configured chain.
6. Verify a **new** outbox row reaches `delivered` and read the actual Discord
   message back. If an organic event is unavailable, obtain approval for one labeled
   delivery test; never silently send it.
7. Do not reset or replay dead rows automatically. A backlog replay is a new batch
   of external messages and can spam the channel; require an explicit bounded
   approval.

## Reporting discipline

State scopes precisely:

- “Configuration verified” = JSON, exact entity contract, runtime list, watchlist.
- “Scanner verified” = chain cursors advance and a real event persists.
- “Delivery verified” = a new outbox row is delivered and Discord readback exists.
- “Tracker working” requires all three.

This distinction prevents a local process check from being reported as an
end-to-end success.
