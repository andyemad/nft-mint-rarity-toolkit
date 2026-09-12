# Post-entry launch TA: cost basis, executable exits, and claim overhang

Use when the user already bought a newly launched NFT and asks for an updated TA while anxious about a fast retracement.

## Required live comparison

Anchor every statement to the exact entry price. Re-fetch in the same pass:

- marketplace floor and unique-token active asks;
- seller-owner validation for the lower book when launch velocity makes stale orders likely;
- highest credible collection bid;
- 10m, 20m, and 30m sale medians/counts, plus broader windows;
- verified seller fee rate;
- current minted/claimed supply and remaining claim overhang;
- active listed inventory as a percentage of circulating supply.

Do not describe a position as profitable from headline floor alone. Compute three separate outcomes:

1. Gross mark-to-floor.
2. Net proceeds if listed near floor: `floor * (1 - verified seller fee)` minus entry and gas.
3. Net proceeds if immediately accepting the best credible bid.

Fee-adjusted break-even is `entry / (1 - verified seller fee)` before gas. A floor above entry can still be a losing exit.

## Trend interpretation

For opening-session retracements, compare short windows rather than relying on the full launch median:

- falling 30m median + lower floor + increasing listings = distribution/claim pressure;
- 10m median above the 30m median can be a relief bounce, not trend reversal;
- tight bid/ask spread and high sale count establish exit liquidity, not necessarily bullish direction;
- remaining claims must be reported as both percentage of raffle/allocation supply and percentage of final supply.

Set support from current bid stacks and recent lower-percentile sales. Set resistance from cumulative active asks and former high-volume shelves. Define invalidation with observable market conditions, such as both a rolling-median break and bid withdrawal—not a vague price feeling.

## Communication for an anxious holder

Lead with the current economic reality: approximately flat, modestly down, or materially impaired after fees. Then give the directional regime honestly. Avoid empty reassurance and avoid defending the prior call.

If the prior recommended entry was filled but the setup deteriorated, say both:

- whether the entry itself remains within the planned zone; and
- which timing/risk assumption failed, such as entering before claims cleared.

Give a direct action frame:

- do not panic-sell into a weak bid if the position can still exit near fee-adjusted break-even;
- do not average down while supply overhang is expanding;
- name a near-flat listing zone, recovery confirmation, and hard invalidation;
- never list, accept an offer, or broadcast without approval.

## Worked pattern: Original Blokyz launch

A 0.159 ETH entry looked +6% against a 0.16895–0.1699 floor, but the collection charged 6% required seller fees. True break-even was about 0.16915. Selling the 0.166 best bid would net about 0.15604 ETH, roughly -1.86% before gas; a 0.1699 listing would be near flat. Meanwhile the 30m median had fallen to 0.162, the 10m median bounced to 0.167, listings reached about 11.5% of circulating supply, and 1,927 claims remained. Correct verdict: not wrecked, but in a bearish launch retracement; no averaging down, use explicit reclaim and invalidation levels.
