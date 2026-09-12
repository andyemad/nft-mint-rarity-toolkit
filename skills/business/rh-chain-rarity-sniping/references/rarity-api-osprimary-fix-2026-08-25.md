# the control room rarity API 503 fix (8/25) — OpenSea-primary traits + key fallback

## Symptom

`/api/rarity` returned `{"error":"Reveal seen but metadata not fetchable yet —
retry shortly."}` (503) for a REVEALED collection. Reveal detection worked
(on-chain probes) but zero metadata loaded.

## Root causes (two separate routes, two bugs)

1. `app/api/rarity/route.ts` fetched metadata ONLY via IPFS, hard-coded to
   `https://nftstorage.link/ipfs/` — a gateway that 403s from this machine.
   Zero OpenSea usage despite OS indexing traits instantly at reveal.
2. `app/api/rarity-gallery/route.ts` DID have OS-primary logic but read only
   `process.env.OPENSEA_API_KEY ?? ""` — no env var exists, so the OS path was
   silently disabled and it fell through to dead IPFS too.

The working key loader already existed in `lib/server/opensea-listings.ts`:
`apiKey()` tries env then reads `~/.hermes/secrets/opensea_key` /
`opensea_api_key`. Both routes must import and use it.

## Fix shape (applied to both routes)

```ts
import { apiKey as osApiKey } from "@/lib/server/opensea-listings";
// paged /nfts with limit=200, X-API-KEY: osApiKey(), 429→sleep 1200ms+retry,
// paginate via data.next cursor until supply covered or no next.
// IPFS (gateway.pinata.cloud) only as fallback for tokens OS hasn't indexed.
```

TypeScript gotcha: annotating `let data: {...} | null = null` then casting
`await response.json() as NonNullable<typeof data>` narrows to `never`
(TS2339 'Property nfts does not exist on type never'). Declare a named
`type OsNftsPage = {...}` inside/above and cast to that.

## Deploy mechanics (launchd service — critical)

the control room runs under launchd `com.the agent.rh-mint-room` as a PRODUCTION
`next start`, NOT `next dev`. Consequences:

- Dev-mode hot reload does NOT apply; you MUST `npx next build` after route
  edits, or the stale `.next/server/app/api/*/route.js` serves forever.
- Do NOT delete compiled route files without rebuilding — launchd restart will
  then throw MODULE_NOT_FOUND on every request ("Internal Server Error").
- There may be ORPHANED next-server processes squatting on :3000 with stale
  code (ppid 1). Diagnose: `lsof -nP -iTCP:3000 -sTCP:LISTEN` + check
  `ps -p <pid> -o lstart=` vs your edit time. Kill strays, then
  `launchctl kickstart -k gui/$(id -u)/com.the agent.rh-mint-room`.
- Logs: `.runtime/logs/launchd.{out,err}.log`. MODULE_NOT_FOUND there = rebuild needed.

Verified post-fix: `/api/rarity` → `{"revealed":true,"totalRanked":6889,…}` in
~12s first hit (OS pages), gallery route serving ranked tokens with images.
