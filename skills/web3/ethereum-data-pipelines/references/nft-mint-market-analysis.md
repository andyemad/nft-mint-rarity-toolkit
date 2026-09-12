# Reading the live NFT mint landscape (no-key, snapshot 2026-08-11)

How to use the same no-key sources as a READ-ONLY market researcher (not a
cloner): which endpoints give a live picture, what the fields mean, coverage
gotchas, and the on-chain tells for bot/farm activity. Data snapshot taken
2026-08-11 via direct curl of public JSON endpoints.

## Endpoints that give a live market picture (all JSON, no key)

MintGo public API (discover by grepping the frontend JS bundle for `/api/`):
- `/api/seadrop-radar?chain=<ethereum|robinhood>` — upcoming staged SeaDrop
  mints enriched with OpenSea metadata. Per drop: `displayName`, `supply`
  {minted, max}, `status`, `dropStagesJson` (per-stage `type`
  signed_presale/public_sale, `label`, `priceWei`, start/endTime,
  `maxPerWallet`), `twitterUrl`/`xUrl`, `openSeaSlug`, `explorerUrl`,
  `feeBps`.
- `/api/trending?window=1m&limit=20` — hot mints with `mintCount`, `txCount`,
  `uniqueMinters`, `volumeEth`, `floorPriceEth`, plus deployer stats
  (`deployerCreatedAgo`, `deployerNftProjectCount`).
- `/api/market-snapshot` — "runners" per window; `/api/runners` — real-time
  mint activity feed.

Magic Eden v2 (`https://api-mainnet.magiceden.dev/v2/collections?offset=0&limit=20&rankBy=7DayVolume`)
works without a key but requires offset/limit as multiples of 20. NOTE: in
2026-08 probes the returned collection objects had null stats fields — verify
the response shape on your own before trusting it.

## Coverage gotchas (critical for market analysis)

- `seadrop-radar` returns 0 items for base/arbitrum/optimism/polygon/solana/
  bitcoin — that means "no SeaDrop factory activity tracked there", NOT "no
  mints on that chain". Base mint activity runs through Zora (posts/creator
  coins), which SeaDrop radar does not see.
- SeaDrop-visible chains in Aug 2026: Ethereum L1 (~23 upcoming drops on
  2026-08-11) and Robinhood Chain (~89 drops — the biggest small-drop venue,
  mostly "Hood" meme PFPs). RH drops are priced in ETH-denominated wei and
  resolve on robinhoodchain.blockscout.com.

## Field semantics for reading a drop

- Standard stage convention: Team/Vault (free) → GTD (guaranteed, signed
  presale) → FCFS (wallet list) → Public. `maxPerWallet` 1 = scarcity play;
  20-200 = fill-rate play.
- Cross-project allowlists are the real distribution engine for small drops
  (stage labels literally name other communities: "OH NFT + PFP Holders",
  "stonk brokers, Mancers, pitboys, Zaibatsu Wagies", "top collection on
  robinhood").
- Pricing bands for small anonymous drops (Ethereum L1, Aug 2026): micro
  36-256 supply @ 0.0003-0.01 ETH; mid 222-3333 @ 0.0005-0.01; large PFP
  7777-10000 @ 0.0002-0.001; named artists run 1-2 orders higher (0.05-0.26
  ETH). Anonymous drops almost never price above ~0.01 ETH.
- Visual conventions: animated GIF PFPs dominate; meme/doomer naming
  (Hood/Broker/Copium/"TERMINAL GRIND: SECTOR 256 GRID-WAGIE TRADER");
  the generative fine-art lane is held by doxxed names (thankyouX, Amber
  Vittoria) — anonymous generative scene art was an empty lane in this snapshot.

## Bot / farm detection from the same fields

- `uniqueMinters` ≈ 1 while `mintCount` >> 1 → single-wallet self-mint
  (bot/scripted), NOT organic demand. Observed live 2026-08-11: #1 trending
  Ethereum collection had 81 mints / 2 txs / 1 unique minter.
- `deployerNftProjectCount` high (e.g. 34) + old deployer wallet → serial
  deployer/farmer, not a first-time creator.
- Organic signals to look for instead: mints spread across many unique
  wallets, natural secondary listings, community pushback/dissent.

## Collection health on OpenSea (organic vs manufactured)

The OpenSea page hydration JSON (`collectionBySlug`) carries the fields needed to
judge whether recent activity is real demand or manufactured. Parse them from the
rich fragment (the one containing both `stats` and `floorPrice`):

- `floorPrice.pricePerItem.token.unit` / `usd` — current floor.
- `stats.totalSupply`, `stats.ownerCount`, `stats.listedItemCount` — compute
  unique-ownership % (`ownerCount / totalSupply`) and % listed
  (`listedItemCount / totalSupply`). Very low unique-ownership (e.g. 723 owners
  on 10,000 supply = 7%) plus high % listed = concentration / overhang risk.
- `stats.oneMinute / fiveMinute / fifteenMinute / oneHour / oneDay / sevenDays`
  `volume` — concentration tells the story. If oneDay ≈ oneHour (nearly all
  lifetime volume in the last hour) it is a fresh breakout, not an established
  market.
- `stats.oneDay.floorPriceChange` — a large recent % move means late entries are
  chasing and early holders have room to dump.
- `drop.stages` + `activeDropStage.price` — mint price history. Compare current
  floor to mint: floor 147× mint with no durable demand is an early-holder exit
  signal, not a buy.

Cross-check the activity page (`collectionActivity.items`, `type == "SALE"`) for
concentration: count top-5 buyers and top-5 sellers as a share of sampled sales.
When the top five buyers take ~60% of purchases AND the top five sellers supply
~60%, treat it as manufactured (coordinated floor-setting / insider distribution)
regardless of headline volume. Spread buyers/sellers plus a real creator history
= credible demand.

Note: a collection slug can be suffixed (e.g. `smiles-341238239`), so parse the
slug from the `collectionBySlug` fragment rather than guessing it from the name.

## Trust-signal context (anonymous drops)

- Standard anonymous-project trust kit: audited SeaDrop protocol itself, open
  stage schedules, team vault visible on-chain, disclosed supply caps,
  etherscan/OpenSea links. Few add timelocks, renounced ownership, or
  open-source generation — those are the differentiators, and the no-team-
  allocation drop was an unserved niche in this snapshot.
- Sources: "How to Spot a Crypto Rug Pull" (theblockverse.co, 2026-07-08) —
  "anonymity is a risk multiplier, not a verdict"; Frosties (anonymous NFT
  project, $1.1M raise, creators charged with wire fraud); $14-17B total crypto
  scam losses in 2025.
