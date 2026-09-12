# NFT Smart-Wallet Watchlists

Use this note when bootstrapping and maintaining wallet intelligence for Ethereum NFT mint dashboards.

## Bootstrap principle

A public reputation is a discovery lead, not a permanent score. Seed only wallets with a public, linkable attribution trail and a relevant history as a collector, trader, or early minter. After a short bootstrap period, rank and retain them from rolling on-chain evidence.

Avoid celebrity wallets selected only for fame. Keep individual collectors, funds/DAOs, project treasuries, market makers, and marketplace contracts in separate cohorts because their objectives and information access differ.

## Attribution standard

For every candidate store:

- exact checksummed address and chain;
- public identity or pseudonym;
- source URL, publisher, publication date, and retrieval date;
- what the source actually proves: identity, primary wallet, historic holdings, or trading behavior;
- confidence level and known alternate/linked wallets;
- whether the address is an EOA, smart account, multisig, treasury, or contract.

Preferred evidence, strongest first:

1. First-party signed statement, official profile, or durable identity record linking the person to the address.
2. A reputable publication that explicitly prints or links the address as that person's wallet.
3. Public ENS forward resolution plus reverse record/social records and a matching public marketplace profile.
4. Analytics-provider attribution corroborated by another independent public source.

ENS resolution is mutable. Record the resolution time and never assume the current ENS destination contains the historic collection. Search-result snippets are discovery aids, not final proof. A nonzero nonce and EOA bytecode check confirm an active account type, not ownership.

## Initial tier discipline

- **Core:** strong attribution plus documented relevant behavior; eligible for prominent alerts only while rolling score remains strong.
- **Context:** credible collector or long-term-conviction signal, but sparse, passive, old, or not clearly mint-oriented.
- **Probation:** public attribution exists but performance evidence is insufficient; collect silently until qualified.

Do not infer mint skill from collection value alone. Historic blue-chip holdings can reflect capital, longevity, or concentration rather than repeatable early selection.

## Genuine-mint classification

Count a mint observation only when:

1. The wallet initiated or authorized the transaction.
2. An ERC-721 or ERC-1155 transfer from the zero address delivered the token.
3. Mint payment, call, and receipt can be connected in the same transaction or protocol flow.
4. The collection is not spam, impersonation, or an unsolicited airdrop.
5. Related-wallet transfers and self-project activity are labeled separately.

Transfer logs alone are insufficient: prominent wallets receive spam designed to resemble mints. Separate paid mints, free mints, allowlist claims, airdrops, and self-ecosystem transactions.

## Rolling 0-100 model

Evaluate each distinct project at fixed 7-, 30-, and 90-day horizons. Entry cost includes mint payment and gas. Use realized proceeds when sold; otherwise use conservative executable value supported by multiple arm's-length trades. Mark illiquid outcomes `unpriced` rather than inventing a floor value.

Suggested components:

- 30% risk-adjusted net return;
- 20% Bayesian-smoothed hit rate versus both an absolute return hurdle and a market benchmark;
- 15% early-entry edge by unique-minter order/time percentile;
- 15% consistency across unrelated projects, net of volatility and concentration;
- 10% liquidity quality based on unrelated buyers and meaningful volume;
- 10% recency/activity with exponential decay (about a 60-day half-life);
- up to -40 points for wash trading, self-dealing, sponsored allocations, spam, sybil clusters, suspicious counterparties, or extreme concentration.

Winsorize project returns and convert components to cohort percentiles so one extreme trade cannot dominate. Suggested confidence gate: at least 12 evaluated projects in 180 days, 5 priced outcomes, and 3 unrelated creator/project clusters. Shrink small samples toward the cohort mean.

Example tier thresholds:

- Core: score >=75 with evidence gate met and no severe integrity flag.
- Context: 55-74, or >=75 with insufficient sample.
- Probation: 40-54 or reputation-seeded observation.
- Remove from active alerts: <40, no qualifying mint for 120 days, or serious integrity evidence.

Require a threshold to persist through two weekly evaluations before promotion or demotion.

## Alert presentation

Expose the wallet's recent score, sample size, confidence, qualifying reason, entry percentile, priced versus unpriced outcomes, and integrity flags. State whether one wallet or several independent wallets corroborate the mint. Never imply that wallet activity is financial advice or a contract-security review.
