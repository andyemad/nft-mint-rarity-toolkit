# NFT Mint & Rarity Toolkit

Agent-ready playbooks and working code for on-chain NFT work: **minting, rarity
ranking, reveal sniping, proof-of-work mints, wallet operations, and on-chain
forensics.**

This is not a framework or a library with an API. It is the accumulated
operational knowledge of an AI agent that has actually minted, ranked, sniped,
audited and been burned on real collections — plus the scripts that did it. Every
claim in the skills is dated and tied to a specific collection, transaction, or
endpoint response, including the ones that turned out to be wrong.

If you are an agent (Hermes or otherwise) picking this up: read
[`SKILLS.md`](SKILLS.md) for the full index, load the relevant `SKILL.md` before
doing the work, and reuse `toolkit/` instead of rewriting the plumbing.

Primary chain of record: **Robinhood Chain (chain id 4663)** — an Arbitrum Orbit
rollout — with Ethereum mainnet and Ink as secondary targets.

---

## 1. What you can build with this

| Capability | Skill(s) | Runnable code |
|---|---|---|
| Rank a whole collection by rarity, matching OpenSea exactly | `nft-rarity-engine`, `ethereum-data-pipelines` | `toolkit/rarity/rarity_engine.py`, `combox_rarity.py`, `bakemono_rarity.py` |
| Detect a reveal the moment metadata flips, then sweep + rank it | `nft-rarity-engine`, `rh-chain-rarity-sniping` | `toolkit/rarity/rarity_engine.py watch` |
| Snipe rare listings at/near floor after a reveal | `rh-chain-rarity-sniping`, `nft-secondary-buy` | `toolkit/sniper/buy_secondary.py`, `probe_fill.py` |
| Fire a SeaDrop public mint across many wallets at T-0 | `seadrop-rapid-mint`, `nft-mint-recon` | `toolkit/mint/seadrop_fire.py` |
| Mint a custom contract (detect `mint()`, find the real price by simulation) | `rh-mint-command-center`, `nft-mint-recon` | see `skills/software-development/rh-mint-command-center` |
| Reverse-engineer an unknown mint site and mint it | `ethereum-data-pipelines` → `free-mint-site-reverse-engineering.md` | — |
| Mine a proof-of-work mint (keccak / sha256, up to max difficulty) | `pow-mint-mining`, `onchain-puzzle-mining` | `toolkit/pow/*` (C, CUDA, Metal, Swift) |
| Solve an on-chain puzzle, claim gate, or refund allocation | `onchain-puzzle-solving`, `onchain-claim-reverse-engineering` | `toolkit/pow/*`, `toolkit/mint/send_mint_tx.py` |
| Create, fund, sweep and batch-transfer wallets | `ethereum-wallet-operations` | `toolkit/wallets/create_wallet.py` |
| Reconstruct wallet P&L (mints, buys, sells, FIFO, gas, both chains) | `ethereum-wallet-operations`, `ethereum-data-pipelines` | `toolkit/wallets/wallet_recon.py` |
| Build a wallet tracker / alert feed with no API keys | `ethereum-data-pipelines`, `wallet-radar-operations` | — |
| Audit a minter or collection for wash trading, bots, allocation | `nft-minter-legitimacy-audit`, `nft-market-analysis` | `toolkit/analysis/minter_legitimacy.py` |
| Scope a floor sweep without spending | `nft-floor-sweep` | `toolkit/analysis/sweep_scope.py` |
| Measure real secondary volume keylessly | `ethereum-data-pipelines` | `toolkit/analysis/collection_volume.py` |
| Vet a collection call, a dev link, or a FUD claim with evidence | `nft-collection-price-analysis`, `web3-claim-verification` | — |
| Design and produce a collection (traits, pricing, drop mechanics) | `nft-collection-production`, `nft-trait-taxonomy`, `nft-trait-curation` | `toolkit/rarity/trait_sampler.py`, `toolkit/contracts/*` |
| Deploy a decaying-price mint contract | `nft-collection-production` → `decaying-price-mint.md` | `toolkit/contracts/DecayedMint.sol` |
| Register an agent identity and sign writes (DID / did:key) | `agent-protocol-identity` | `toolkit/did/flop-labs-sign.py` |
| Build a mint-intelligence dashboard product | `ethereum-data-pipelines`, `mint-field-guide` | — |

Two complete applications are documented in `skills/software-development/`:
**Rh Mint Command Center** ("Mint Room" — a local-first mint operations console
with a rarity sniper, wallet fleet manager, SeaDrop planner and queue worker) and
**Mint Field Guide** (a read-only mint/market intelligence dashboard). Their
source lives in separate repositories; the skills here carry the architecture,
the pitfalls, and the acceptance criteria.

---

## 2. Layout

