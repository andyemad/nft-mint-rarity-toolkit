# Skill index

31 skills ship in this repository. Each is a `SKILL.md`
playbook an agent loads before doing the work, plus the
`references/` and `scripts/` that go with it. Paths below are relative
to `skills/`.

## On-chain / NFT core

### `agent-protocol-identity`
- **Path:** `skills/web3/agent-protocol-identity`
- **Load when:** Onboard an agent to a did:key protocol with signed writes.
- **Depth:** 153 lines of playbook, 3 supporting files

### `ethereum-data-pipelines`
- **Path:** `skills/web3/ethereum-data-pipelines`
- **Load when:** Use for NFT/mint dashboards with no-key on-chain data.
- **Depth:** 127 lines of playbook, 57 supporting files

### `ethereum-wallet-operations`
- **Path:** `skills/web3/ethereum-wallet-operations`
- **Load when:** Use when creating, backing up, or sending assets from EVM wallets. Handles local keys, verification, and safe transfers.
- **Depth:** 121 lines of playbook, 5 supporting files

### `flop-technocore-agent-ops`
- **Path:** `skills/web3/flop-technocore-agent-ops`
- **Load when:** Use for technocore.chat / FLOP: DIDs, posts, checks, X spread via @bidetusersunite.
- **Depth:** 206 lines of playbook, 2 supporting files

### `internet-computer-development`
- **Path:** `skills/web3/internet-computer-development`
- **Load when:** Use when building or researching ICP blockchain apps.
- **Depth:** 155 lines of playbook, 2 supporting files

### `nft-collection-price-analysis`
- **Path:** `skills/web3/nft-collection-price-analysis`
- **Load when:** Use when deciding if a live NFT collection is a buy.
- **Depth:** 308 lines of playbook, 2 supporting files

### `nft-collection-production`
- **Path:** `skills/web3/nft-collection-production`
- **Load when:** Use when creating/minting an anonymous NFT collection.
- **Depth:** 293 lines of playbook, 13 supporting files

### `nft-exit-discipline`
- **Path:** `skills/web3/nft-exit-discipline`
- **Load when:** Use when Emad trades or sells NFTs, or decides on an exit.
- **Depth:** 43 lines of playbook, 0 supporting files

### `nft-market-analysis`
- **Path:** `skills/web3/nft-market-analysis`
- **Load when:** Use when judging an NFT buy or predicting collection price.
- **Depth:** 164 lines of playbook, 6 supporting files

### `nft-minter-legitimacy-audit`
- **Path:** `skills/web3/nft-minter-legitimacy-audit`
- **Load when:** Use when asked "are these minters legit?" to vet a launch.
- **Depth:** 71 lines of playbook, 1 supporting files

### `nft-rarity-engine`
- **Path:** `skills/web3/nft-rarity-engine`
- **Load when:** Use for NFT rarity ranks, reveal snipes, rarity galleries.
- **Depth:** 220 lines of playbook, 6 supporting files

### `nft-trait-curation`
- **Path:** `skills/web3/nft-trait-curation`
- **Load when:** Use when auditing or approving NFT metadata trait drafts.
- **Depth:** 54 lines of playbook, 1 supporting files

### `nft-trait-taxonomy`
- **Path:** `skills/web3/nft-trait-taxonomy`
- **Load when:** Build/audit NFT trait taxonomies with vision passes.
- **Depth:** 161 lines of playbook, 4 supporting files

### `onchain-claim-reverse-engineering`
- **Path:** `skills/web3/onchain-claim-reverse-engineering`
- **Load when:** Use to solve on-chain mint, claim, and puzzle gates.
- **Depth:** 96 lines of playbook, 4 supporting files

### `onchain-puzzle-mining`
- **Path:** `skills/web3/onchain-puzzle-mining`
- **Load when:** Claim puzzle-gated NFTs; brute-force SHA-256 via Metal GPU.
- **Depth:** 74 lines of playbook, 4 supporting files

