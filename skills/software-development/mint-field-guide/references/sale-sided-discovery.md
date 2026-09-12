# Sale-side ERC721 discovery leg (T3, DEPLOYED + verified live 2026-08-23)

## Why it exists
The mint scan only admits collections that MINTED inside its observable window.
A collection distributed before the cursor (e.g. RWAKERS) can trade heavily
forever and never appear — sales are only scanned for collections that already
carry a bucket row. The discovery leg is the sale-side door: one unfiltered
`eth_getLogs` sweep per chunk returns every contract that moved ANY ERC721
token in the range; the log's `address` field IS the collection.

## The three pieces
1. **RPC method** — `EvmRpcSource.getTransferContractAddresses(fromBlock, toBlock,
   chunkBlocks)` in `src/worker/rpc-source.ts`: unfiltered Transfer-topic getLogs,
   chunked at `GETLOGS_CHUNK[chain]`, batched 10 calls/request (same shape as the
   address-filtered scans), refused chunks COUNTED not dropped (`RpcBatchOutcome<Set<string>>`).
2. **Repository dedup** — `D1CanonicalRepository.filterKnownCollections(chain,
   addresses)` in `d1-repository.ts`: chunks of 100 against `collection_meta`,
   so OpenSea resolution spend goes ONLY to never-seen contracts.
3. **Worker wiring** — `discoverSaleSidedCollections(...)` in `src/worker/index.ts`,
   called from `runIngestion` AFTER `scanFloors`. Guards:
   - `DISCOVERY_INTERVAL_SEC` wall-clock throttle per chain (`lastDiscoveryAt`),
   - `DISCOVERY_SCAN_BLOCKS` per-chain record — Ethereum OFF (`chain-not-enabled`;
     10-block Alchemy chunks make a full sweep there impractical),
   - `DISCOVERY_MAX_RESOLVE` cap on novel addresses resolved per run;
     novel-but-over-cap contracts wait for the next run (interval throttle makes this safe).
   Result payload carries `seenContracts/known/novel/resolved/resolvedNames`
   so the run log is auditable. Name-based utility filtering happens downstream,
   same as every other path into collection_meta.

## Verified numbers (live smoke, 2026-08-23)
Robinhood chain head ~43.76M: 1,000-block unfiltered sweep → 12,832 logs,
261 distinct contracts, no rate-limit rejection. Use `scripts/live-rpc-smoke.mjs`
in this skill to reproduce against any chain/RPC before shipping an
RPC-touching engine.

## Status
Deployed to production 2026-08-23 (worker version 50f4d14f) and verified error-free
across subsequent cron cycles. Two launch bugs found live and fixed the same day:
(1) `filterKnownCollections` chunked at 100 addresses + chain_id = 101 bound vars →
D1 "too many SQL variables" — chunk at 99; (2) discovery shares the cron tick with
all other legs, contributing to arrowrpc 429 bursts — see the SKILL.md pitfalls for
the backoff tuning that resolved it. Full gate green (132 files / 1034 tests,
lint 0 errors, tsc clean).
