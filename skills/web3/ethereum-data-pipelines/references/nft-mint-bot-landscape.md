# NFT Mint-Bot Landscape (open-source sniper + commercial SaaS)

Surveyed 2026-08-15 while planning the case-study collection's mint tooling. Two reference points:
the open-source SeaDrop sniper (morsyxbt/nft-public-mint) and the commercial
browser SaaS umi.bot. Both are "execute a mint faster than other people" tools;
know what each does, what it CANNOT do, and what the shared race dynamics are.

## morsyxbt/nft-public-mint (open-source, TypeScript/ethers v6, ~1200 LOC)

- **What it does:** snipes PUBLIC SeaDrop stages on Ethereum/Base/Robinhood
  Chain. Builds `mintPublic()` calldata LOCALLY from on-chain reads
  (`getPublicDrop`, `getAllowedFeeRecipients` on the SeaDrop singleton
  `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5`), pre-signs every wallet's tx
  BEFORE the stage opens, then at T-0 blasts raw signed txs to all RPC
  endpoints simultaneously (fire-and-forget `eth_sendRawTransaction`), with
  socket warmers + sub-ms spin-wait timer. Multi-wallet parallel.
- **Why the local-calldata trick matters:** the OpenSea API path needs an
  access token + a ~1s API round-trip on the critical path. Building calldata
  on-chain means at T-0 the only work left is writing bytes to sockets.
- **Safety checks (well-built):** keys pasted at runtime, memory only; RPC
  chain-id probe per endpoint (wrong-chain dropped, send-only sequencers kept
  for blasting); pre-fire affordability check (node reserves
  `gasLimit × maxFee + mintPrice` — it refuses underfunded wallets); won't
  offer "fire now" before the stage opens; EIP-1559 ceiling/tip validation.
- **Limits (read before assuming it does more):**
  - PUBLIC SeaDrop stages ONLY. No allowlist/FCFS — `mintSigned()` needs an
    OpenSea-generated per-wallet signature, genuinely impossible locally
    (README admits this).
  - No custom mint contracts (any drop with its own `mint()` is invisible);
  - No RH launchpad fee-split paid mints (the pattern detected in
    mint-market-dashboard via fixed-recipient ERC20/ETH transfers);
  - No discovery/automation (paste a link manually), no retry/gas-bump,
    no private mempool send, no post-mint exit automation.
- **License trap:** package.json says MIT but the repo has NO LICENSE file —
  treat as reference material, rewrite your own implementation.
- **Tweet economics are marketing:** "99% of public RH NFTs do 5-6x, make
  $70-700" is unverifiable (no data, no tracking, no examples). The real edge
  is private-RPC speed + wallet count + drop selection — the script is the
  loader, the race is still a race, and the 70+ forks are the competition.

## umi.bot (commercial browser SaaS, by Geauser, successor to Misei on SEI)

- **What it is:** Nuxt SPA "ultimate minting bot"; connect wallet (auth only),
  paste a launchpad link, schedule; mints run server-side even with the
  browser closed. QuickNode enterprise + colocated RPC, local anvil
  simulation before sending, gas estimated at fire time.
- **Coverage:** 21 chains incl. Robinhood; launchpads OpenSea, Hyperlaunch
  (Drip), Blever, Scatter, Mintify, Ronin, Poply, Rarible, Puffles, LiquidFi,
  Transient, OddsLaunchpad. **Handles OpenSea ALLOWLIST mints** by fetching the
  mint payload from launchpad servers via fast proxies — the capability the
  open-source tool says is impossible locally.
- **Pricing (USDC, on-chain activation):** 1-day 12 (8 wallets, priority +6) /
  weekly 59 (75 wallets, +30) / monthly 149 (200 wallets, priority included).
  Up to 500 wallets. Purchases were temporarily paused at survey time.
- **Security model (has FUD history):** FAQ links an "original claim" +
  "founder's response" — a competitor accused key theft. Their design:
  sync-stored keys encrypted client-side with wallet signature (staff can't
  decrypt) + temporary mint storage encrypted with Umi's secret, auto-deleted.
  Honest: failed mints burn ~20-30% of gas; no refunds unless Umi bug.
- **Flags:** "gets around all anti-bot incl. captchas" is the industry arms-race
  claim (unverifiable, dies when launchpads update); Disperse tool "has known
  issues that cannot be fixed right now" (their words); no direct contract
  minting yet (launchpad-only).

## Shared race dynamics (for "should I build or buy?")

- FCFS chains (Abstract, Apechain, MegaETH, RH-style): inclusion = lowest
  latency to the sequencer; private/colocated RPC wins.
- Gas-based chains (Ethereum, Monad, Berachain): success = gas-setting
  competition against other botters.
- Allowlist stages break the local-calldata approach — they need a launchpad
  signature/payload per wallet. That is the key fork in the road between the
  open-source tool (public only) and commercial tools (allowlist-capable).

## Defense takeaway for the case-study collection's OWN drops

The same knowledge that builds a sniper tells you how to stop one:
allowlist/mintSigned stages, per-wallet caps (`maxTotalMintableByWallet`),
restricted fee recipients (`restrictFeeRecipients=true` + custom allowlist),
or a custom mint contract (defeats the SeaDrop-singleton bot entirely);
surprise/last-minute timing; monitor for dev-fronted mint + wash rings (see
`dev-fronted-mint-wash-trade-forensics.md`).

## Related project files (2026-08-15)

- `~/Projects/casestudy-mint-sniper/PLAN-claude-review.md` —
  fork+harden plan (M0-M6, defense first, kill-gates) for Claude review.
- `~/Projects/casestudy-mint-sniper/COLLECTION-NOTES-PLAN-v2.md`
  — the collection-forensics pipeline (BRHD-style notes on demand) plan +
  Claude review prompt.