### `onchain-puzzle-solving`
- **Path:** `skills/web3/onchain-puzzle-solving`
- **Load when:** Solve computational puzzles gating on-chain mints/claims.
- **Depth:** 148 lines of playbook, 2 supporting files

### `seadrop-rapid-mint`
- **Path:** `skills/web3/seadrop-rapid-mint`
- **Load when:** Fire SeaDrop public mints fast with a fresh funded wallet.
- **Depth:** 39 lines of playbook, 0 supporting files

### `wallet-radar-operations`
- **Path:** `skills/web3/wallet-radar-operations`
- **Load when:** Use when operating, debugging, or changing Wallet Radar wallets, classifiers, alerts, valuation, delivery, or its live daemon.
- **Depth:** 277 lines of playbook, 9 supporting files

### `web3-claim-verification`
- **Path:** `skills/web3/web3-claim-verification`
- **Load when:** Use when verifying a crypto project's claims on-chain.
- **Depth:** 124 lines of playbook, 0 supporting files

## Mint + market execution

### `nft-floor-sweep`
- **Path:** `skills/business/nft-floor-sweep`
- **Load when:** Use when the user says "sweep this" or "buy the floor".
- **Depth:** 59 lines of playbook, 1 supporting files

### `nft-mint-recon`
- **Path:** `skills/business/nft-mint-recon`
- **Load when:** Use when Emad shares an NFT mint link to recon headlessly.
- **Depth:** 130 lines of playbook, 4 supporting files

### `nft-secondary-buy`
- **Path:** `skills/business/nft-secondary-buy`
- **Load when:** Buy an NFT off secondary (OpenSea/Robinhood) fast.
- **Depth:** 121 lines of playbook, 1 supporting files

### `rh-chain-rarity-sniping`
- **Path:** `skills/business/rh-chain-rarity-sniping`
- **Load when:** Use for RH Chain NFT reveals, ranking, and rare-sniping.
- **Depth:** 366 lines of playbook, 5 supporting files

## Chain + protocol research

### `onchain-game-economy-analysis`
- **Path:** `skills/research/onchain-game-economy-analysis`
- **Load when:** Map an onchain game's economy from Solidity source.
- **Depth:** 42 lines of playbook, 1 supporting files

### `polymarket`
- **Path:** `skills/research/polymarket`
- **Load when:** Query Polymarket: markets, prices, orderbooks, history.
- **Depth:** 77 lines of playbook, 2 supporting files

### `proof-of-play-archive`
- **Path:** `skills/research/proof-of-play-archive`
- **Load when:** Use when referencing Proof of Play, Pirate Nation, PopBot.
- **Depth:** 107 lines of playbook, 1 supporting files

### `pseudonym-identity-research`
- **Path:** `skills/research/pseudonym-identity-research`
- **Load when:** Profile pseudonymous identities across X, ENS, and wallets.
- **Depth:** 68 lines of playbook, 1 supporting files

## Flagship application builds

### `mint-field-guide`
- **Path:** `skills/software-development/mint-field-guide`
- **Load when:** Use when adding/editing code or tests in mint-field-guide.
- **Depth:** 324 lines of playbook, 15 supporting files

### `rh-mint-command-center`
- **Path:** `skills/software-development/rh-mint-command-center`
- **Load when:** Use when editing Mint Room code or running its mint engines.
- **Depth:** 1269 lines of playbook, 30 supporting files

## Delivery tooling

### `public-wallet-xlsx-delivery`
- **Path:** `skills/productivity/public-wallet-xlsx-delivery`
- **Load when:** Use when Emad pastes wallets. Deliver a public XLSX.
- **Depth:** 49 lines of playbook, 0 supporting files

## _standalone

### `pow-mint-mining`
- **Path:** `skills/pow-mint-mining`
- **Load when:** Use when an NFT mint requires mining a keccak PoW nonce.
- **Depth:** 51 lines of playbook, 5 supporting files

