# Competitor Launch Forensics + Verified Launch Playbook (Cyclops Eyrix case, 2026-08-15)

Use when the user drops an X handle or collection and says "devise a plan like
this". The workflow: forensics first, honest math, then the playbook.

## Step 1 — Profile timeline via logged-out X scrape

`curl -sL -A "<browser UA>" https://x.com/<handle>` then relay regexes
(from terminal-web-research): tweet IDs
`re.findall(r'__typename:"TweetResults",rest_id:"(\d+)"', html)`, texts
`full_text:"..."`. Reconstruct the launch ladder from the texts — the
pre-mint hype sequence is almost always legible there.

## Step 2 — Resolve the mint link + venue

t.co links in the tweets: `curl -sIL -A "Mozilla/5.0" <t.co>` and grep
location. Mint links usually land on an OpenSea collection overview URL —
that's the venue.

## Step 3 — OpenSea collection page = full stats, no API key

The collection overview page (`opensea.io/collection/<slug>`) embeds the
complete GraphQL state server-side. Key fields (verified on
cyclopseyrixnft):

- `"totalSupply":8558` and `"uniqueItemCount"` — minted/supply
- `"ownerCount":1560`
- `stats.volume.usd` — ALL-TIME volume in USD (1-day/1-hour/7-day windows
  also present; on a brand-new collection they're all ~equal, that's normal)
- `activeDropStage.price.usd` — current mint price in USD, plus
  `token.unit` in the chain's native unit. On Robinhood Chain the unit is
  ETH-denominated micro-amounts: 0.0001 ETH = $0.19 USD. NEVER read the
  raw unit as "0.0001 ETH is basically free so mint is free" — take the
  USD field.
- `"floorPrice":{"pricePerItem":{...,"usd":0.16}}` inside `BestOrder` —
  live floor. Compare floor vs mint price: floor < mint = minters already
  underwater, tells you the launch's real health.
- `"chain":{"identifier":"robinhood"}` — venue chain
- `"createdAt":"2026-08-14T..."` — how fresh
- `isVerified`, `discordUrl` (often empty = no community infra)

Gross mint revenue = mint_price_usd × totalSupply (or supply cap). For
Cyclops: $0.19 × 8,558 ≈ $1.6K gross in 24h — that's the honest ceiling
of a no-distribution RH-chain launch, not "easy money".

## Step 4 — Verdict framing

Report: gross revenue, net after ~10% royalty + fees, floor vs mint,
volume (all-time = 1-day on fresh collections), and the ONE real lever:
distribution. Better art raises the ceiling; it doesn't fill the room.
Give realistic bands: 300-1K engaged followers = $2-5K gross; 5-10K =
$10-20K gross. Cyclops numbers are the floor, not the target.

## Verified launch playbook (the D-count ladder)

The pattern that actually ran, with the user's tightening:

- **D-21..D-8 SETUP**: anonymous X account + matching name on OpenSea/Discord,
  daily art WIP posts (no links), follow+engage 50-100 mint accounts via
  replies/likes (not DMs), Discord skeleton. **KILL GATE: 300+ engaged
  followers by D-8 or cancel** — the user's distribution-first gate.
- **D-7**: full art drop teasers, 3-4 hero images + rarity table preview.
- **D-5**: WL giveaway — like + repost + tag 1 friend + drop ETH wallet.
  20-50 spots, 24h only, scarcity in the post.
- **D-3**: "early access" X group chat, 100 spots, guaranteed WL + airdrop
  (builds the DM/email list — the real asset).
- **D-1**: "difficult decision" post (supply cut / price change / window) —
  manufactured drama, keep it believable.
- **D-day**: PUBLIC MINT LIVE, countdown, "no whitelist, no waiting", pinned.
- **D+1**: floor support (buy back cheap if floor dips below mint, small wallet).
- **D+2**: trait reveal + rarity leaderboard (drives secondary volume).
- **D+3**: roadmap tease. **DELIVER promised airdrops** — wallet harvest
  without delivery = rug = legal exposure + dead brand for drop 2.

Mechanics: RH chain, SeaDrop ERC-721, $0.19-0.50 mint, 10K supply, 5-10%
royalty, mint page 30-60s to feel hot. Never list below break-even
(mint / 0.89).

## Parody/likeness boundary (the user's idea-space)

- Real extremist/hate-figure likeness (e.g. Nick Fuentes): hard no — OpenSea
  prohibited-content policy delists mid-mint, zero audience overlap, right-of-
  publicity exposure, poisons anonymity for future drops.
- Fictional archetype (invented cult-leader persona): fine, ownable.
- Parody of public-figure TYPES (pundit-class archetypes: red ties, flag
  pins, podiums, toupees, no real names in metadata, cartoonized not
  photoreal): legally satire-protected territory (Hustler v. Falwell
  standard) and delisting risk is low but nonzero. Saved plan:
  "podium" keyword → ~/Projects/podium-nft/PLAN.md.
- Precedent: Capitol Punks got pulled; official TrumpCards printed money.
  The line: cartoonized parody of types vs real-person glorification.
