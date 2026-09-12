---
name: onchain-game-economy-analysis
description: "Map an onchain game's economy from Solidity source."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Onchain Game Economy Analysis

Use when asked to produce a technical map, audit, or "how does the economy work" breakdown of an onchain game's Solidity contracts (Pirate Nation/Proof of Play, or any ECS-style onchain game). Deliverable shape: a structured report with `file:function` references and exact economic constants, ~900 words unless told otherwise.

## Workflow

1. **Survey first, read second.** List the repo tree (`search_files` target=files), then `ls`/`wc -l` the subdirectories to find where the money lives (shop/, marketplace/, energy/, gems/, trade/, loot/, transform/). Size-rank the files — 500+ line systems are where the real rules are.
2. **Read the ECS core before anything else.** `EntityLibrary` (entity packing), the registry (service locator + roles), the consumer base (pause/roles/ERC2771), `Constants.sol` (role + trait ID definitions). Everything else reads through these. Core patterns to recognize:
   - Entities as uint256: `(tokenId << 160) | address` packing; wallet = plain address; derived entities = keccak(account, entity).
   - Auto-generated component contracts: role-gated writes (`onlyRole(GAME_LOGIC_CONTRACT_ROLE)`), unstructured storage at slot `bytes32(ID)`, registry index updated on every write.
   - Ownership checks resolve through `_getPlayerAccount(_msgSender())` — ownership is *player*-keyed, never the raw caller.
3. **Grep function signatures before full reads.** `search_files` for `function |constant|error |struct ` on big files, then read only the meat (purchase/fulfill/spend/consume paths). Skip boilerplate generated components — read one as a template, skip the rest.
4. **Chase the money through every sink and lever:** shop (fixed pricing, burn percentage, global price index, per-wallet caps), marketplace (escrow/fulfill, replay protection, who signs), energy (regen rates, earnable caps, VIP multipliers, purchase-gated packs), premium skip-currency (piecewise time→gem formulas, multipliers), loot tables (weighted draws, maxSupply self-removal, VRF path), trade gating (license → liquidity switch), crafting timers (timeLock, cooldown, slot counts).
5. **Identify the gasless / delegated-play path** — it's always there in fully-onchain games: ERC2771 forwarder (trusted-forwarder role + `_msgSender()` calldata stripping) and/or off-chain-signed operator registration. Note replay guards (or their absence).
6. **Report in four parts:** architecture (how state/roles/ownership work), economic rules with exact numbers, gasless/delegation path, and a "reusable patterns / fragility" split. Exact constants matter more than prose.

## What to flag (fragility checklist)

- No access control on state-writing functions (`recordGameResult` style — anyone can corrupt).
- Admin roles with full economic power (relayed orderbooks, minter roles) — note where trust concentrates.
- Commented-out security checks (replay guards, block limits) — dead mitigations.
- uint32 timestamps (2106 rollover), divergent duplicate shop codebases, "handle ERC721s later" TODOs.
- Client-supplied price caps instead of oracles (`expectedGemCost` pattern) — legit, note it as a feature.

## Pitfalls

- Don't read generated components wholesale — they're ~300 nearly identical files. Read one, treat the rest as known.
- Component/entity IDs are keccak strings (`game.piratenation.<name>`); the constants file defines the canonical trait IDs — check there before grepping raw strings.
- L1/L2 games often have two parallel shop implementations; report both, they diverge.
- Pause semantics: `paused()` ORs the consumer's own flag with the registry's — global kill switch exists.

## Reference

- `references/piratenation-contracts-economy.md` — verified technical map of Pirate Nation's onchain economy (Aug 2026): ECS architecture, exact economic constants (10% burn, 6.25 NRG/hr, gem token 335, Glicko params, priceIndex), gasless pattern, reusable patterns, fragility notes. Path: `~/Projects/proofofplay/piratenation-contracts`.
