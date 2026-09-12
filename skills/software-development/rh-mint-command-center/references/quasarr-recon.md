# Quasarr Desktop — recon record (2026-08-23)

Everything a future session needs to continue the Mint Room parity program without
re-mining the app. Clean-room: behavior and schemas only, no proprietary code copied.

## What it is
- Quasarr Desktop v1.3.4 — .NET 10 + Avalonia (ShadUI) macOS app, arm64, adhoc-signed.
  NFT minting automation + wallet management. Vendor: quasarr.xyz (docs:
  quasarr.gitbook.io/quasarr-docs, dashboard: quasarr.xyz/dashboard). Also ships a
  Discord "Bot" product (monitors/tweets/alerts) — separate, not part of parity scope.
- Install: extracted from `~/Downloads/work/Quasarr-osx-arm64-Setup.pkg` → copied to
  `/Applications/Quasarr.app`, quarantine cleared (`xattr -cr`). Gatekeeper still shows
  spctl "rejected" (adhoc signature) but the app launches fine.
- Licensed: Pro Access trial, HWID-locked, 1 reset/7 days. Key stored
  `~/.hermes/secrets/quasarr_license` (chmod 600, never echo). Discord account "emad"
  linked; wallet NOT linked in their dashboard.
- App data: `~/Library/Application Support/Quasarr/` — `quasarr.db` (SQLite, WAL),
  `license.key`, `logs/quasarr-YYYYMMDD.log`, `ImageCache/`.

## Extraction recipe (any .pkg / .NET app)
```
xar -tf X.pkg                       # list
xar -xf X.pkg -C /tmp/x             # extract -> Distribution, <id>.pkg/{Bom,Payload,PackageInfo}
cat <id>.pkg/Payload | gunzip -dq > payload.cpio   # gzip'd cpio
cpio -idm < payload.cpio            # -> App.app tree
strings -a App.app/Contents/MacOS/<App>.dll | grep -iE "<keywords>"
```
- `strings` on the main .dll reveals: feature strings (UI labels), EF Core migration
  names (a free dated feature timeline: e.g. `20260725233653_AddContractMinter`,
  `20260814092506_AddOpenSeaApiKeyPool`), embedded URLs, module ids.
- The app's LIVE SQLite DB is the ground-truth data model: `sqlite3 .schema <table>`
  per table. Logs show runtime behavior (and failing endpoints).

## Data model (23 tables, from live quasarr.db)
Wallets (EncryptedPrivateKey+Salt+Nonce+EncryptionVersion, WalletGroupId, Balance,
Nonce blob) · WalletGroups · WalletDelegations · TaskGroups (ContractAddress, ModuleId,
ModuleChain, ModuleMetadataJson) · MintTasks (Abi, RawData, Value, GasLimit,
MaxFee/MaxPriorityPerGas, AutoGasEnabled+Multiplier, BroadcastMode, ExecutionStrategy,
SimulationMode, SpamCount+SpamDelayMs, ScheduledFor, BlockNumber, Nonce, TriggerMethod-
Selector+TriggerWatchContractAddress+TriggerSenderFilter+TriggerWsRpcUrl+TriggerGasStrategy,
MerkleProofDataJson, AbiParameterRangesJson, ErrorSelector, MintSubmissionMode,
OpenSeaScheduleStageIndex, ModuleParamsJson/ModuleSourceDataJson, AutoTransfer*,
AllowPublicFallback, per-task RPC via MintTaskRpcEndpoints) · MintHistory (OccurredAt,
GasUsed, EthValue, MintedTokenIds, ErrorSelector, ModuleIdentifier) · TaskLogs ·
ContractMinter{Deployments,BatchExecutions,BatchJobs,BatchTransactionAttempts}
(operator wallet, OperatorNonce, nonce-lane filter, per-job wallet+status) ·
ContractErrorSignatures (revert-selector decoding) · RpcEndpoints (Url, Priority,
MaxRequestsPerSecond, encrypted ApiKey, IsDefault/IsActive) · ProxyGroups (proxy pool
for module API requests) · CaptchaSettings (provider+key) · OpenSeaApiCredentials
(key POOL: Ciphertext+Tag, IsActive, SortOrder) + OpenSeaApiSettings (preference/
transport/schedule-stage) · DashboardStatistics · StateSyncOutboxItems ·
QuickTaskSettings · AppSettings.

