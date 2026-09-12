# NFT Mint & Rarity Toolkit

Agent playbooks and working code for on-chain NFT work: minting, rarity ranking,
reveal sniping, proof-of-work mints, wallet operations, and on-chain forensics.

This is not a library with an API. It is what one AI agent learned doing this work
for real, plus the scripts that did it. Every claim in the skills has a date and a
specific collection, transaction, or endpoint response behind it, including the
claims that turned out to be wrong.

If you are an agent picking this up: [`SKILLS.md`](SKILLS.md) indexes every skill
and its trigger. Load the relevant `SKILL.md` before doing the work, and use what
is already in `toolkit/` instead of writing the plumbing again.

Most of it targets **Robinhood Chain (chain id 4663)**, an Arbitrum Orbit
rollout. There is also material for Ethereum mainnet and Ink.

---

## What is in here

| Capability | Skill(s) | Code |
|---|---|---|
| Rank a collection by rarity, matching OpenSea | `nft-rarity-engine`, `ethereum-data-pipelines` | `toolkit/rarity/rarity_engine.py`, `combox_rarity.py`, `bakemono_rarity.py` |
| Catch a reveal when metadata flips, then sweep and rank it | `nft-rarity-engine`, `rh-chain-rarity-sniping` | `toolkit/rarity/rarity_engine.py watch` |
| Buy rare tokens at or near floor after a reveal | `rh-chain-rarity-sniping`, `nft-secondary-buy` | `toolkit/sniper/buy_secondary.py`, `probe_fill.py` |
| Run a SeaDrop public mint across many wallets at T-0 | `seadrop-rapid-mint`, `nft-mint-recon` | `toolkit/mint/seadrop_fire.py` |
| Mint a custom contract | `rh-mint-command-center`, `nft-mint-recon` | see `skills/software-development/rh-mint-command-center` |
| Work out how an unknown mint site works and mint it | `ethereum-data-pipelines` → `free-mint-site-reverse-engineering.md` | |
| Mine a proof-of-work mint | `pow-mint-mining`, `onchain-puzzle-mining` | `toolkit/pow/*` (C, CUDA, Metal, Swift) |
| Solve a puzzle, claim gate, or refund allocation | `onchain-puzzle-solving`, `onchain-claim-reverse-engineering` | `toolkit/pow/*`, `toolkit/mint/send_mint_tx.py` |
| Create, fund, sweep, and batch-transfer wallets | `ethereum-wallet-operations` | `toolkit/wallets/create_wallet.py` |
| Reconstruct wallet P&L (mints, buys, sells, gas, both chains) | `ethereum-wallet-operations`, `ethereum-data-pipelines` | `toolkit/wallets/wallet_recon.py` |
| Watch wallets and alert on buys, with no API keys | `ethereum-data-pipelines`, `wallet-radar-operations` | |
| Audit a collection for wash trading, bots, allocation | `nft-minter-legitimacy-audit`, `nft-market-analysis` | `toolkit/analysis/minter_legitimacy.py` |
| Scope a floor sweep without spending | `nft-floor-sweep` | `toolkit/analysis/sweep_scope.py` |
| Measure real secondary volume keylessly | `ethereum-data-pipelines` | `toolkit/analysis/collection_volume.py` |
| Vet a collection call, a dev link, or a scam accusation | `nft-collection-price-analysis`, `web3-claim-verification` | |
| Design and produce a collection | `nft-collection-production`, `nft-trait-taxonomy`, `nft-trait-curation` | `toolkit/rarity/trait_sampler.py`, `toolkit/contracts/*` |
| Deploy a decaying-price mint contract | `nft-collection-production` → `decaying-price-mint.md` | `toolkit/contracts/DecayedMint.sol` |
| Register an agent identity and sign writes (did:key) | `agent-protocol-identity` | `toolkit/did/flop-labs-sign.py` |
| Build a mint intelligence dashboard | `ethereum-data-pipelines`, `mint-field-guide` | |

`skills/software-development/` documents two full applications: **Rh Mint Command
Center** (a local-first mint operations console with a rarity sniper, wallet fleet
manager, SeaDrop planner, and queue worker) and **Mint Field Guide** (a read-only
mint and market intelligence dashboard). Their source is in separate repos. What
is here is the architecture, the pitfalls, and the acceptance criteria.

To run any of this on your own agent, [`INSTALL.md`](INSTALL.md) walks through a
VPS, Hermes, Discord, and installing the skills in one command. [`site/`](site/)
holds a single-file landing page you can deploy to Vercel or Cloudflare Pages.

---

## Layout

