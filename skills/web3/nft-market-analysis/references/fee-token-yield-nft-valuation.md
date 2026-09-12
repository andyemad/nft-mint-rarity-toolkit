# Fee-token + yield-NFT valuation

Use when one project has a fungible fee/burn token and a scarce NFT that receives fees, yield, or redemption assets. The Reserve on Robinhood Chain (September 2026) is the worked case; the method generalizes.

## Core valuation mistake

Do not compare `$0.002/token` with `$400/NFT`. Compute:

- token total valuation = price × `totalSupply()`;
- burn-adjusted valuation = price × (supply − dead-address balance);
- economic-float valuation = price × (supply − dead − provably permanent locks);
- NFT floor value = validated floor × surviving supply;
- NFT bid value = executable collection bid × surviving supply.

In the worked case, 1B tokens, 254.5M dead, and 81.63M in a no-withdraw launch locker produced a ~$1.48M economic-float valuation at ~$0.00223. About 1,885 NFTs at a validated $389 floor implied only ~$733K. The “cheap coin versus expensive NFT” intuition reversed once supplies were normalized.

## Reproduce the displayed market cap

Different dashboards may use:

- full `totalSupply()`;
- supply excluding the dead address;
- supply excluding dead + lockers;
- an undocumented circulating-supply feed.

Calculate each. If one matches the displayed number, explain the convention rather than claiming a data error.

## Determine who owns value

Build a two-column economic map:

- **fee/burn token:** holder revenue, governance, redemption, transfer tax, activation/climb sinks, mint authority;
- **NFT:** fee share, coupon, vault claim, cage/backing, activation state, transfer reset, upgrade weight.

A burn token may be structurally subordinated: traders fund the fee stream while NFTs own the claim. Deflation alone does not make those rights equivalent.

## Vault truth versus marketing totals

Read live:

- backing-token balance;
- accounted assets;
- coupon/cage liabilities;
- surplus-skimming rule;
- current active weight/count;
- per-item pending coupon and cage for the cheapest valid listings.

Keep three numbers separate: current vault assets, cumulative deposits, cumulative payouts. A “$100K distributed” claim does not mean $100K remains as floor backing.

Read the redemption function’s actual transfer token. In the worked case, burning a Note transferred Robinhood-chain GLD, a third-party tokenized instrument—not physical bars supplied by the project. State instrument/custody/legal risk separately.

## Trace upstream fee routing

Inspect marketplace order consideration recipients and protocol fee contracts. Ask:

1. Is the fee sent directly to the vault?
2. Does an escrow make it claimable by an EOA?
3. Is the advertised split enforced on-chain or performed by a crank/operator?
4. Can the recipient be rotated?
5. Does the vault protect only funds already deposited?

A secure redemption vault does not prove future revenue will be deposited. In the worked case, marketplace royalties went to a treasury EOA, while the vault safely protected GLD after deposit.

## Contract-claim conflict scan

Search the complete inheritance tree, not only the custom contract body:

- `setMaxSupply` and mint-stage controls;
- mutable base/contract URI;
- royalty recipient changes;
- ownership transfer/renunciation;
- pause/blacklist/transfer controls;
- reissue behavior after burns.

The worked contract claimed supply only falls, yet inherited owner-callable max-supply and stage controls remained. Current max supply staying unchanged is not the same as an enforced hard cap.

Also compare live website copy with deployed constants. Flag stale launch terms when activation cost, transfer behavior, backing source, or mint price changed before deployment.

## Reflexive sustainability test

Launch volume can produce simultaneously:

- large tax-funded NFT payouts;
- rapid token burns from activation/upgrades;
- rising NFT floors;
- rising token price.

Do not annualize it. Measure whether the strongest sinks are finite:

- number sealed/dark/live;
- remaining capped upgrade seats;
- activation cost in fiat at the current token price;
- recurring reactivation demand per genuine secondary transfer;
- payout sensitivity to 90% and 99% volume contraction.

A higher token price raises the cost of using the NFT and can suppress the burn demand that created the rise.

## Marketplace validation

An API `ACTIVE` floor can be stale. Compare each lower-book listing maker with the current token owner through `ownerOf` or an explorer instance endpoint. Hydrate traits/state for at least the cheapest 20–50 items. A sealed zero-backing floor asset and an activated higher-weight asset are economically different.

Include activation expense in all-in entry and seller fees in break-even:

`break_even = (NFT price + required activation + acquisition gas) / (1 - seller fee rate)`

## Decision rule

Do not call the fungible token undervalued merely because individual NFTs are expensive. Require:

- normalized token versus NFT valuations;
- durable, enforceable token-holder value capture—or explicitly price the token as consumable fuel;
- sustainable post-launch volume;
- continuing organic burns after one-time upgrade races;
- proportional vault growth;
- sufficient liquidity after transfer tax and slippage;
- public claims consistent with callable contract controls.

A token can be real, fixed-supply, and mechanically useful while still not be fundamentally cheap.