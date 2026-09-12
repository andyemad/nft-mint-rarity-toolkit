# Pirate Nation Onchain Economy — Technical Map (from source, Aug 2026)

Verified against `~/Projects/proofofplay/piratenation-contracts` (read Aug 2026).
All paths relative to `contracts/`. Repo is "heavy development, reference only" per README.

## ECS architecture

- **Entities are uint256s.** `core/EntityLibrary.sol:tokenToEntity` packs `(tokenId << 160) | address` (tokenId < 2^96); wallet = `addressToEntity(addr)`; derived = `accountSubEntity` = `keccak256(account, entity)`. `entityToToken`/`entityToAddress` unpack with round-trip verification.
- **State lives in ~300 auto-generated component contracts** (`generated/components/*`, "Mage CLI codegen"). Pattern (e.g. `generated/components/EnergyComponent.sol`): writes gated `onlyRole(GAME_LOGIC_CONTRACT_ROLE)`, storage is an unstructured mapping at slot `bytes32(ID)`, every write calls `gameRegistry.registerComponentValueSet` (`core/components/BaseStorageComponentV2.sol:_emitSetBytes`) to maintain the registry's entity→components index.
- **GameRegistry** (`GameRegistry.sol`, 1,332 lines) is the service locator + access hub: `registerSystem` needs DEPLOYER_ROLE; `registerComponent`/`batchSetComponentValue` need GAME_LOGIC_CONTRACT/MANAGER/admin; also does cross-chain component publish and multichain transfer delivery. All systems inherit `GameRegistryConsumerUpgradeable` (pausable + reentrancy guard + ERC2771 recipient); `paused() = _paused || _gameRegistry.paused()`.
- **Ownership is always player-keyed**: `core/OwnerSystem.sol:_onlyEntityOwner` compares `OwnerComponent` value against `_getPlayerAccount(_msgSender())`.
- Roles in `Constants.sol`: PAUSER, MINTER, MANAGER, DEPLOYER, GAME_LOGIC_CONTRACT, GAME_CURRENCY/NFT/ITEMS_CONTRACT, DEPOSITOR, VRF_SYSTEM, VRF_CONSUMER, TRUSTED_FORWARDER, TRUSTED_MIRROR, TRUSTED_MULTICHAIN_ORACLE.

## Economic rules (exact numbers from code)

- **L2 shop** — `shop/ShopListingSystem.sol`: SKU entities carry ShopFixedPricingComponent (price), ShopListingComponent (supply, hasUnlimitedSupply, purchaseLimit), MintCounterComponent, EnabledComponent, TimeRangeComponent. `processOrder` (onlyRole SHOP_MINTER_ROLE = Crossmint path) does `transferFrom(msg.sender → treasury, price*qty)` with USDC (6 decimals), validates supply/enabled/time-range/purchaseLimit in `_validateOrder`, fulfills via `batchGrantLootWithoutRandomness`, writes a receipt entity via `GUIDLibrary.guidV1`. `deliverTokenPurchase` is idempotent via ShopTokenDeliveredComponent keyed by purchaseId.
- **L1 shop** — `mainnet/shop/PirateTokenShop.sol:_purchase`: `itemsLimit = 10` per SKU per tx, global `priceIndex = 100` (`total = total*priceIndex/100` — one-var economy lever), `BURN_PERCENTAGE = 10` → **10% of every token payment burned**, foundersDiscount for stake-only buyers holding Founder Pirate, maxPurchaseByAccount, start/end times, `purchasePermit` (ERC20 permit) and `purchaseWithCrossmintETH` (`msg.value == total`). Every purchase mints a ShopReceiptNFT keyed by incrementing purchaseId.
- **Marketplace** — `marketplace/MarketFulfillmentSystem.sol`: admin-relayed orderbook. `escrowListing` burns seller's GameItems, `fulfillOrder` mints to buyer, `cancelListing` mints back; all onlyRole(MARKETPLACE_ADMIN_ROLE); replay protection via per-order components storing block.timestamp. **No price logic onchain.**
- **Energy** — `energy/EnergySystemV3.sol`: measured in wei-ether; `DAILY_ENERGY_REGEN_SECS = 3600`, daily amount + regen (6.25 ether/hr) + VIP regen via GameGlobals read through Uint256Component. `_maxEnergy` = 0 unless wallet owns Gen0 or starter pirate NFT. VIP = `SubscriptionSystem.checkHasActiveSubscription(VIP_SUBSCRIPTION_TYPE)` boosts regen. `purchaseEnergy`: one pack/day keyed `tokenToEntity(caller, block.timestamp/1 days)`, counted by EnergyPackCountComponent, paid by burning loot, grants EnergyPackComponent.energyAmount. `useEnergyConsumable` burns ERC1155 items flagged EnergyProvidedComponent.
- **Cooldowns** — `cooldown/CooldownSystem.sol`: `entity→(cooldownId→uint32 timestamp)`; updateAndCheckCooldown/reduceCooldown/deleteCooldown onlyRole(GAME_LOGIC). NOTE: uint32 timestamps (2106 rollover).
- **Crafting/transforms** — `transform/TransformSystem.sol`: startTransform (user path) / startTransformWithAccount (GAME_LOGIC) / validator variants (TRANSFORM_VALIDATOR_ROLE); inputs burned, outputs granted via loot system; duration = TransformConfigTimeLockComponent.value; repeat cooldown = DefaultTransformRunnerConfigComponent.cooldownSeconds. Crafting buildings: `CraftingBuildingTransformRunnerSystem.getMaxQueueSlotCount` sums CraftingSlotsGrantedComponent; recipes gated by account skill levels (`trade/AccountXpSystem.hasRequiredSkills`).
- **Gems (premium skip-currency, GameItems token id 335)** — `gems/GemUtilitySystem.sol`: gemStartTransform (mints missing inputs after converting deficit→energy-seconds→gems), gemCompleteTransform (early-finish), gemTransformCooldownRemoval. Cost = piecewise formula `(numerator*(t-reduction))/denominator + offset` (`_calculateGemCost`) selected by RangeComponent bounds; per-transform multiplier applied `×mult/100` ceil (`_roundUpWithMultiplier`). Client passes `expectedGemCost`; reverts if `gemCost > expectedGemCost` — a client cap, not an oracle.
- **Loot** — `loot/LootSystemV2.sol`: loot types ERC20/ERC1155/ERC721/LOOT_TABLE/CALLBACK. Weighted draws: `entropy = randomWord % totalWeight`, chained `RandomLibrary.generateNextRandomWord`; per-entry maxSupply (0 = infinite), weight zeroed at cap with cached total weight recompute. VRF path: grantLoot → `_requestRandomNumber` → randomNumberCallback (onlyRole VRF_SYSTEM_ROLE).
- **Ladder** — `combat/Glicko2System.sol` + `core/Glicko2Library.sol`: Glicko-2, INITIAL_RATING 1500, RD 350, volatility 0.06, clamps [100,3000] / RD [30,350]; inactivity grows RD. **No access control on recordGameResult/manuallySetUserData — anyone could write any rating.**
- **Starter pirate** — `starterpirate/StarterPirateSystemV2.sol`: grantStarterPirate (API_MINTER_ROLE), once/account (MintedStarterPirateComponent), VRF-derived traits. `core/TokenIdLibrary.generateTokenId` packs `chainId<<64 | tokenId` for cross-chain uniqueness (Apex/Barret/Cid chains keep raw id).
- **Islands** — `islands/IslandSpawnSystem.sol:spawnStarterIsland`: user-triggered, once/account, GUID scene entity + OwnerSystem.
- **Achievements** — `achievements/AchievementSystemV2.sol:grantAchievement`: MANAGER-gated, counter-minted AchievementNFT, MixinComponent template id.
- **Trade gating** — `trade/TradeLicenseSystem.sol:consumeTradeLicense` burns a Trade License game item → TradeLicenseComponent. `tokens/goldtoken/GoldTokenStrategy.sol`: **no license ⇒ balance is MarkToken (illiquid mark); license ⇒ GoldToken (PIRATE)**; tradeLicenseWasEnabled burns marks→mints gold 1:1; convertGoldToMarks converts back. Earn-and-lock until you pay for tradeability.

