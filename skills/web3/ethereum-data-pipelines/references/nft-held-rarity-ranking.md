# Ranking a wallet's held NFTs by rarity (revealed collection)

CLASS: given an already-revealed collection and a wallet, rank the wallet's held
tokens by statistical trait-frequency rarity. The rarity rank determines which
pieces carry the only plausible exit value.

Validated on TWO collections back-to-back (ComboX, 5000 supply; Bakemono
Crayons, 2026-08-19) — the pattern is reusable, not one-off.

## Re-usable engines (source of truth)
- `~/Projects/rarity-engine/combox_rarity.py` — single-collection rarity.
- `~/Projects/rarity-engine/bakemono_rarity.py` — GENERALIZED: adds a `held`
  fetch (wallet's tokens in the collection) and a `mine` command that prints the
  user's holdings rarest-first with rank/pct/score/contributing traits.
Commands: `python3 bakemono_rarity.py both` (fetch traits + held + rank + mine).
Data parked under `~/.hermes/rarity/<collection>/` (`traits.json`, `scores.json`,
`held.json`).

## Rarity model (statistical trait-frequency)
Per-token score = Σ over that token's traits of (collection_size / trait_count)
for the trait value. Rarer trait value → larger contrib → higher score. Rank =
descending score; pct = rank/size*100. This beats OpenSea's lagging rarity tab
by ranking the same raw metadata the instant it's indexed.

## Fetching the source data
- Traits: OpenSea V2 `GET /api/v2/chain/{chain}/contract/{addr}/nfts?limit=50`
  cursor-paginated with `X-API-KEY` (RH chain worked keyless before, keyed is
  safe). IPFS gateways stay blocked for fresh reveals — use the OpenSea list-NFTs
  endpoint, not tokenURI.
- Wallet holdings in the collection: `GET /api/v2/chain/{chain}/account/{wallet}/nfts?collection={slug}`
  (paginate `next`), filter by collection slug.
- Pace ~0.25s between calls, retry with backoff on rate limits (OpenSea replies
  `"errors": ["rate limit"]`).

## Pitfalls / honest caveats
- **Supply mismatch:** a collection's `total_supply` on OpenSea stats can differ
  from what list-NFTs returns (Bakemono: stats page said 3,962 / unique_item_count
  3,962, but list-NFTs returned 5,000 tokens). Use the list-NFTs total as the
  rarity denominator; the stats `total_supply` is unreliable as a rarity base.
- **The "Rarity: 1/1 / Rare / Uncommon / Common" level trait AND dedicated
  "1/1 Scene" + "1/1 Title" traits dominate the top of the range.** Tokens carrying
  a 1/1 Scene+Title cluster to the very top (scores ~1415-1418) versus ~120 for
  mid-tier — a ~10x score gap. Treat raw score as ordinal ranking, never as EV.
- **Rarity ≠ liquidity.** On an illiquid / rug-dumping thin book, a high rarity
  rank does NOT guarantee an exit. The rare 1/1-titled pieces are the ones a
  collector actually wants (i.e. the only plausible exit value); mid/floor-ranked
  pieces are bulk and effectively unsellable at a premium. Report this plainly —
  do NOT let a "you own top-0.3% rares" message oversell a dead collection.
- For the cost side of the same bag, `scripts/wallet_recon.py` reconstructs
  holdings at cost basis (FIFO) independently of rarity.
