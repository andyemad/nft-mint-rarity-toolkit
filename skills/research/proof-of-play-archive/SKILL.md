---
name: proof-of-play-archive
description: "Use when referencing Proof of Play, Pirate Nation, PopBot."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Proof of Play Archive & Lessons

Proof of Play = a16z-backed fully-onchain game studio (Pirate Nation, Apex/Boss chains, founder Amitt Mahajan of FarmVille fame). Ceased operations Aug 4, 2026 after ~$63M raised. Open-sourced everything. **Local mirror: `~/Projects/proofofplay/` (all 10 org repos, cloned 2026-08).**

## Local inventory

| Repo | What it is | License | Notes |
|---|---|---|---|
| `drand` | Distributed randomness beacon (Go, DEDIS upstream) — verifiable unbiased RNG, PoP's vRNG base | NOASSERTION (fork of drand/drand) | Biggest repo ~50MB |
| `piratenation-game` | Full Unity client (C#) — reference onchain game client | MIT (studio code) | glTF/glTFast rigged assets |
| `piratenation-art` | Founder Pirates NFTs + Pirate Nation artwork/IP/logos | **CC0-1.0** | Free for any project |
| `popbot-tool` | Internal multi-agent coding cockpit (Electron/Node) | MIT | **The sleeper asset** (see below) |
| `piratenation-contracts` | Solidity game contracts | MIT | "Heavy development, reference only" per README |
| `piratenation-shuffler` | Provably-fair NFT shuffle (Python) — Ethereum block hash as seed + image-dir hashing | N/A | Great pattern for fair reveals |
| `glfast-importer-unity` | glTFast fork — glTF 2.0 import for Unity | Apache-2.0 | |
| `server-status-monitor` | express-status-monitor (realtime server metrics) | MIT | |
| `operator-filter-example` | OpenSea/Blur operator-filter royalty protection (Hardhat/TS) | N/A | Used post-launch on Pirate Nation |
| `s3-sync-action` | GitHub Action wrapping `aws s3 sync` | MIT | |

## Business postmortem — why it failed

Timeline: founded 2023 ($33M seed, a16z + Greenoaks) → $30M round 2024 → Aug 2025 Pirate Nation killed as standalone game (features folded into "Arcade on Abstract") → Aug 4, 2026 company shutdown, Apex/Boss chains sunset in 30 days.

Core lesson (their own words):
- **"Adding earning wasn't a feature, it's the Original Sin"** (co-founder Fern). Mixing financial incentives with play → short-term spikes, long-term damage, sell-pressure > DAU spiral.
- **"P2E (& Play-and-Earn) is fundamentally broken"** (CEO Mahajan, when they killed token emissions). Emissions to unaligned parties = downward spiral.
- Tech that works ≠ business that works. They proved gasless onchain gaming; the audience and revenue never scaled.
- Sector context: Web3 gaming is contracting — Uncharted, YGG Play, POAP, Proof of Play all shut. The "player ownership / games that outlive developers" thesis failed at scale.

Token-economy red flags (generalize to any token-gated product):
- Emissions paid to parties not aligned with long-term success.
- Reward eligibility moved late (Pirate Nation Season 3: VIP-pass requirement announced at season end), 180-day vesting, burned unvested rewards → community "rug" accusations.
- Rewards > fun in the product loop.

## PopBot — reusable multi-agent orchestration pattern

Location: `~/Projects/proofofplay/popbot-tool` (docs: GUIDE.md, CORE_MODEL.md, ARCHITECTURE.md, POPBOT_DESIGN.md). Drives the REAL Claude Code and Codex via their SDKs — not a reimplementation.

The durable, generalizable pattern (MIT, meant to be forked):
1. **One unit of work = one Chat.** Durable transcript (SQLite): prose, tool calls, diffs, permission decisions. Archive/reopen with full history — rollback = send another message, never rewrite history.
2. **Slots = git worktree + warm build state.** Pool per repo; chats lease/release; worktrees created rarely, reused. For Unity: per-slot `Library` import cache COW-cloned from a master checkout (first warmup cheap), sticky reuse keeps Editor hot. Branch isolation = N agents without chaos.
3. **Repoless review chats.** PR review is read-only → instant, no slot. Reviews never starve builds of slots.
4. **Inbox-as-queue.** Linear tickets + GitHub PR reviews = one-click chat spawns; ticket auto-moved In Progress; branch named `<user>/<ticket>-<slug>` from base branch.
5. **Permission floor (hard, in code, not overridable by UI grants).** Auto-allowed: in-worktree reads/edits/shell + slot's own services. Always gated: `git push`/reset/force, anything outside the worktree, PR creation, sending messages, network to non-allowlisted hosts. Grants: once / session / durable, all revocable.
6. **Live fleet view.** Thumbnail strip of every open chat, color-coded (blue=running, green=done, yellow=needs-you, red=error) with live transcript preview — catch a wrong path before it burns tokens.
7. **Ephemeral vs durable.** AgentSession = in-memory, spawned per running chat, disposed on close. Chat/Slot = durable. Status is derived, not prescribed.
8. **Mid-session model switch** + **restart-with-context** (fresh session primed with chat history) for long/wedged sessions.
9. **Verify by running.** Agent launches the actual app in its slot (Unity Editor + sidecar server on a second display, MCP-driven) — "seen it work, not thinks it works."
10. **Electron hygiene:** renderer never owns canonical state, never touches FS/processes; typed namespaced IPC (`pb:*`); secrets in OS keychain (keytar), never in DB/logs.

Relevance to our stack: same ideas map to Hermes + Claude Code/Codex delegation — isolated worktrees, gated irreversible actions, persistent transcripts, live oversight. Use as reference when building our own orchestration tooling or evaluating Hermes features.

## Deep technical map

`references/deep-dive-technical-map.md` — full forensic map read from the actual code (Aug 2026): onchain ECS internals, every economy mechanic with exact values (energy 6.25/hr, 10% burn, priceIndex, one-pack/day, gem formulas, trade-license mark↔gold, self-deleting loot tables), the gasless forwarder + operator-registration layers, Unity client sync (Mage codegen, GraphQL, Nethereum, replay-validated combat with keccak fingerprints), GameLift PvP server (Unity sources compiled into .NET), CI/CD, PopBot internals (parking-branch worktrees, permission floor), drand wiring, plus the reusable-patterns list and fragility red flags. Cite from there instead of re-reading the repos.

## When to use this skill

- Any analysis/writing referencing Proof of Play, Pirate Nation, PopBot, or onchain gaming.
- Building multi-agent dev tooling — steal the slot/permission/inbox patterns.
- Game projects wanting free CC0 pirate art (`piratenation-art`) or a Unity onchain-client reference (`piratenation-game`).
- Evaluating crypto/P2E/web3-gaming opportunities — apply the postmortem lens (emissions alignment, reward-vs-fun, eligibility transparency).
- Provably-fair randomness/shuffle needs (drand, piratenation-shuffler) or Unity glTF import (glfast-importer-unity).

## Asset audit corrections (Claude review 2026-08-05) — supersede any inflated earlier counts

- **~605 distinct ships** (411 glTF models), not "28,775 renders". The rest are 5 thumbnail resolutions × 2 variants + 6 orthographic angles, and shared parts duplicated per folder (`PN_ship_flag_03.vxm` appears in 247 ship dirs).
- **~10,000 unique Founder's NFTs** (9,999 pirates), not "30,149 files" — `illustrated/` + `model3d/` + `voxel/` are the same pirates in three render styles.
- **CC0 images cloned as 131-byte Git LFS pointers** — git-lfs was installed but never wired; the ~41.9 GB payload lives on GitHub only. Ship subset (1,531 files, ~984 MB, thumbnails + glTF) already pulled into `piratenation-art` and verified real (1024×1024 PNGs, valid glTF JSON) — that's the shippable inventory.
- **CC0 §4(a) does NOT waive trademark** (`LICENSE:104-105`); the Pirate Nation Foundation still operates and uses the mark. Sell the art, never the brand, never ship `Logos/`.
- **"Strip the blockchain" = 100% rewrite.** Every economy system inherits `GameRegistryConsumerUpgradeable` + on-chain ECS + ERC-1155/721 on an upgradeable proxy. What transfers is a spec, not an engine.
- Verified TRUE in source: CC0-1.0 art / MIT contracts+client; energy 6.25/hr + VIP multiplier + daily cap (`energy/EnergySystemV3.sol:41-52`); trade-license earn-and-lock (`trade/TradeLicenseSystem.sol`); Glicko2 (`core/Glicko2Library.sol`); self-deleting loot tables (`loot/LootSystemV2.sol:382-386` — weight zeroes once mintCounter >= maxSupply).
- **Standing risk:** no public mirror of the art; org is on paid LFS data packs — when a winding-down company stops paying, LFS goes read-blocked silently (likely weeks, no warning). If a pack ever sells, pull the rest immediately, not incrementally.

## Study findings (Claude's source pass, 2026-08-05) — five things the first map missed

Companion skill: **`f2p-economy-architecture`** (`~/.hermes/skills/game-development/`, symlinked into `~/.claude/skills/` — one file, both agents). 15 economy patterns with file:line. Load it for any game build. Claude re-derived everything from source; the corrections below supersede `references/deep-dive-technical-map.md` where they differ:

1. **The Transform engine is the biggest idea.** `transform/` (4,395 lines, 17 files) is ONE engine (`TransformSystem.sol`, 1,115 lines) + pluggable runners (~250 lines each). Crafting, bounties, building upgrades, blacksmith, roguelite runs, lives, stockpile tax are all runners, not systems. Runners compose on a single action; flags OR together. Build this first in any future game.
2. **Energy is TWO pools**: `energy` (spend to act) + `energyEarnable` (separately regenerating cap on what you can receive). Independent `(amount, timestamp)` pairs. Decouples play from extraction — whales who buy energy can't also drain the reward faucet. Also: retroactive VIP proration across rate-change gaps.
3. **Anti-cheat is server-authoritative simulation, not command-log replay.** `DotNet/PiratePvPServer/Server/PvPSession.cs:522+` — the server builds a real `CombatSession` and runs the game. Randomness: `roll(n) = keccak(seed ‖ n ‖ playerAddress)`, seed from **drand** (`api.drand.sh`), optionally bound to a FUTURE round so the seed provably doesn't exist at match start. No blockchain needed — one HTTP GET + a hash. Most transferable idea in the archive.
4. **Trade license has a second path: auto-grant on account-XP threshold** (`trade/AccountXpSystem.sol:241-258`). Proof-of-engagement / anti-Sybil gate first, paywall second. Generalizes to any exit gate.
5. **~Half the contracts are generated.** 225 of 449 (72,465 of ~100k lines) are Mage-CLI codegen, marked `DO NOT EDIT`. Hand-written logic ~30k lines. Also: shared primitives (`CooldownSystem`, `CountingSystem`) are two-level `entity → key → value` maps used by every other system.

Not in the archive (say this up front in plans): combat engine source is GONE (`DotNet/PirateCombatEngine/` has only a `.csproj`); no ready-to-run backend; art is Git LFS (41.9 GB; ~605 ships / 984 MB fetched locally).

## Pitfalls

- Proof of Play points are worthless (explicitly non-redeemable). $PIRATE continues via the independent Pirate Nation Foundation, NOT PoP.
- `popbot-tool` runtime depends on `@anthropic-ai/claude-agent-sdk` — proprietary, outside the MIT grant. That blocks **redistributing the SDK bundled in your own MIT project**, not installing/running/studying/forking PopBot (it installs from npm under Anthropic's ordinary terms, same as running Claude Code). 26,829 lines of TypeScript for running a fleet of Claude Code/Codex agents in parallel in isolated git worktrees — a production reference for our own orchestration. Read `docs/adr/0004-canusetool-policy-boundary.md` first (see the `agent-tool-policy-boundary` skill).
- `piratenation-contracts` README warns: reference only, heavy development.
- `drand` is a fork of upstream drand/drand — check which lineage before reusing.
- Repos cloned 2026-08; re-pull (`git pull` in each) before reuse in new work.

## Verification

- `ls ~/Projects/proofofplay/` shows all 10 repos.
- `git -C ~/Projects/proofofplay/popbot-tool log --oneline -1` works; docs present under `docs/`.
- License spot-checks: popbot-tool → MIT, piratenation-art → CC0-1.0, piratenation-contracts → MIT, glfast-importer-unity → Apache-2.0.
