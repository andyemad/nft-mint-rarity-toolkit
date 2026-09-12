# Alpha-group acquisition-source split (mint vs secondary buy) — 2026-08-24

Emad: "i need this to start distinguishing between minting (paid and free) and
buying on secondary." Complete fix for the alpha-group ("funkari buying (N/M)")
signal. Feature staged; NOT yet migrated/deployed (needs approval).

## The defect class
The alpha-group count (`/alpha-groups` route + the `alpha-group-buying` webhook,
both via `D1CanonicalRepository.getAlphaGroupActivity`) is
`COUNT(DISTINCT wallet)` where `wallet_positions.last_acquired_at >= since`.
`last_acquired_at` is updated by **BOTH** a mint event (`kind:"mint"` from
`mintEvents`) and a secondary purchase (`kind:"buy"` from `saleEvents`) — see
`src/lib/wallets/ledger.ts` `applyWalletEvents`. So a FREE mint labelled "X
members buying": the same false-fire class as the Rekt Tradoor `(50/50)`
incident documented in START-HERE.md §9. The threshold was CALIBRATED on total
acquisitions, so firing must keep reading `last_acquired_at` — only the REPORT
splits by source.

## The fix (all files staged)
1. **Migration `0018_wallet_acquire_source.sql`** — three nullable per-position
   source timestamps on `wallet_positions`: `last_mint_paid_at`,
   `last_mint_free_at`, `last_secondary_at`. NULL = "never" (0 is a valid Unix
   second, must not mean never). Two indexes: mint-by-collection + secondary.
   `last_acquired_at` is left as the MAX over all sources (the firing statistic).
2. **`ledger.ts`** — `Position` gains `lastMintPaidAt?/lastMintFreeAt?/
   lastSecondaryAt?` + `stampAcquisitionSource(position, event)`:
   - kind `"mint"` → paid when `native>0 || usd>0`, else free
   - kind `"buy"`  → secondary
   - a wallet hitting multiple sources keeps independent stamps (counts in each
     bucket it belongs to).
3. **`d1-repository.ts`** — `loadWalletAggregates` SELECT + `commitWalletAggregates`
   INSERT/UPDATE carry the 3 columns (load: `== null ? undefined : Number`).
   `getAlphaGroupActivity` now returns `{members, minted, paidMint, freeMint,
   secondary}` via `SUM(CASE WHEN COALESCE(col,0)>=? THEN 1 ELSE 0 END)`.
   Bind order matters: 5× `sinceSeconds` for the CASEs, then `CHAIN_ID`, then
   `sinceSeconds` for the WHERE.
4. **`alpha-group.ts`** — `AlphaGroupSample` gains optional `minted/paidMint/
   freeMint/secondary`; `AlphaGroupAlert` carries them REQUIRED (default `?? 0`
   in `deriveAlphaGroupAlerts`). Firing still keys off `members`.
5. **Delivery + title** (`alpha-group-delivery.ts` + `mint-terminal.tsx`
   `alertTitle` — the SAME headline, so board and webhook cannot disagree):
   - `alphaAlertTitle`: split by source, first part carries the slug.
     - mixed:  `funkari minting (2/2) · buying on secondary (1/2)`
     - mints:  `funkari minting (2/2)`
     - sec.:   `funkari buying on secondary (3/2)`  ← must prepend slug
     - neither:  `funkari acquiring (3/2)`  (unreachable fallback)
   - `formatAlphaAlertMessage` adds body line `Minting: 1 paid · 1 free` ONLY
     when `freeMint > 0` (silent default: "paid" must not imply "free happened").
   - board momentum tag: `BUYING` → `MINTING · BUYING` / `MINTING` / `BUYING` /
     `ACQUIRING` based on the split.
6. **Worker route** `/alpha-groups` — `counted` rows carry the 4 split fields;
   `withoutUtilityCollections` (filter-only) and `partitionByDevFrontedRisk`
   (generic over `{chain,collection}`) both pass extra fields through unchanged.

## Emad's format decision (asked via clarify, he chose)
Source-aware HEADLINE first. "Keep 'X buying (N/M)' with a breakdown line below"
and "only flag when it changes meaning" were BOTH options Emad did not pick. Do
not regress to a single conflated `buying (N/M)`.

## Tests staged
- `ledger.test.ts`: paid-mint→lastMintPaidAt, free-mint→lastMintFreeAt,
  buy→lastSecondaryAt, multi-source independence (4 new).
- `alpha-group.test.ts`: split carried through derive; missing fields default 0.
- `alpha-group-delivery.test.ts`: 3 headline shapes + mint-detail body + omit
  when no free + never-empty. Fixture carries `minted:2,paidMint:1,freeMint:1,
  secondary:1`.
- Integration (real SQLite + all migrations) passes — proves 0018 is
  SQLite-valid as an `ALTER TABLE ADD COLUMN` on a STRICT table (it is).

## Gate + deploy path
`npx tsc --noEmit` clean; focused suites green. Full `npx vitest run` (~70s+) run
in background; two visible FAILs (`ledger.integration.test.ts` round-trip,
`wire-runtime-repositories.test.ts`) are the KNOWN full-suite flake (see
SKILL.md — SQLite-subprocess constraint-stepping races; rerun green). Confirm an
A/B baseline (whichever failures reproduce before my diff) before blaming the
change. Deploy = `wrangler d1 migrations apply` + `wrangler deploy`, both
external consequences → approval first.
