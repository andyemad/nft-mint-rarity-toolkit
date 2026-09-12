# Smart-wallet scoring v2 (shipped 2026-08-16)

Supersedes the Tier-1 ranking (`ORDER BY realized_native DESC` with min 4 matched
sells). That rule ranked a single lucky flip above a consistent trader and was
honestly labelled weak by Hermes before the redesign.

## Why v1 was weak (the analysis that drove the change)
1. 4 matched sells ≈ noise, not a track record.
2. Raw realized-profit sort → one lucky 10× flip outranks a wallet profitable on 50 trades.
3. Only ~48h of indexer history → fast flippers surface, patient holders invisible.
4. Unrealized losses invisible (a wallet +2 native realized holding −50 in bags still tops the board).
5. No wash-sale filter (not addressed in v2 — noted as future work).

## Formula
```
score = winRate × sqrt(matchedUnits) × sign(realizedNative) × log2(1 + |realizedNative|)
```
Computed in JS in `D1CanonicalRepository.getTopWalletsByRealized` (name kept from v1;
signature grew an optional `minTrackRecordSeconds = 0`):

1. SQL: `SELECT ... FROM wallet_ledger WHERE chain_id=? AND (sell_units - unmatched_sell_units) >= ? AND (last_seen_at - first_seen_at) >= ? ORDER BY realized_native DESC LIMIT limit*4`
2. Map to `{wallet, score, winRate, wins, losses, matchedSells, realizedNative, ...}`
3. Sort by score desc, slice to `limit`.

Why the pieces:
- **winRate**: consistency. `wins / (wins + losses)` over *decided* sell events.
- **√matchedSells**: track record length with diminishing returns (100 trades doesn't auto-beat 20 good ones).
- **sign(profit) × log2(1+|profit|)**: profit matters but log-damped so one huge flip can't dominate;
  a net-losing wallet scores below break-even regardless of gross volume.

## Qualification
- `SMART_WALLET_MIN_MATCHED_UNITS = 10` (was 4) — in `src/worker/index.ts`.
- `SMART_WALLET_MIN_TRACK_RECORD_SECONDS = 3600` (new) — span between `first_seen_at` and `last_seen_at`.
- Both routes (`/wallets`, `/smart-collections`) accept `?minMatched=` and `?minTrack=`; responses
  carry `minMatchedUnits` and `minTrackRecordSeconds` so consumers see the bar.
- `countQualifiedWallets` and `getSmartHoldingsByCollection` apply the same two filters.
  `getSmartHoldingsByCollection` keeps the curated-wallet bypass: `OR w.wallet IS NOT NULL`.

## Cold-start design (the subtle part)
Migration 0012 adds `wins`/`losses` columns DEFAULT 0. Every sell BEFORE the migration
has no win/loss split, so `wins + losses = 0` for the whole historical ledger. Two things
prevent a dead leaderboard:
- `matchedSells` = `sell_units - unmatched_sell_units` (already known for every wallet), NOT `wins + losses`.
- `winRate` = `wins / (wins + losses)` when decided > 0, else neutral `0.5`.

So immediately after deploy the ranking is profit-shaped (with 0.5 × √matched) and
sharpens into a consistency ranking as counters fill. Verified live: top wallet showed
winRate 1.00 with 1,398 matched sells within ~30 min of deploy because its new sells
counted immediately.

## Migration 0012 (`migrations/0012_wallet_score.sql`)
```sql
ALTER TABLE wallet_ledger ADD COLUMN wins INTEGER NOT NULL DEFAULT 0;
ALTER TABLE wallet_ledger ADD COLUMN losses INTEGER NOT NULL DEFAULT 0;
```

## Win/loss accounting in `src/lib/wallets/ledger.ts`
`applySell` computes `realizedNativeThisSell` per event; `> 0` → `wins++`, `< 0` →
`losses++`, `== 0` → neither. Counted per sell EVENT, not per unit (a 5-token sell in
one tx is one trade decision). Only *matched* sells (we held basis) can be a win/loss;
unmatched units bump `unmatchedSellUnits` only. `emptyTotals` and
`loadWalletAggregates` both carry the new fields (the SELECT must include `wins, losses`
or `Math.round(undefined)` → NaN → `non-finite SQLite number` in the test DB).

## Deploy sequence (verified 2026-08-16)
1. `npx wrangler d1 migrations apply mint-field-guide --remote` (0012 → ✅)
2. `npx vitest run` (854/854) + `npx tsc --noEmit`
3. `npx wrangler deploy --dry-run` gate, then `npx wrangler deploy`
4. Verify: `curl "https://mint-field-guide-indexer.mintfieldguide.workers.dev/wallets?chain=robinhood&limit=5"`
   — qualified wallets dropped 1,284 → 469 under the tighter bar.
5. Commit + push (`andyemad/mint-field-guide`, commit 14eb701).
