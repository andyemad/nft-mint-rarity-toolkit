# MintGo reverse-engineering notes (2026-08-10/11, updated 2026-08-13)

Reference clone target: mintgo.fun. Findings below were verified by probing the
shipped frontend bundle and public API endpoints.

## LIVE API ACCESS — same-origin session gate (verified 2026-08-13)

MintGo’s browser endpoints can be queried for audit purposes when the request
matches the same-origin browser contract. Treat them as private implementation
details, not a stable public API.

1. `POST https://mintgo.fun/api/session` with `content-type: application/json`,
   `origin: https://mintgo.fun`, `referer: https://mintgo.fun/`, browser UA, and
   browser-like `Sec-Fetch-Site: same-origin`, `Sec-Fetch-Mode: cors`, and
   `Sec-Fetch-Dest: empty`; body `{}`.
2. Use a cookie jar for **both** reading and writing on the session POST and all
   later requests: `curl -b jar -c jar ...`. Protected responses may rotate
   `mg_access`; reading from a jar without updating it can work once and then
   unexpectedly return `BROWSER_SESSION_REQUIRED`.
3. Send the same origin/referer/fetch-metadata headers on subsequent requests.
   The session observed in this audit used HttpOnly `mg_access` (~30 minutes)
   and `mg_vid` (~1 year).

A representative live `/api/status?chain=ethereum` response disclosed HTTP RPC
failover across MEV Blocker, Blast, and PublicNode; WSS candidates including
PublicNode, 0xRPC, and Tenderly; `marketData: opensea`; and a connected OpenSea
stream. This is useful provenance evidence, but server status fields are
operational and must not be treated as permanent product guarantees.

Verified/identified endpoint families include:

- `/api/status`, `/api/eth-price`, `/api/eth-gas`
- `/api/events`, `/api/all/stream`
- `/api/trending`, `/api/trending-snapshot`
- `/api/runners`, `/api/runners-ranked`, `/api/market-snapshot`
- `/api/search`, `/api/collection/:address`, `/api/mint-analysis/:address`,
  `/api/mint-tx/:address`
- `/api/seadrop-radar`
- `/api/monitor/*`, `/api/tx-gas/:tx`
- `/api/opensea-eligibility/*`

Response shapes: `market-snapshot` returns rolling runner windows; rows include
contract identity, window mint/sales/volume fields, OpenSea identity, and a
preformatted `display` object. `trending-snapshot` has a similar nested window
map. The exact schema is versioned by the deployed bundle and should be sampled
again before implementation.

FREE-MINT SIGNAL: a zero-volume runner (`windowVolumeEth === 0` while
`windowMintCount > 0`) can indicate a free mint, but verify the payment token
and route before labeling it—zero reported market volume is not sufficient by
itself.

A practical audit/proxy pattern is: establish the same-origin session, sample
bounded JSON endpoints in parallel, and avoid consuming an unbounded SSE stream
unless realtime behavior itself is under test. Keep request volume low and do
not present these private endpoints as a supported integration contract.

## Bundle-derived parity inventory (verified 2026-08-13)

Do not stop at endpoint discovery. MintGo's current landing HTML and shipped
bundle exposed product behavior that is easy to miss in a data-only audit:

- Primary surfaces: New Mints, Trending, Runners/Sales, Upcoming Mints, indexed
  project search, collection detail, wallet tracker, OpenSea eligibility, and
  wallet-mediated mint execution.
- Current visible chain selector: ALL, ETH, RH, and ARC marked coming soon. The
  bundle also contains Stable Mainnet configuration, but Stable is excluded
  from the active `DATA_CHAINS` list and is not currently user-selectable; treat
  it as dormant/experimental rather than parity scope.
- Trending windows currently rendered: 1m, 5m, 10m, 30m, 1h, 6h, 12h, 24h.
  Runner windows: 1m, 5m, 15m, 1h, 1d.
- Filters/settings: chain, free/paid, runner sort, native-vs-USDT volume,
  project block/unblock, language, and local persisted preferences.
- Alerts: new upcoming mint, ten minutes before start, mint live, trending
  threshold, runner sales threshold, and tracked-wallet activity. The bundle
  includes per-category sound presets, volume, preview, Telegram configuration,
  and language indicating true background tracking after signed authentication.
- Wallet tracking: add/edit addresses by chain, alert history, signature-based
  authentication, and a current UI limit of 100 monitored wallets per connected
  wallet.
- Mint flow: browser wallets and WalletConnect, chain switching, balance,
  quantity/batch mint, eligibility, gas/price/total, paid-price-change handling,
  unsupported/restricted contracts, and failure/success states.
- Detail/risk fields: holders, supply, floor, volume/sales, deployer age and NFT
  project count, source-code verification, community reports, listing-honeypot
  warning, social/market/explorer links, and stage/supply progress.

