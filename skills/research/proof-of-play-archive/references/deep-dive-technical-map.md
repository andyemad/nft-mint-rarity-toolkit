# Pirate Nation — Deep Technical Map (read from code, Aug 2026)

Full forensic pass over piratenation-game (971 C# files), piratenation-contracts, popbot-tool, drand, shuffler. All paths relative to `~/Projects/proofofplay/`. Game: WebGL Unity 2022.3.51f1, onchain ECS, archival release does NOT compile OOB (12 paid plugins stripped: Privy, ACTk, Sentry, Odin, DOTween Pro, Voxel Importer, Stylized Water 2, etc.).

## Onchain ECS (contracts/)
- Entities = uint256. `core/EntityLibrary.sol`: `tokenToEntity` packs `(tokenId<<160)|address`; wallet = `addressToEntity`; sub-entities = `keccak256(account,entity)`.
- State in ~300 generated component contracts (Mage CLI codegen). `generated/components/EnergyComponent.sol:setLayoutValue`: writes gated `GAME_LOGIC_CONTRACT_ROLE`, storage at unstructured slot `bytes32(ID)` (diamond-style, no collisions), every write → `gameRegistry.registerComponentValueSet` (index for offchain queries).
- `GameRegistry.sol` (1,332-line god object): registerSystem (DEPLOYER_ROLE), registerComponent/batchSet, service locator, cross-chain component publish, multichain 1155 delivery. Consumers = `GameRegistryConsumerUpgradeable` (pausable, reentrancy-guarded, ERC2771).
- Ownership always resolved to player via `OwnerSystem._onlyEntityOwner` → `_getPlayerAccount(_msgSender())`, never the operator.

## Economy rules encoded onchain (the money map)
- **Shop L2** (`shop/ShopListingSystem.sol`): SKU entities with `ShopFixedPricingComponent` (USDC 6dp price), `ShopListingComponent` (supply, hasUnlimitedSupply, purchaseLimit), `MintCounterComponent`, `TimeRangeComponent`. Orders via Crossmint (`SHOP_MINTER_ROLE`): pay → validate (price≠0, supply, time, mints+qty≤supply, qty≤purchaseLimit) → `batchGrantLootWithoutRandomness` + receipt entity (GUID). Idempotent via `ShopTokenDeliveredComponent`.
- **Shop L1** (`mainnet/shop/PirateTokenShop.sol:_purchase`): itemsLimit 10/SKU/tx, global `priceIndex` lever (total=(total*priceIndex)/100), **10% burn on every token payment** (`BURN_PERCENTAGE=10`), foundersDiscount for Founder Pirate holders, `maxPurchaseByAccount`, permit or ETH purchase, receipt NFT per purchaseId.
- **Marketplace** (`marketplace/MarketFulfillmentSystem.sol`): admin-relayed orderbook. escrow burns seller GameItems, fulfill mints to buyer, cancel mints back — all `MARKETPLACE_ADMIN_ROLE`, replay-protected via per-order timestamp components. NO price logic onchain (trust boundary).
- **Energy** (`energy/EnergySystemV3.sol`): wei-ether, "6.25 ether per 3600s" regen; max/regen caps via GameGlobals (`Uint256Component`); `_maxEnergy=0` unless wallet holds Gen0/starter pirate; VIP subscription (`SubscriptionSystem`) switches regen amount; `purchaseEnergy`: ONE pack/day keyed `tokenToEntity(caller, now/1day)`, paid by burning loot, grants `EnergyPackComponent.energyAmount`.
- **Cooldowns** (`cooldown/CooldownSystem.sol`): entity→(cooldownId→uint32 timestamp) — uint32 = 2106 rollover.
- **Crafting/transforms** (`transform/TransformSystem.sol`, 1,100+ lines): inputs burned, outputs via loot system, duration = `TransformConfigTimeLockComponent`, repeat cooldown = `DefaultTransformRunnerConfigComponent.cooldownSeconds`; queue slots sum `CraftingSlotsGrantedComponent` per building; recipes gated by account XP/skills.
- **Gems** (premium skip currency, item id 335, `gems/GemUtilitySystem.sol`): `gemStartTransform` converts deficit → energy-seconds → gems; `gemCompleteTransform` early-finish; piecewise cost formula `(numerator*(t-reduction))/denominator + offset` with `RangeComponent` bounds; client passes `expectedGemCost` cap (reverts if gemCost > cap — no price oracle). Resource→seconds = `(amount/unitDenomination)*unitEnergyCost*unitEnergyMultiplier`, min 1.
- **Loot** (`loot/LootSystemV2.sol`): weighted draws (`entropy = randomWord % totalWeight`, chained RNG); each entry `maxSupply` (0=infinite); when mintCounter≥maxSupply the weight is ZEROED and total recomputed — loot tables self-remove at cap (finite drops without manager action). VRF routes via `grantLoot→_requestRandomNumber→randomNumberCallback` (VRF_SYSTEM_ROLE).
- **Ladder** (`combat/Glicko2System.sol` + `core/Glicko2Library.sol`): Glicko-2, initial 1500, RD 350, volatility 0.06, clamp [100,3000], RD [30,350]; inactivity grows RD. ⚠️ `recordGameResult` has NO access control — anyone could write any rating.
- **Trade license** (`trade/TradeLicenseSystem.sol` + `tokens/goldtoken/GoldTokenStrategy.sol`): THE standout mechanic. Burn a Trade License item → `TradeLicenseComponent` flips tradeability. No license ⇒ balance is `MarkToken` (illiquid marks); license ⇒ `GoldToken` (PIRATE). `tradeLicenseWasEnabled` burns marks → mints gold 1:1; `convertGoldToMarks` converts back. **Earn-and-lock until you pay for tradeability.** Soft-peg on/off switch for any currency.
- **Starter pirate** (`starterpirate/StarterPirateSystemV2.sol`): once per account, traits derived from VRF word (DiceRoll, StarSign, Affinity, Expertise); `TokenIdLibrary.generateTokenId` packs `chainId<<64|tokenId` for cross-chain uniqueness.
- **Islands** (`islands/IslandSpawnSystem.sol`): once per account, GUID scene entity. **Achievements**: MANAGER-gated counter-minted AchievementNFTs.

## Gasless / meta-tx (two layers)
1. `PopForwarder.sol` — EIP-712 MinimalForwarder, 2D nonces per batchId; `execute` appends `req.from`, asserts `gasleft() > req.gas/63`; consumers ERC2771 via `TRUSTED_FORWARDER_ROLE`.
2. `GameRegistry.registerOperator` — player ECDSA-signs an offchain message authorizing an operator wallet; operator then plays as the player (`getPlayerAccount(operator)`); server-side operator = free relayer for all gameplay while ownership stays player-keyed. Block-number replay guards are COMMENTED OUT (only per-player cooldown remains). ⚠️

## Unity client (piratenation-game)
- **Mage codegen**: `Assets/_PirateNation_/Mage/Runtime/Components/Generated/*.cs` autogenerated partials (Id e.g. `game.piratenation.energycomponent`, keccak Hash, typed fields). Consumed via GraphQL + Nethereum.
- **GraphQL** (`Game/Core/Runtime/GraphQL/UnityClient/GraphQLApi.cs`): legacy subgraph + new indexer, `MageGQLClient.cs` POST with 502-retry + exponential backoff. Remote config (`GraphQL/Shared/Configs.cs`): rpcUrl, subgraphUrl, drandUrl, relayApiUrl.
- **Nethereum** (`NethereumUnityProxy.cs`): sign/send via PopForwarder relay; nonce tracking, gas factor 1.25, 5 retries. Per-domain backends (Island/Energy/Gold/GameItem/Crafting/DailyDungeon). VrfListener block polling. Auth = Privy embedded wallet.
- **Combat**: `CombatEngine/Runtime/CombatEngine.cs` compiles IDENTICALLY in Unity and as the standalone .NET PvP server (`#if UNITY_2022_1_OR_NEWER` flips isCombatServer); deps are interfaces via `ServiceManager` DI. Decks: min 40 cards, persisted in PlayerPrefs (not onchain), submitted per battle. Battle payload = `MegaPack.cs` (MessagePack): seed, players, enemies; randomness from drand (DrandNumberProvider), deterministic per-player streams (seed+address, counter-based). Commands (`PlayCardCommand` etc.) snapshot state before each; whole battle = `CombatCommandCollection` MessagePack. `CombatSession.cs` 2,100-line state machine. `CombatValidator.cs` REPLAYS the command list against initial state, returns keccak256 fingerprint if valid; validation sampled server-side (`ValidationFrequency`). Settlement: keccak posted via HMAC meta-tx relay.
- **Anti-cheat**: client = CodeStage ACTK (ObscuredCheatingDetector, SpeedHackDetector, TimeCheatingDetector, InjectionDetector) + honeypot values; real enforcement = replay validation + keccak settlement + cheat analytics events.
- **Voxel**: 16³ chunks, greedy meshing + LOD (`MeshBuilderGreedyCubesGenerator.cs`); local placement NOT synced; persistence = onchain `UpdateScene` object lists (x,y,z,rotation,objectEntity,instanceEntity).
- **Asset pipeline**: `AssetCache/Runtime/CachedAssetManager.cs` maps `ipfs://hash→prefab`; `GLTFPostProcessor.cs` bakes GLTFs to cached prefabs; ArWeave + IPFS avatar materials.

## Server / ops / tooling
- **PvP server** (`DotNet/`): AWS GameLift, ONE battle per process (exits after session). csproj wrappers `Compile Include` the exact Unity C# sources into .NET libs (`EnableDefaultCompileItems=false`, `NoWarn CS0436`) — one combat engine, two runtimes. Session payload via GameSessionData (megapack JSON) / GameProperties / FlexMatch MatchmakerData. WebSocketSharp per-player connections keyed by address. Results PATCHed to relay. Glicko2 is Solidity, NOT .NET — FlexMatch pairs, contracts rate.
- **CI/CD**: `.github/workflows/main.yml` — custom Unity runner, WebGL build → brotli → S3 `pop-game-assets` via vendored s3-sync-action; iOS/Android via fastlane (match certs from git repo, gym, TestFlight/Play AABs). `build-and-deploy-gamelift.yml`: dotnet publish single-file → zip → S3 → GameLift fleet (us-west-2 "because us-west-1 does not support flexmatch").
- **PopBot** (`popbot-tool/src/main`): parking-branch model — each slot N = long-lived worktree on `<repo>/slotN` parking branch; idle slots never hold develop/main. `ensureSlotWorktree` idempotent, `parkSlot` stashes dirty → checkout parking, per-chat stash naming. Permission floor in `agents/ClaudeBackend.ts handleCanUseTool` → `resolveRule`: per-chat rules first, then global; allow/deny short-circuit, else permission-request parked in `pendingPerms`; `AgentHost.ts` (1,148 lines) singleton: lazy spawn, pinned SDK session UUIDs, `recoverFromBadSession` (30s cooldown), SQLite durability mirror, transcript replay as flattened narration (resumes history WITHOUT re-executing tool side effects). ⚠️ Codex backend: `approve()` is a no-op — no interactive permission floor (asymmetric).
- **drand**: fork, only PoP work = local multi-beacon docker-compose dev branch; in-game uses public drand network, seed = first 64 bits of keccak(utf8(randomness)) committed into megapack. **shuffler**: `mint-shuffler.py` seeded shuffle of 9,998 NFT ids around team NFTs 9,983-9,999; `hash-image-dir.py` SHA3-224 dir fingerprint; fair-reveal proof: seed = FUTURE Ethereum block hash announced in Discord, before/after hashes published.

## Reusable patterns (steal these)
1. Role-gated component storage + registry index (trivial permissions, hot-swappable logic, clean indexing).
2. Unstructured storage at keccak(ID) — zero proxy-slot collisions, no migration risk.
3. Operator registration = cheapest onchain session system (delegated hot wallet, player-keyed ownership).
4. **Trade license (Mark↔Gold): earn-and-lock liquidity switch** — best single mechanic in the codebase.
5. `priceIndex` + burn-% = two-variable shop tuning.
6. Piecewise "time = premium currency" formula with client-side cost cap (no oracle).
7. Self-deleting loot tables (weight zeroing at maxSupply).
8. Admin-relayed marketplace with replay components (orderbook UX without per-order sigs).
9. Receipts as GUID entities (every purchase indexable).
10. Shared pure-C# engine compiled into client AND server (deliberate CS0436) + replay validation + keccak fingerprint = deterministic anti-cheat without trusting the client.
11. Megapack = self-contained battle-state JSON flowing through session data/matchmaker.
12. PopBot parking-branch worktrees + layered permission rules + transcript-replay session resumption.

## Fragility / red flags (learn from these)
- Glicko2 `recordGameResult` NO access control; `manuallySetUserData` "for testing" — ladder integrity relied on nobody calling it.
- `registerOperator` replay guards commented out.
- Marketplace = full trust in admin role; 721 handling unfinished (admitted in comments).
- Two divergent shop codebases (L2 listing system vs L1 PirateTokenShop).
- God objects: GameRegistry 1,332 lines; CombatSession 2,100 lines; AgentHost 1,148 lines.
- V1/V2 dual serialization, `TypeNameHandling.Auto` (type-name deserialization risk), "TODO: remove after migration" markers.
- uint32 cooldown timestamps (2106 rollover). Hardcoded testnet relay fallback. One-battle-per-process GameLift (no warm reuse). Sampled validation = trust gap. OSS release ships empty HMAC secret.
- Business layer: 10% token burn, 180-day vesting + burned unvested rewards, late VIP-pass eligibility change — the community-facing failures that read as a rug.
