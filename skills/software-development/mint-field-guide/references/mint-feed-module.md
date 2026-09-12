# New Mints feed — mint-feed.ts + /api/mints (DI-09..14)

Pure module `src/lib/indexer/mint-feed.ts` + route `src/app/api/mints/route.ts`, built
2026-08-13 as "New Mints feed" over canonical `MintFact[]`. No crypto/network deps.

## Acceptance-point map
| DI | Concern |
|----|---------|
| 09 | deterministic ordering: blockNumber desc → logIndex desc → chain → txHash → id |
| 10 | chain filter `all \| ethereum \| robinhood` (union under `all`, disjoint subsets, single-pass input = no refetch duplication) |
| 11 | free/paid filter via `classifyMintPrice(nativeValueWei)` only; `unknown` never silently included as free/paid |
| 12 | bounded batching: coalesce `(chain, collection, blockNumber, standard, priceClass)`, cap `MAX_MINT_BATCH_SIZE = 50`, preserve every fact id |
| 14 | dedup by `(chain, transactionHash, logIndex)`; canonical beats orphaned, then drop any remaining non-canonical → one current fact per reorg |

## Pipeline (in order)
dedupe → chain filter → classify + freePaid filter → sort → coalesce → offset-cursor paginate.

- Item shape `MintFeedItem { kind: "mint"|"batch", chain, collection, standard, priceClass, quantity, nativeValueWei, blockNumber, logIndex, observedAt, factIds }`.
- Batch representative fields: `logIndex`/`observedAt` = max within group; `quantity` = sum;
  `nativeValueWei` = safe BigInt sum (non-uint strings treated as 0 so a "null"/empty value can't throw).
- Cursor: base64url JSON `{ version, chain, freePaid, offset }`, version = `MINT_FEED_CURSOR_VERSION`.
  Decode mismatch on version or query params throws /match/i; out-of-range offset throws /offset/i —
  route maps those to 400 `INVALID_CURSOR`.
- Route: injectable `MintsReadRepository.getCanonicalMints(): Promise<MintFact[]>` (returns ALL chains once;
  chain filter is an in-memory subset). 400 `INVALID_REQUEST` on bad enum/limit, 503 `MINTS_UNAVAILABLE`
  on store/not-configured, `no-store` cache-control.

## Test pitfalls (hit and fixed this session)
- Same-collection facts coalesce under DI-12, so an ordering/tie-break test that reuses one collection
  silently collapses multiple facts into one batch and the assertion misleads. Give each fact a DISTINCT
  collection (or blockNumber) so they remain separate items.
- `0n` BigInt literal throws TS2737 (`target < ES2020`). Use `BigInt(0)` / `BigInt(value)` — all existing
  indexer modules use the constructor form.
