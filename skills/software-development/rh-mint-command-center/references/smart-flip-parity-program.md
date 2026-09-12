# Smart Flip Tools parity program (2026-08-26 →)

Emad: "incorporate this into mint room" (smart-flip-tools.com). Source recon:
paid hosted bidding engine for flippers — Collection/Trait/Token bidders with
floor-relative rules + auto counter-bids, Auto Lister after fills, flip PnL
tracker, seven alert types, Vault key storage. OpenSea + Blur, all EVM chains
incl. Robinhood (advertised). Founder Hret / dev Compich, ~3 yrs running.
Tiers Ξ0.04–0.09/mo; their setup = Windows/VPS + ~20 ISP proxies + own RPC.

Consolidated plan (plan-first workflow lesson applied — plan written BEFORE
any code, per the Quasarr parity precedent):
`docs/plans/2026-08-26_smart-flip-parity-consolidation.md`.

## Waves
- **A recon** (no money, no writes): offer wire shapes on RH — WETH contract +
  bot-wallet balance/allowance on chain 4663, wrap path; offer POST
  `/api/v2/orders/{chain}/seaport/offers` envelope (mirror of the listings
  envelope already validated in nft-listing.ts); cancel path = Seaport
  `cancel(OrderComponents[])` signed+broadcast vs OS API cancel; best-bid /
  collection-offer / fulfillment-for-offers endpoints. Deliverable:
  `references/smart-flip-offer-wire-shapes.md` in-repo + decision memo.
- **B bid engine core** (rehearse-only): `lib/server/nft-offer.ts` (build/sign/
  post/cancel offers, same zone V2/conduit/fee-bake discipline as
  nft-listing.ts) + `lib/server/bid-policy.ts` PURE: `topPlus(step)` /
  `floorTimes(bips)`, clamp to [floorMin, floorMax], min-profit vs floor,
  counter-or-give-up at max, 1d/7d floor-change stops. Exact-BigInt tests.
- **C Collection Bidder**: bid-store + `/api/bids` loopback route + daemon
  (10 s tick: floor + best bids → policy → diff vs standing offers → post/
  cancel via signer gate) + `/bids` sidebar page with winning/outbid pills;
  caps cards reuse the sniper two-tier pattern.
- **D Token + Trait bidders**: per-tokenId default/max/counter rows; trait
  mode = trait-floor price (cheapest listed token carrying the trait, from
  rarity gallery data), bid targets = listings at/below trait price. Same
  daemon, task kinds.
- **E Auto Lister**: on bid-fill detection (nft-scan wallet diff) auto-list at
  max(floor × factor, cost × (1 + minProfit)) via existing nft-listing.ts;
  never-below-cost guard; optional AutoSell = accept offers ≥ min profit.
- **F Flip PnL**: flip ledger buy ↔ sell (fees + gas included), realised PnL
  per flip and per collection; REALISED PNL panel on /bids.

## Scope cuts (deliberate)
OpenSea only — Blur has no RH presence and no keyless API. No SaaS/hosting,
no proxies/rate-evasion, no 100-bids/sec arms race (our edge: zero
subscription, RH-native, trait-aware, keys never leave the box; ~1 repricing
pass/collection/5–15 s tick is ample on RH).

## Key mapping + safety
A bid is the Seaport-offer MIRROR of `lib/server/nft-listing.ts` (offerer
offers WETH; consideration = NFT). All live post/cancel flow through
`signer.ts` (kill switch → auth → protected signer → simulate → cap →
rehearse-before-live). Two-tier caps global + per-collection. Alerts chime +
IRC on fill / stop-trip / cap hit. Clean-room rule as Quasarr: public
landing/docs behavior only.

## Status at plan write (8/26)
DRAFT — awaiting Emad's go for wave A. Open questions: (1) wrap ~0.1 RH ETH
from bot wallet for WETH or separate funding; (2) first live test collection
(Clay StonKz / CACHE FLOW / his pick); (3) trait bidder first target = Clay
traits post-reveal.
