# NFT FUD / "same dev did X" scam-claim verification (cross-chain deployer tracing)

Verified 2026-08-23 on the InkBrokers vs "CornHood" accusation. Use when a
tweet or post claims some NFT collection is a "scam" by "the same person/dev"
who ran another (often dead) collection, and you must adjudicate it with
evidence instead of vibes. Complements `nft-collection-call-due-diligence.md`
(command/call sizing) — this one is the *claim-verification* / FUD loop.

## The claim shape to defuse
"@X @Y this is a scam, the same guy did <other collection>." Typical author:
unverified account, small follower count, **zero evidence attached** (no tx
hash, no wallet, no contract, no screenshot). That lack of receipts is itself
findable and reportable.

## Verification loop (run until it resolves, then stop)
1. **Read the tweet keylessly** (fxtwitter `api.fxtwitter.com/<u>/status/<id>`),
   and record author verification + follower count + bio. Unverified + no
   evidence = FUD-shaped from the start, but keep testing the falsifiable bit.
2. **Identify both collections' contracts.** Keyed OpenSea v2:
   `GET /collections/{slug}` → `contracts[]` `{address, chain}`; also
   `owner` (the collection editor), `twitter_username`, `description`.
   Note: a cross-chain pair heads to **different explorers.**
3. **Trace each contract's deployer/creator via its own chain's Blockcout v2:**
   `GET {explorer}/api/v2/addresses/{0x...}` and read:
   - `creator_address_hash` / `creation_transaction_hash` (the deployer)
   - `creation_status`, `is_verified`, `reputation` ("ok"/"bad"), `is_scam`
   - `implementations[].name` + `proxy_type` (e.g. `eip1167` = cloneable proxy;
     `ERC721SeaDropCloneable` = OpenSea SeaDrop, no admin rug lever)
   - `is_contract` on creator ⇒ deployer was a **factory/launchpad**, so the
     "dev EOA" is one hop removed — say so rather than over-claiming linkage.
   Known host maps (verified 2026-08):
   - Ink (Kraken L2): `https://explorer.inkonchain.com/api/v2/...`
   - Robinhood Chain: `https://robinhoodchain.blockscout.com/api/v2/...`
   - Ethereum: prefer RouteScan `api.routescan.io/.../etherscan/api` for
     history; for creator use etherscan/blockscout per availability.
4. **Compare deployers.** Different wallets, different chains, different
   factories ⇒ the "same dev did both" claim **fails on-chain**. Same wallet
   finding doesn't itself prove scam — only that the operator is shared; keep
   going to screen the contract for rug mechanics.
5. **Screen the target contract's health** (independent of the accusation):
   verified + `reputation: ok` + `is_scam: false` on explorer, SeaDrop
   cloneable standard, honest docs that name their own failure modes = healthy
   picture. A "dead" other collection (0 volume / 0 sales / 0 owners all-time
   per `GET /collections/{slug}/stats`) is a *cautionary datapoint about its
   own operator*, **not** proof about a different operator.

## Market-pattern lesson which colored the verdict (TGE coattail pump)
A chain-native token launch (e.g. $INK on Ink, Kraken L2 TGE) sends *every*
native-NFT floor into a hype rip in hours — observed floor going
`<0.0001 ETH → 0.033 ETH` (~360x) on the day of the TGE, with 1-day volume
~55.8 ETH / $136K and bipolar listings (common Tier 0.03–0.04 ETH next to
2–3 ETH and even a 320 ETH long-shot listing). That is an **exit-liquidity
window for holders, not an entry signal for buyers** — especially when the
collection's own yield engine is still unshipped ("behind glass", no dated fee
source) and contracts are unaudited on their own admission. For a rare tier
(T4/Partner = top-2% seats, 60× share), **floor is the wrong reference** — it
trades at a tier premium; "sell into the exit wave" still applies.

## ERC-6551 token-bound-account primitive (recognize the "broker/desk" genre)
"An NFT that holds its own assets / signs its own txs / 'earns' as an account"
= ERC-6551 token-bound accounts. Recognizable tells: CRISP2/6551 registry
`0x0000...6551...5758`, ERC-1167 minimal proxies derived via CREATE2,
activation that BURNS tokens to fix a tier, pull-based (accounted) distribution
that can legally pay zero. The "StonkBrokers/InkBrokers" broker-desks are the
same archetype transplanted chain-to-chain — origin (RH, StonkBrokers) vs newer
(Ink) differs mainly in whether a *concrete dated fee source* exists yet.

## Quick reusable reads
- `GET /collections/{slug}/stats` (keyed) → total volume/sales/owners all-time
  + 1d/7d/30d intervals. Zero across the board = never-traced collection.
- OpenSea page `<title>` is a no-key floor probe: `"Floor < 0.0001 ETH"` vs
  `"Floor 0.033 ETH"` — cheap before/after TGE floor check.
- Listing feed (keyed, when orders endpoint 405s): `GET /api/v2/events/collection/{slug}?event_type=listing&chain={chain}&limit={n}` → `asset_events[]` with per-item `payment.quantity` (wei→ETH ÷1e18) and `asset.identifier`.
