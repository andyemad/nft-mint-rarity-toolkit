# the control room rarity implementation map (as of 2026-08-22, post speed-fix)

Project: `~/Projects/mint-control-room` (Next.js, loopback-only at http://127.0.0.1:3000, launchd service `com.the agent.rh-mint-room`).

## Endpoints

- `GET /api/rarity-gallery?page=N&maxRank=M` — paginated gallery data.
  - No `collection` param: legacy the rarity-test collection mode, reads `.runtime/raritytest_{scores,images}.json`.
  - With `collection=<CA | OpenSea URL | slug>`: generic scanner. Flow = resolve via `parseCollectionInput`/`resolveOpenSeaSlug` → `totalSupply()` + 8-sample tokenURI reveal probe → pre-reveal short-circuit → sweep → info-content rank → persist to `.runtime/rarity/<lowercase-CA>/ranked.json`. Serves memory→disk cache before re-sweeping; `refresh=1` forces a fresh scan. Background image backfill (`backfillImages`) writes `images.json`; next page load merges it.
  - Returns `{total, page, pageSize:60, hasMore, tokens:[{tokenId,rank,pct,score,image,traits:[{type,value,count}]}], status, note, collection:{address,name}}`. `status`: `"pre-reveal"` or `"ranked"`.
- `GET /api/rarity-gallery/saved` (`app/api/rarity-gallery/saved/route.ts`) — lists every persisted scan: `{collections:[{address,name,revealed}]}`. Reads directory names under `.runtime/rarity/`, checks `ranked.json` for non-empty tokens = revealed, resolves display names via OpenSea v2 `/chain/robinhood/contract/<ca>` (needs key; returns null name → UI falls back to short address). Added 2026-08-22 after the user complained earlier scans (THE POOL) were invisible after service restarts.
- Loopback guard via `assertLoopback(request)` from `lib/server/loopback.ts`.
- Raw RPC helper: `rawRpcCall(method, params)` in `lib/server/rpc.ts`.

## Sweep source order (the speed fix)

1. Primary: OpenSea paged list endpoint `/api/v2/chain/robinhood/contract/<ca>/nfts?limit=50&next=...` — includes traits AND image_url. Measured: full 5000-token the rarity-test collection scan in **10.5s** end-to-end.
2. Fallback (API unindexed post-reveal): on-chain tokenURI at 96-way RPC windows + `ipfsJson` per distinct URI (capped).
3. Never use the per-token single-NFT endpoint as a bulk primary — sustained-burst 429s made it take **43 minutes** for 5000 tokens.

Cache reload measured at 45ms.

## Pages

- `/rarity` — gallery (`app/rarity/page.tsx` + `RarityGallery.module.css`). Scan box ("Scan any collection": CA or OpenSea link), **"Saved scans" dropdown** (added 2026-08-22, populated from `/api/rarity-gallery/saved`, lets the user jump between previously scanned collections — the page itself always opens on legacy the rarity-test collection and has no memory of past scans without it), image grid, rank-band badges (legendary ≤0.5%, epic ≤2%, rare ≤10%), top-N filter, pagination, click detail sheet with trait counts + OpenSea link, "Re-check reveal" button when status is pre-reveal. Uses `playwright-core` with Brave executablePath for screenshots (channel:"brave" fails).
- Dashboard panel 03 links to the gallery.

## Data files

- `.runtime/raritytest_scores.json` / `.runtime/raritytest_images.json` — legacy the rarity-test collection default gallery data.
- `.runtime/rarity/<lowercase-CA>/ranked.json` — persisted scan `{at,status,note,tokens}` per collection.
- `.runtime/rarity/<lowercase-CA>/images.json` — tokenId→image URL backfill target.

## Service environment

- `OPENSEA_API_KEY` must be present in the launchd plist `EnvironmentVariables` (added via plistlib; key value from `~/.hermes/secrets/opensea_key`). After editing the plist, a plain kill+respawn does NOT reliably pick up env changes — do full `launchctl bootout gui/501/com.the agent.rh-mint-room` then `launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.the agent.rh-mint-room.plist`, wait for `/api/status` 200.

## Verification workflow

1. `npm run check` (vitest + eslint + next build + e2e) must exit 0. The wallets-page lint error (react-hooks/set-state-in-effect) that previously forced a partial gate was FIXED 2026-08-22 (initial refresh deferred via setTimeout); full `npm run check` is clean again — keep it that way rather than falling back to `npm test` alone.
2. Restart service with bootout/bootstrap cycle above, then curl the changed endpoint and confirm payload (e.g. top ranks vs known-good: the rarity-test collection #4820=#1).
3. Screenshot pages with playwright-core + Brave executablePath `/Applications/Brave Browser.app/Contents/MacOS/Brave Browser`, vision-inspect for defects.

## Repo state (2026-08-22)

the control room is under local-only git (branch main; commits: init, queue-vocabulary fix `3cb31e3`, P&L tracking `6665644`, saved-scans switcher `032096e`). NEVER push (owner rule: local git only). `engine/osnm-z` is an embedded clone with its own history — shows as permanent `m engine/osnm-z` in status; leave it. Mission P&L records auto-save on every confirmed live mint to `.runtime/pnl/<missionId>.json`; totals at `GET /api/pnl` (PATCH logs proceeds).

## Reveal watcher (separate from web app)

Cron `testcollection-reveal-watch` (job 24f61a028317), every 2m, no-agent script `~/.hermes/scripts/testcollection_reveal_watch.py`: probes sample URIs, sweeps + ranks + iMessages (AppleScript Messages.app fallback; imsg CLI not installed) on reveal, writes `~/.hermes/rarity/testcollection/scores.json`, one-shot via state file.

## Live test cases

- **Robinhood mfers `0x09127A4Ef72639959967FE39864D462618404a84`** (slug robinhood-mfers-nft, pre-reveal as of 8/22) — the user flagged it as "about to reveal"; next live fire drill.
- THE TEST COLLECTION `0x1e64861134001d446a2af01f74a59326c259c9f8` (2000 supply, pre-reveal as of 8/22) — scan returns correct pre-reveal note; re-scan on reveal is the live fire drill (~4–5s expected).
- the test collection `0xde0acefc89d4cf5f4ce45a4fb8a51aa355091b44` (6969 supply, pre-reveal) — ~15s expected on reveal.
- the rarity-test collection `0x512faa1354c8d634cd0e78e6ec5ba1d9fe19d55c` (5000, revealed) — regression baseline: #4820 rank 1.

## Queue-and-forget (Queue Mint)

The queue feature (queue a bounded mint that auto-executes when the public SeaDrop stage goes live) was found DEAD-ON-ARRIVAL 2026-08-22 and fixed in commit `3cb31e3`: `lib/server/seadrop.ts` `stageState()` emits `"scheduled"/"live"/"ended"/"unconfigured"` but the queue UI/API/domain checked `"future"/"active"` — tests passed only because they injected the same wrong strings. Pitfall for any state-machine work here: **the canonical stage vocabulary lives in seadrop.ts; never invent synonyms in downstream gates**, and don't trust green tests when the test fixtures hardcode the same strings as the code under test. Live proof pattern: `/api/plan` on real CAs returns the actual state string; queue POST then passes the state gate and fails only at the later restricted-stage guard (correct behavior).

## Smart wallet tracker

Panel 07 + `/api/smart-wallets` (GuarEmperor degen list, coordinated-mint signals). Implementation map, the two session-costing bugs (rawRpcCall object-vs-JSON hang, getLogs topic1/topic2 incoming-outgoing trap), timings, and verification: `references/control-room-smart-wallets.md`.