## Feature map (parity checklist)
1. Wallets: groups, batch-create (1-500, prefix), import single/batch (`alias,key`
   lines), export (keys!), balance refresh per RPC, nonce tracking.
2. Task groups: named per-mint container; contract + module context; tasks inherit.
3. Modules: manual (ABI or raw hex calldata + value), opensea (slug/URL → fetch chain/
   contract/stages; public stages direct on-chain encoding, API stages resolve
   proof/signature at runtime; schedule-stage binding), rarible/merkle (RPC → detect
   allowlist phases, per-wallet + batch proof generation), contract-minter (operator
   batch-mints many recipients in ONE tx via deployed helper contract; full journal).
4. Execution: simulation (eth_call dry-run, timeout, retries, gas+cost estimate),
   gas strategy (manual maxFee/priority, auto-gas × multiplier, safety margin),
   speed-up (same-nonce higher-gas re-send), spam mode (count+delay), broadcast modes,
   scheduled-for, per-task RPC override.
5. Trigger mode: wss pending-tx watch (contract + method selector + sender filter)
   → launch prepared group. Private bundles: NOT supported (their gap; we skip too).
6. Post-mint: auto-transfer destination; MintHistory with mintedTokenIds; revert
   decoding via ContractErrorSignatures.
7. Fund ops: Disperse (1→N native/ERC20, per-row or bulk amounts, gas-aware total),
   Collect (N→1, collect-all-with-gas-reserve or fixed).
8. NFTs: on-chain ERC-721/1155 scan by contract across selected wallets (no
   marketplace guessing), detail panel, single/batch transfer.
9. Ops: RPC manager (priority, rate limit, failover, encrypted keys), proxy pool,
   captcha provider setting, OpenSea key pool rotation, dashboard stats.
10. Quasarr gaps we exploit (parity-OR-better): no Robinhood-chain preset, no rarity
    intelligence, no deal/snipe ranking, no reveal watching — Mint Room already has
    all four (rarity-gallery generic scanner, deal-scan, reveal watcher crons).

## Runtime quirk (his copy, 2026-08-23)
Its log spams `Network status fetch failed ... ethereum-rpc.publicnode.com` every ~3s
(default ETH RPC unreachable — likely the Wi-Fi split-proxy 127.0.0.1:8887 interfering
with the .NET HTTP stack, or the endpoint itself). Fix path: add working endpoints
(RH RPC + any alchemy/infura keys he holds) via its RPC settings UI; wave 14 item.

## Mint Room mapping (what to build where)
- MintTask model + calldata/gas planners → `lib/server/task-modules.ts` (wave 7)
- Simulation → `lib/server/simulate.ts`; revert decode → `lib/server/error-decode.ts`
  (openchain.xyz signature DB, cached)
- OpenSea module → reuse vendored osnm-z engine + opensea-listings pipeline +
  `~/.hermes/secrets/opensea_key`; stage scheduler extends queue-worker
- Merkle → `lib/server/modules/merkle.ts` (claim-condition detect + per-wallet proofs)
- Contract-minter → new Solidity operator contract, LOCAL/SIMNET deploy only until
  Emad approves live
- Trigger/spam → `lib/server/trigger-watch.ts` (wss), spam runner behind per-run
  max-spend + kill switch
- Fund ops → `lib/server/fund-ops.ts` (unsigned-tx builders + rehearse summaries)
- Deviations by design: keys stay in ~/.hermes/secrets (never in-app DB), loopback
  guards, rehearse/live toggles, RH chain first-class.