```
skills/            31 agent playbooks (SKILL.md + references/ + scripts/)
  web3/                    on-chain, NFT market, wallets, DID, ICP
  business/                floor sweeps, mint recon, secondary buys, reveals
  pow-mint-mining/         proof-of-work mint playbook + miner sources
  seadrop-rapid-mint/      multi-wallet SeaDrop kit
  research/                chain/protocol/game-economy research
  software-development/    the two flagship builds
  productivity/            delivery tooling
toolkit/           runnable code, grouped by job
  rarity/                  ranking engines + dashboard generator
  mint/                    SeaDrop fire tool, PoW mint tx broadcaster
  pow/                     keccak/sha256 miners (C, CUDA, Metal, Swift)
  sniper/                  secondary buy + Seaport fill diagnostics
  wallets/                 wallet creation, PnL reconstruction
  analysis/                volume, minter legitimacy, sweep scoping
  contracts/               Solidity + compile check
  did/                     did:key signed-write helper
SKILLS.md          generated index of every skill and its trigger
SECURITY.md        how secrets and keys are handled
```

Every `SKILL.md` starts with frontmatter whose `description` is the load trigger:

```yaml
---
name: nft-rarity-engine
description: Use for NFT rarity ranks, reveal snipes, rarity galleries.
---
```

---

## 3. Verified technical facts you can rely on

These were re-verified against live chains and endpoints, not copied from docs.

**Robinhood Chain (4663)**
- RPC `https://rpc.mainnet.chain.robinhood.com`. It **hard-rate-limits per IP**
  (429 on reads *and* writes) — this is the single most common failure in the
  skills. Batch, back off, and prefer the explorer APIs for history.
- Python `urllib` requests to this RPC return **403 without a browser
  `User-Agent`**. `curl` sends one automatically, so curl-only testing hides the
  bug. This applies to the RPC *and* the OpenSea API.
- Explorer API: `https://robinhoodchain.blockscout.com/api/v2`
  (`creator_address_hash`, `creation_transaction_hash`, `/tokens/{addr}/transfers`,
  `/holders`). For user-facing tx links use **`robinscan.io`**, not Blockscout.
- SeaDrop singleton: `0x00005EA00ac477b1030ce78506496e8c2de24bf5`
  - `getPublicDrop` = `0xbc6a629c`, `mintPublic(address)` = `0xa06cb719`
  - `PublicDropUpdated` topic0 = `0x8764214b5defe9caa9c5b38b36f0cc5e482a8ab15d78696659e61989e48e6e70`
    (data = 6 ABI words: price, start, end, maxPerWallet, feeBps, restrictFeeRecipients)
  - `SeaDropMint` topic0 = `0xe90cf9cc0a552cf52ea6ff74ece0f1c8ae8cc9ad630d3181f55ac43ca076b7d6`
- Seaport 1.6: `0x0000000000000068f116a894984e2db1123eb395`
- ERC-721/20 `Transfer` topic0 = `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`
- Ink chain: RPC `https://rpc-gel.inkonchain.com` (chainId `0xdef1`),
  explorer `https://explorer.inkonchain.com/api/v2`.

**Rarity — the formula that matters**
- OpenSea's rarity tab is **OpenRarity information content**:
  `score = Σ −log₂(count / total)`, lower score = rarer.
- A trait-frequency `1/pct` heuristic looks plausible and is **wrong** — it
  produced ranks that disagreed with OpenSea and was retired. Do not ship it.
- Verify before publishing: hype the trait-count totals against OpenSea
  hydration. One token with empty traits skewed hundreds of ranks.
- `toolkit/rarity/` is validated rank-for-rank against OpenSea on a 5000-token
  collection.

**OpenSea API v2**
- Keyless: `/collections/{slug}` and `/collections/{slug}/stats` work with no
  header. Slug → contract also comes from the `urql_transport` hydration blobs on
  the collection page (brace-count the `push(...)` JSON objects; never regex
  40-hex out of raw HTML).
- Keyed (`X-API-KEY`): per-token, per-listing and events endpoints 401 without
  it. Live listings on Robinhood Chain come from the **events feed**
  (`/api/v2/events/collection/{slug}?event_type=listing`) — the orders endpoints
  return 405/404 there.
- Payload key is `asset_events`, not `events`. The `next` cursor is opaque
  base64 and must be passed as `&next=`.
- Trading: buy = `/listings/fulfillment_data` → Seaport `fulfillAdvancedOrder`;
  list = `/listings/actions` → EIP-712 sign → `POST /orders/robinhood/seaport/listings`.
  A missing `setApprovalForAll(contract, Seaport, true)` makes listing return
  HTTP 500 collection-wide.
- Free agent keys expire after 7 days — treat them as rotating, not durable.

**IPFS gateways** (they differ per network and go down)
- Working from this environment: `gateway.pinata.cloud`, `{cid}.ipfs.w3s.link`.
- `nftstorage.link` started 403ing, `ipfs.io` / `dweb.link` / Cloudflare's
  gateway failed. Always keep a chain of gateways, and fall back to OpenSea's
  per-token endpoint when every gateway is blocked.

**Proof-of-work mints**
- FAB4200-style: broadcast `mint(nonce)` with `value = 0`; the contract checks
  `keccak256(...) < target`. `eth_estimateGas` with a dummy nonce reverts with
  `BelowFloor(uint8,uint8)` (selector `0xfcf93064`) — that revert **confirms your
  calldata, from-address and gas path are correct** without spending anything.
