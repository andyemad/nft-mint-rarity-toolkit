# Jackpot / prize-pool mechanics & marketplace-terms risk

When the user says "add a jackpot" (a prize pool to drive FOMO), the BIG decision
is the PAYOUT SHAPE, not whether to have one. Shape drives BOTH the FOMO
impact AND whether the mechanic gets flagged/banned on OpenSea / RH. Verified
2026-08-19 while sizing a 4444-supply STILL UP launch.

## The one rule that protects you: RANDOM-WINNER = lottery risk, MINT-ORDER = distribution

- **Random single winner** ("pay, random number picks one, everyone else
  loses their stake") is a game of chance → regulators/platforms treat it as
  gambling/raffle → highest OpenSea delisting / wallet-flag risk. Avoid.
- **Mint-order / supply-based deterministic payout** ("holder of token #N
  wins", "last minted wins", "every holder gets a proportional share") is a
  distribution, not a lottery → far lower ban risk. Always prefer this.
- Only the user-facing rule matters here — never advertise in copy a jackpot
  the CONTRACT doesn't actually implement (see `fomo-mint-page.md`'s
  anti-fake-mechanism rule). The safest design is honest copy + real logic.

## Why "every 888 mints split the pool equally" is a trap

the user's instinct (4444 supply → split a pool among each 888-mint cohort) sounds
fair but tests poorly on BOTH axes:

- Split too thin → worthless reward. At a 10% cut, 888-way split paid each
  holder ~$0.04 → $1.09. Nobody FOMOs over four cents.
- Split meaningfully (25% cut) → each holder gets ~$0.10 → $2.73, but the
  creator surrenders ~55% of mint revenue. Worst of both worlds: you lose
  money AND the prize is too small to matter. Don't build the equal-split form.

## The shape that wins: one winner per milestone, weighted, escalating

For a 4444 supply with a 50%-of-mint-fees pool (~1.94 ETH on full sellout at
3.88 ETH total), ONE winner per milestone (e.g. every 888th token), with pots
weighted by revenue accumulated at that milestone so later pots are bigger:

| milestone # | pot        | that token cost | winner multiple |
|-------------|-----------|-----------------|-----------------|
| 888         | $82        | $0.85           | ~97x            |
| 1776        | $346       | $1.74           | ~199x           |
| 2664        | $789       | $2.62           | ~301x           |
| 3552        | $1414      | $3.51           | ~403x           |
| 4440        | $2219      | $4.40           | ~504x           |

The 500x "your token could be worth 500x with zero effort" is the screenshot /
FOMO missile that drives buys. It stays a deterministic distribution (winner =
the holder of a specific token id, chosen by mint order / a fixed reveal rule —
NOT a random draw) → low ban risk. Creator still banks ~half the revenue.

## Sizing the pool cut

Pool = a fixed % of every paid mint, split to winners; creator keeps the rest.
Rough reference on 4444 / ~3.88 ETH full revenue:
- 10% pool ~ 0.85 ETH (~$2.1K) to winners — gentle, creator keeps ~78%.
- 25% pool ~ 2.1 ETH — creator keeps ~45%.
- 50% pool ~ 1.94 ETH — 5 milestone winners ~$82 → $2219, creator keeps ~50%.
Recommend a 50/50 split as the strongest FOMO-to-cost ratio, OR drop the
jackpot entirely and keep just the curve + free wave (cleanest, creator keeps
~all revenue, zero terms risk). Equal-split-across-cohort is never the pick.

## Confirmed numbers for the STILL UP ladder (4444 supply)

- 4444 supply, 44 free (small starter wave, not 444), then paid ladder.
- START = 0.000002 ETH (~$0.005, half a penny), STEP = 0.0000004 ETH/mint,
  top ≈ 0.00176 ETH (~$4.40), full-revenue ≈ 3.88 ETH (~$9.7K), avg ≈ $2.20.
- Weighted per-milestone one-winner pool at 50% is the recommended jackpot shape.

## Pitfall: don't lecture, offer the safe/bold fork

Present the risk + the numbers once, then hand the user the choice between the
safe shape and dropping it. Don't re-argue distribution; he wants a working
FOMO design. (See `nft-collection-production` honest-gate: state race/cost
once, then build.)