General audit recipe: save HTML + CSS + JS; inspect DOM controls and labels;
grep the bundle for `/api/`, `data-*`, `localStorage`, `wallet_*`, alert/sound
keys, time-window arrays, translations, render functions, and empty/error copy;
then exercise representative live endpoints. Maintain a parity matrix separating
**observed UI**, **bundle-confirmed behavior**, **live-API-confirmed data**, and
**inference**. Never claim complete parity from API fields alone.

## Architecture

MintGo is NOT reading one public calendar API. It runs a continuously connected
backend that:
1. Connects to public Ethereum HTTP/WSS RPCs (its `/api/status` listed
   `rpc.mevblocker.io`, `eth-mainnet.public.blastapi.io`,
   `ethereum-rpc.publicnode.com`, Tenderly public gateway).
2. Watches on-chain mint events in real time, enriches server-side, keeps
   rolling snapshots, pushes updates to browsers over SSE (`/api/events`,
   `/api/all/stream`).
3. Maintains trending windows and market snapshots (market source = OpenSea,
   active OpenSea stream connection).
4. Watches SeaDrop configuration events for upcoming mint schedules, then
   enriches each contract with OpenSea metadata and all signed/public stages.

Implication: a static clone cannot replicate this without a long-lived backend.
A Vercel serverless version must use bounded lookbacks + caching instead.

## First-party frontend endpoints (private, not a stable API)

`/api/session`, `/api/bootstrap`, `/api/all/bootstrap`, `/api/events`,
`/api/all/stream`, `/api/trending`, `/api/trending-snapshot`, `/api/runners`,
`/api/runners-ranked`, `/api/market-snapshot`, `/api/seadrop-radar`,
`/api/collection/:address`, `/api/mint-analysis/:address`, `/api/search`,
`/api/status`.

Sample `/api/seadrop-radar?chain=ethereum` response: 24 projects, 71 stages,
all `stageSource: opensea`. The Galleria (0x0964fe43b3be705219a1513b3f0450ad65692ebc)
had 5 stages (signed presales + public), prices 0.00125–0.0025 ETH.

## SeaDrop discovery (verified)

- Canonical SeaDrop contract: `0x00005ea00ac477b1030ce78506496e8c2de24bf5`
- Event: `PublicDropUpdated(address,(uint80,uint48,uint48,uint16,uint16,bool))`
- Topic: `0x3e30d8e1f739ea4795c481b21c23f905e938b80339305f3508e43c558e5dead3`
- NFT contract = topic[1]; data = 6 words: mintPrice, startTime, endTime,
  maxPerWallet, feeBps, restrictFeeRecipients.
- A 5,000-block sample via `rpc.mevblocker.io` returned 21 updates (mevblocker
  accepts ranges up to 10,000 blocks).
- MintGo enriches every address with OpenSea collection identity + full stage
  schedule → our no-key pipeline derives public stages on-chain and labels
  provenance instead of claiming OpenSea as the source.

## OpenSea no-key enrichment (verified data exists in page)

Official REST API (`api.opensea.io/api/v2/...`) returns 401 without a key, but
public pages are server-rendered with GraphQL hydration:
`https://opensea.io/contract/ethereum/<address>` 308-redirects to
`https://opensea.io/collection/<slug>`.

The HTML contains multiple
`(window[Symbol.for("urql_transport")] ??= []).push({"rehydrate":{...}})` script
fragments. One fragment holds `data.collectionBySlug` with the FULL record:
name, slug, imageUrl, externalUrl, twitterUsername, isVerified, isApproved,
drop (type SEADROP_V1_ERC721, maxSupply, stages[] with startTime/endTime/
stageIndex/price.token.unit+symbol), stats (totalSupply, floorPrice.usd).

PITFALL: 4 `collectionBySlug` occurrences exist; some are partial fragments.
First occurrence may lack `name`/`drop`. Select the occurrence containing the
rich fields (name + drop), or merge by id. Live JS parser returned null on the
real page when it only read the first (partial) fragment — the Python probe
found the full record by scanning all fragments.

Sample decoded: Cowz (0x17573ad7d3c4194e856d6976d8667eb377b2c3c4) — 4 stages,
free → 0.001 ETH, supply 10000, verified, twitter EthCowz.

## Live mint detection (verified)

Standard Transfer topic `0xddf252ad...` with indexed `from = 0x0` over 120
blocks returned 1,604 logs / 196 contracts. Filter to EXACTLY 4 topics
(3-topic logs are ERC-20 transfers). Group by contract + transaction; enrich
only the most active candidates to bound RPC load.

## Product deltas vs MintGo (what NIGHTMINT added)

- transparent quality scoring with visible reasons (not raw activity)
- desktop/browser notifications (not sound-only alerts)
- saved per-project watches + alert thresholds
- explicit provenance + degraded-state indicators
- original dark-editorial UI (not MintGo's copied green three-column terminal)
- honest separation of on-chain facts vs OpenSea enrichment vs heuristics

Browser notifications work while the PWA is open/polling. Closed-browser web
push requires persisted subscriptions + VAPID + scheduled backend — out of
scope for the no-key serverless build, stated honestly in UI.