```
skills/            31 agent playbooks (SKILL.md + references/ + scripts/)
  web3/                    on-chain, NFT market, wallets, DID, ICP
  business/                floor sweeps, mint recon, secondary buys, reveals
  pow-mint-mining/         proof-of-work mint playbook + miner sources
  seadrop-rapid-mint/      multi-wallet SeaDrop kit
  research/                chain, protocol, and game-economy research
  software-development/    the two flagship builds
  productivity/            delivery tooling
toolkit/           runnable code, grouped by job
  rarity/                  ranking engines and dashboard generator
  mint/                    SeaDrop fire tool, PoW mint broadcaster
  pow/                     keccak and sha256 miners (C, CUDA, Metal, Swift)
  sniper/                  secondary buy and Seaport fill diagnostics
  wallets/                 wallet creation, P&L reconstruction
  analysis/                volume, minter legitimacy, sweep scoping
  contracts/               Solidity and compile check
  did/                     did:key signed-write helper
SKILLS.md          generated index of every skill and its trigger
INSTALL.md         VPS, Hermes, Discord, and skills setup
SECURITY.md        how secrets and keys are handled
```

Every `SKILL.md` opens with frontmatter, and the `description` field is the
trigger for loading it:

```yaml
---
name: nft-rarity-engine
description: Use for NFT rarity ranks, reveal snipes, rarity galleries.
---
```

---

## Facts checked against live chains

These were checked against live chains and endpoints. Where a fact is dated,
re-check it, because this ecosystem moves.

**Robinhood Chain (4663)**

- RPC is `https://rpc.mainnet.chain.robinhood.com`. It rate-limits per IP, on
  reads and writes alike, and returns 429. This is the most common failure in the
  skills. Batch your calls, back off, and prefer the explorer APIs for history.
- Requests from Python `urllib` get 403 without a browser `User-Agent`. This
  applies to the RPC and to the OpenSea API. Curl sends one automatically, so
  testing with curl hides the bug.
- Explorer API: `https://robinhoodchain.blockscout.com/api/v2`, which exposes
  `creator_address_hash`, `creation_transaction_hash`, `/tokens/{addr}/transfers`
  and `/holders`. For links you show a user, use `robinscan.io` instead.
- SeaDrop singleton: `0x00005EA00ac477b1030ce78506496e8c2de24bf5`
  - `getPublicDrop` is `0xbc6a629c`; `mintPublic(address)` is `0xa06cb719`
  - `PublicDropUpdated` topic0 is `0x8764214b5defe9caa9c5b38b36f0cc5e482a8ab15d78696659e61989e48e6e70`.
    The data is 6 ABI words: price, start, end, maxPerWallet, feeBps, restrictFeeRecipients
  - `SeaDropMint` topic0 is `0xe90cf9cc0a552cf52ea6ff74ece0f1c8ae8cc9ad630d3181f55ac43ca076b7d6`
- Seaport 1.6 is at `0x0000000000000068f116a894984e2db1123eb395`
- ERC-721 and ERC-20 `Transfer` topic0 is `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`
- Ink: RPC `https://rpc-gel.inkonchain.com` (chainId `0xdef1`), explorer
  `https://explorer.inkonchain.com/api/v2`

**Rarity**

- OpenSea's rarity tab is OpenRarity information content:
  `score = Σ −log₂(count / total)`. Lower is rarer.
- A trait-frequency `1/pct` heuristic looks reasonable and is wrong. It produced
  ranks that disagreed with OpenSea, and it was retired. Do not ship it.
- Check your trait-count totals against OpenSea hydration before you publish a
  ranking. One token with empty traits moved hundreds of ranks.
- `toolkit/rarity/` was validated rank-for-rank against OpenSea on a 5000-token
  collection.

**OpenSea API v2**

- `/collections/{slug}` and `/collections/{slug}/stats` work with no key. Slug to
  contract also works keylessly, from the `urql_transport` hydration blobs on the
  collection page. Brace-count those `push(...)` JSON objects; do not regex 40-hex
  out of raw HTML.
- Per-token, per-listing, and events endpoints return 401 without `X-API-KEY`. On
  Robinhood Chain, live listings come from the events feed
  (`/api/v2/events/collection/{slug}?event_type=listing`). The orders endpoints
  return 405 or 404 there.
- The payload key is `asset_events`, not `events`. The `next` cursor is opaque
  base64 and has to be passed as `&next=`.
- Buying is `/listings/fulfillment_data` into Seaport `fulfillAdvancedOrder`.
  Listing is `/listings/actions`, then an EIP-712 signature, then
  `POST /orders/robinhood/seaport/listings`. If `setApprovalForAll(contract,
  Seaport, true)` is missing, listing fails with an HTTP 500 for the whole
  collection.
- Free agent keys expire after 7 days. Treat them as rotating, not permanent.

**IPFS gateways**

They behave differently per machine and they go down. What worked here:
`gateway.pinata.cloud` and `{cid}.ipfs.w3s.link`. `nftstorage.link` began
returning 403, and `ipfs.io`, `dweb.link`, and Cloudflare's gateway all failed.
Keep a chain of gateways, and fall back to OpenSea's per-token endpoint when every
gateway is blocked.

**Proof-of-work mints**

