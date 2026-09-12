# ERC-6551 token-bound-account "broker" NFT genre + clone detection

Refined 2026-08-23 on the user's request to deep-dive **InkBrokers** (inkbrokers.com,
Ink chain) and judge whether it's a genuine project or "just a StonkBrokers clone."
This is a reusable recipe for a recurring NFT genre: the **NFT-is-a-wallet**
collection where the token is an ERC-6551 token-bound account that holds its own
assets, earns from a corporate "desk/suite," and where the payout engine may or
may not (yet) exist. Use for any future "NFT that earns / NFT is an account /
NFT-as-position" collection call.

## The genre's shape (recognize it instantly)
- Fixed supply (4444 is the recurring number — StonkBrokers AND InkBrokers both 4444).
- `mint` is FREE or near-free (SeaDrop stage price 0) and sells out fast.
- Each token is an ERC-6551 token-bound account: it holds assets, signs txs, and
  "the drawer goes with it" on sale. Address is what the token *is*, not a pay-sheet keyed separately.
- **Activate-to-earn**: activation burns a token (permanent supply drop) and
  fixes a **tier** (cut by rarity, sum-of-reciprocals rank).
- Payouts are **pull-based distributions** weighted by tier, paying **only what
  the project actually collects that round** — rounds are explicitly allowed to be **zero**.
- Often ships NFTs-per-AMM (`Anvil NFT AMM` on StonkBrokers, a bonding-curve floor
  that quotes floor and nothing above floor) + loans against the token (liquidation if price drops).
- Docs are unusually candid about failure modes (unaudited contracts, empty-drawer,
  ownership cycles, zero rounds) — this honesty is a POSITIVE signal, not a rug tell.

## The linchpin question (always ask this)
**Where is the yield engine, and is it named and dated?** This is what separates a
real position from a momentum flip.
- StonkBrokers: concrete — 70% of Anvil AMM trade fees → real stock-token airdrops to activated wallets. NAMED fee source.
- InkBrokers: vague — "pays what the desk collects" with **no named fee source and no date**. Yield is a promise with no engine attached yet.

## The clone angle (StonkBrokers was first)
StonkBrokers (Clutch Markets, **Robinhood chain**, Bloomberg-profiled Aug 11 2026;
$STONKBROKER CA on RH) did this exact playbook first: 4444, ERC-6551, activate-to-earn,
collection token. InkBrokers = same architecture transplanted onto **Ink** (Kraken's
OP-Stack L2) to ride the $INK TGE wave the way StonkBrokers rode Robinhood.
Structurally a clone; that alone doesn't make it a scam — quality differs (concrete
vs vague yield engine). Evaluate the earning source, not the architecture.

## The "token launch in N hours" trap
Critical framing for this genre: **a chain-level token TGE is not the project's
payout.** When hype says "token launches in ~12/24h," verify WHICH token:
- InkBrokers' own feed said "Reveal in 2 hours / Token in 24 hours" — the token is
  **$INK, the Kraken-issued ecosystem token** (TGE expected Jul→Sep 2026, airdrop via
  Kraken Drops, officially "no precise date"), NOT these brokers' token.
- Implication: the catalyst is a chain-wide **liquidity tailwind**, not a payout
  guarantee from these NFTs. Buying secondary into that is buying the top of the
  mouse-race flip window on a project whose engine is still "behind glass."

## Ink-chain facts (for future Ink or $INK research)
- Ink = Kraken's OP-Stack L2, live mainnet since Dec 2024. `inkonchain.com`.
- OpenSea chain identifier = `ink`. InkBrokers slug = `inkbrokers-nft`; the collection
  page hydration shows the same collection also at slug `ink-brokers` (name collision
  note — verify slug via `contracts[].chain.identifier === "ink"`).
- On-chain state read keylessly: SeaDrop V1 ERC-721, maxSupply 4444 = totalSupply 4444 (sold out),
  floor ~0.00009 ETH (~$0.22), stage price 0 (free mint). Keyless OpenSea hydration parses fine.
- $INK TGE: Kraken blog "integrating-ink-token" (Jul 24 2025) declares intent + airdrop;
  as of Aug 19 2026 still NO precise date from the Ink Foundation. Watch Kraken/Ink blog
  + `airdrops.io/ink-chain` as the date firms.
- X reads: `~/.hermes/the curl-based fallback in your own toolkit` twitter_watch / fxtwitter
  / logged-out x.com relay regex all work here (verified 2026-08-23).

## Verification kit (all keyless, used this session)
- Site/docs: `curl` the landing, strip `script|style`, parse meta + visible text — the
  InkBrokers docs carried the whole mechanism + failure modes in HTML (no SPA shell).
- X feed: x.com logged-out relay `__typename:"TweetResults",rest_id:"..."` + `full_text:`
  regexes recovered the reveal/token-announcement posts; fxtwitter profile gave
  followers/verified/desc.
- OpenSea: `/collection/<slug>` page HTML hydration (collectionBySlug fragments) gives
  floor, stage, supply, chain WITHOUT an API key (the rich fragment has `stats`/`drop`).
- Search fallback when managed web tools are down: Brave HTML curl worked; Mojeek
  returned a ~361-byte stub (blocked-ish) same session — rotate engines.

## Bottom-line verdict template for this genre
Score thesis / evidence / risk-mgmt / positioning AND state the single fact that would
upgrade "momentum flip" → "position" (here: a dated, named, live-on-chain fee source).
Positioning is usually weakest once sold-out-and-pumped into a chain TGE event — name that.