- Hashcats-style: `keccak256(miner20 ‖ nonce32 ‖ prev32 ‖ anchor32) < target`,
  where `prev` is the previous token's winning work. Sequential, not parallel.
- At 40-bit difficulty expect ~1.1e12 hashes per solve. GPU/Metal miners in
  `toolkit/pow/` reach the range where this is a coin flip per round, not a
  guarantee. Never describe a PoW mint as profitable — it is a lottery ticket
  with an expected-negative cost.

---

## 4. Safety model (read before running anything that spends)

1. **Keys never live in a repo.** The convention throughout is raw hex in
   `~/.hermes/secrets/<name>_key`, `chmod 600`, read at runtime by path. This
   repository contains **no** private keys, seeds, API keys, tokens, or webhooks —
   `SECURITY.md` documents the audit that proves it and how to re-run it.
2. **`eth_call` before every broadcast.** Every buying/minting script here
   simulates first. A clean simulation is the requirement, not a nice-to-have: it
   is what catches stale orders, wrong price, wrong chain, and encoding mistakes.
   Read-only paths are safe; anything that moves money ships disabled behind an
   explicit `--send` / `--fire` / arm flag.
3. **Bounded, expiring authority.** The pattern used in production is: authorize
   a maximum total spend and a TTL before the window opens, then refuse to exceed
   either. Caps are hard-coded constants in the scripts (`MAX_PER_BUY_ETH`,
   `DAILY_CAP_ETH`, reserve floors).
4. **Check the wallet's real balance on-chain first.** A dispatch gate that read
   the balance before planning turned "buy as many as you can" into a bounded,
   honest 5-token plan instead of a failed batch.
5. **Free mints still get an approval.** Zero cost is not zero consequence — it
   is a public, irreversible transaction.
6. **Do not script gate bypasses.** Geoblocks, declaration gates and social
   gates are documented so you can recognise them and stop, not defeat them.
7. **A repo's README is marketing.** Auditing mint bots found the demo surface
   overstating the engine (extension never called its own stats endpoint; the
   scheduler sent a stale plan). Audit the code, not the claims.

---

## 5. Quickstart

```bash
git clone <this repo> && cd nft-mint-rarity-toolkit

# optional: an OpenSea key unlocks per-token traits, listings and trading
mkdir -p ~/.hermes/secrets && chmod 700 ~/.hermes/secrets
printf '%s' 'YOUR_OPENSEA_KEY' > ~/.hermes/secrets/opensea_key
chmod 600 ~/.hermes/secrets/opensea_key

# rank a collection you own (no key needed for the keyless paths)
python3 toolkit/rarity/rarity_engine.py compute
HELD="12,44,91" python3 toolkit/rarity/gen_dash.py   # writes dashboard_out.html

# read-only recon before anything else
python3 toolkit/analysis/collection_volume.py <contract> 3000000
python3 toolkit/analysis/minter_legitimacy.py <contract> <deploy_block>
python3 toolkit/analysis/sweep_scope.py <opensea-slug>

# mint tooling (simulation by default; --send / --fire to broadcast)
python3 toolkit/mint/seadrop_fire.py recon  <collection>
python3 toolkit/mint/seadrop_fire.py wallet <collection> 3
python3 toolkit/mint/send_mint_tx.py <keyfile> <nonce>          # dry-run
python3 toolkit/mint/send_mint_tx.py <keyfile> <nonce> --send

# miners
cc -O3 -o pow_miner toolkit/pow/pow_miner.c && ./pow_miner --help
```

Python scripts use the standard library only unless a docstring says otherwise
(`eth-account`, `coincurve`, `pycryptodome` for signing paths). Nothing here
requires a hosted service.

---

## 6. Honest limitations

- **This is one operator's field notes, not a product.** Some references cite
  the operator's private repositories (`rh-mint-command-center`,
  `mint-field-guide`) or local paths under `~/.hermes/`. Those repos are not part
  of this release; the skills are written so the technique stands on its own.
- **Wallet addresses in the skills are placeholders.** `0x1111…`, `0x2222…` and
  similar stand in for the addresses the operator actually used, so that the
  narrative stays readable without publishing anyone's holdings — including
  third parties who were analysed.
- **Timestamps matter.** Robinhood Chain, its RPC limits, and OpenSea's API all
  changed repeatedly during this work. Where a fact is dated, re-verify it before
  relying on it. Several skills explicitly record a finding that was later
  overturned (a mis-read mint price, a wrong rarity formula, a sniper path that
  reverted 49/49 times) because the correction is the useful part.
- **Nothing here is financial advice, and no strategy in it is profitable by
  construction.** The snipers, sweeps and lotteries are documented with their
  real loss modes.
- **Licensing:** MIT. Bundled third-party references keep their own terms.

## 7. Contributing

Add a skill as `skills/<category>/<name>/SKILL.md` with the trigger in the
frontmatter `description`, and put any code it needs in `scripts/` or `toolkit/`.
Before proposing anything public: run the secret audit described in
[`SECURITY.md`](SECURITY.md). Private keys belong in `~/.hermes/secrets/`, never
in a file.