## Gasless / meta-transactions

Two layers:
1. **`PopForwarder.sol`** — EIP-712 MinimalForwarder with 2D nonces per batchId; execute appends req.from to calldata, asserts `gasleft() > req.gas/63`. Consumers implement IERC2771Recipient: `GameRegistryConsumerUpgradeable.isTrustedForwarder` checks TRUSTED_FORWARDER_ROLE on the registry; `_msgSender()` strips trailing 20 bytes.
2. **`GameRegistry.registerOperator`** — player ECDSA-signs off-chain message ("Authorize operator account 0x… to perform gameplay actions… with expiration … signed at block …"); operator registers itself; `getPlayerAccount(operator)` resolves to player (reverts if expired, 0 = forever). Systems gate on `_getPlayerAccount(_msgSender())` → server-side operator wallet = free relayer; ownership stays player-keyed. `registerOperatorBatch` (MANAGER) is the server path. Block-number replay guards are commented out; only a per-player cooldown remains.

## Patterns worth stealing

- Components as role-gated storage + registry index; unstructured storage at keccak(ID) (no proxy-slot collisions).
- Operator registration = delegated hot-wallet gameplay with player-keyed ownership (cheapest onchain "session" system).
- Mark↔Gold trade license = soft-peg on/off switch for any currency.
- priceIndex + burn-percentage = two-variable shop economy tuning.
- Piecewise gem formulas = standard time→premium-currency curve; client expectedGemCost cap avoids price oracles.
- Loot tables that self-delete entries at maxSupply (finite supply without manager intervention).
- Admin-relayed marketplace with replay components = orderbook UX without per-order signatures.
- Receipts as GUID entities (indexable, not just events).

## Fragility / overengineering notes

- ~300 generated components + upgradeable proxies everywhere; GameRegistry is a god-object.
- Glicko2System.recordGameResult has NO auth; manuallySetUserData left in "for testing".
- Marketplace has no onchain price/settlement — full trust in MARKETPLACE_ADMIN_ROLE; ERC721 fulfillment unfinished ("Handle ERC721s later").
- Two divergent shop codebases (L1 PirateTokenShop vs L2 ShopListingSystem); L2 trusts Crossmint (SHOP_MINTER_ROLE).
- CooldownSystem uint32 timestamps; TradeLicenseSystem._grantTradeLicense self-warns it "could fail with 2k+ game items"; TransformSystem 1,100+ lines with a dozen runner variants.