- FAB4200-style contracts take `mint(nonce)` with `value = 0` and accept when
  `keccak256(...) < target`. Calling `eth_estimateGas` with a dummy nonce reverts
  with `BelowFloor(uint8,uint8)`, selector `0xfcf93064`. That revert is useful: it
  confirms your calldata, from-address, and gas path are correct, and it reports
  live difficulty, without spending anything.
- Hashcats-style contracts use
  `keccak256(miner20 ‖ nonce32 ‖ prev32 ‖ anchor32) < target`, where `prev` is the
  previous token's winning work. The chain is sequential, so it cannot be
  parallelized across tokens.
- At 40-bit difficulty, expect around 1.1e12 hashes per solve. The GPU and Metal
  miners in `toolkit/pow/` are fast enough to make a round close to a coin flip.
  That is still a lottery ticket with a negative expected cost, and it should not
  be described any other way.

---

## Safety notes

1. Keys never live in a repository. The convention throughout is raw hex in
   `~/.hermes/secrets/<name>_key`, `chmod 600`, read at runtime by path. This repo
   contains no private keys, seeds, API keys, tokens, or webhooks. `SECURITY.md`
   documents the audit that proves it and how to run it yourself.
2. Every script that spends simulates with `eth_call` first. That is a
   requirement, not a nicety. It is what catches stale orders, wrong prices, wrong
   chains, and encoding mistakes. Read-only paths are safe to run; anything that
   moves money ships disabled behind an explicit `--send`, `--fire`, or arm flag.
3. Caps are hard constants in the scripts: `MAX_PER_BUY_ETH`, `DAILY_CAP_ETH`,
   reserve floors. Production use authorized a maximum total spend and a TTL
   before a window opened, then refused to exceed either.
4. Check the funded wallet's real balance on chain before planning. A gate that
   read the balance first turned "buy as many as you can" into an honest five-token
   plan instead of a failed batch.
5. A free mint is still an irreversible public transaction and still needs an
   approval.
6. Geoblocks, declaration gates, and social gates are documented so you recognize
   them and stop. Do not script a way around them.
7. Audit mint bots by reading the code. One audited sniper's demo surface
   overstated its engine: the extension never called its own stats endpoint, and
   its scheduler sent a stale plan.

---

## Quickstart

```bash
git clone <this repo> && cd nft-mint-rarity-toolkit

# optional: an OpenSea key unlocks per-token traits, listings, and trading
mkdir -p ~/.hermes/secrets && chmod 700 ~/.hermes/secrets
printf '%s' 'YOUR_OPENSEA_KEY' > ~/.hermes/secrets/opensea_key
chmod 600 ~/.hermes/secrets/opensea_key

# rank a collection you own (keyless paths need no key)
python3 toolkit/rarity/rarity_engine.py compute
HELD="12,44,91" python3 toolkit/rarity/gen_dash.py   # writes dashboard_out.html

# read-only recon, run these first
python3 toolkit/analysis/collection_volume.py <contract> 3000000
python3 toolkit/analysis/minter_legitimacy.py <contract> <deploy_block>
python3 toolkit/analysis/sweep_scope.py <opensea-slug>

# mint tooling (simulates by default; --send / --fire broadcasts)
python3 toolkit/mint/seadrop_fire.py recon  <collection>
python3 toolkit/mint/seadrop_fire.py wallet <collection> 3
python3 toolkit/mint/send_mint_tx.py <keyfile> <nonce>          # dry run
python3 toolkit/mint/send_mint_tx.py <keyfile> <nonce> --send

# miners
cc -O3 -o pow_miner toolkit/pow/pow_miner.c && ./pow_miner --help
```

Python scripts use the standard library only, unless the docstring says
otherwise. The signing paths need `eth-account`, `coincurve`, and `pycryptodome`.
Nothing here needs a hosted service.

---

## Limits

- These are one operator's field notes. Some references cite that operator's
  private repositories (`rh-mint-command-center`, `mint-field-guide`) or paths
  under `~/.hermes/`. Those repos are not part of this release. The skills are
  written so the technique stands without them.
- Wallet addresses in the skills are placeholders. `0x1111…`, `0x2222…` and
  similar stand in for the addresses actually used, so the narrative stays
  readable without publishing anyone's holdings, including third parties who got
  analyzed.
- Dates matter. Robinhood Chain, its RPC limits, and OpenSea's API all changed
  repeatedly during this work. Several skills record a finding that was later
  overturned: a misread mint price, the wrong rarity formula, a sniper path that
  reverted 49 times out of 49. The corrections are kept because they are the
  useful part.
- Nothing here is financial advice, and no strategy in it is profitable by
  construction. The snipers, sweeps, and lotteries are documented with their real
  loss modes.
- License: MIT. Bundled third-party references keep their own terms.

## Contributing

Add a skill as `skills/<category>/<name>/SKILL.md`, with the trigger in the
frontmatter `description`, and put any code it needs in `scripts/` or `toolkit/`.
Before proposing anything public, run the secret audit described in
[`SECURITY.md`](SECURITY.md). Private keys belong in `~/.hermes/secrets/`, never in
a file.
