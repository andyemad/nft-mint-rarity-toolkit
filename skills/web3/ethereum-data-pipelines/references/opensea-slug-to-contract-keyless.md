# OpenSea slug → contract address, keylessly (verified 2026-08-21)

Let users paste an OpenSea collection URL instead of a raw CA. No API key needed.

## What works

Fetch `https://opensea.io/collection/<slug>` with a browser UA
(`Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36`)
and `accept: text/html`. The SSR payload embeds `urql_transport` hydration blobs:

```
(window[Symbol.for("urql_transport")] ??= []).push({...});
```

There are MULTIPLE `push(...)` calls per page. Extract each top-level JSON object by
brace counting (respect strings/escapes) then `JSON.parse` exactly that slice —
do NOT try to `JSON.parse` from `push(` to end-of-script (extra trailing data breaks it).
Walk the parsed object recursively and collect entries where:

- `slug` matches the requested slug (case-insensitive), AND
- `address` matches `^0x[0-9a-fA-F]{40}$`
- grab `chain.identifier` and `name` from the same object

Prefer the match whose `chain.identifier === "robinhood"` when a collection spans chains;
otherwise take the first.

## Input parsing

Accept all of: raw `0x…` address, `https://opensea.io/collection/<slug>`,
locale-prefixed variants (`/es/collection/...`, `/assets/ethereum/collection/...`),
query strings, and an `os:<slug>` shorthand. Slugify to lowercase.

## Pitfalls

- **Never regex-scrape `0x[40hex]` from the raw HTML** — the page embeds thousands of
  unrelated contract addresses (token contracts, WETH, storefronts). Only an address found
  INSIDE an object whose `slug` matches counts.
- **Slug collisions across chains**: `opensea.io/collection/mugs` is an unrelated Ethereum
  shared-storefront "Mugs", NOT Robinhood-chain MUGS. Always check `chain.identifier`,
  not just the name.
- 404 means the slug doesn't exist — say so plainly rather than guessing a nearby slug.
- Treat this as best-effort enrichment: if OpenSea blocks or reshapes the page, the raw-CA
  path must remain fully functional.

## Production implementation (reuse, don't re-derive)

the control room ships a tested TS version:
`~/Projects/mint-control-room/lib/server/opensea-resolve.ts`
with `tests/opensea-resolve.test.ts` (5 tests). Exports: `parseCollectionInput`
(address | URL | `os:` shorthand → discriminated union), `extractContractsFromOpenSeaHtml`
(string-aware brace-count parser + slug/chain walk), `resolveOpenSeaSlug` (fetches the
page, prefers RH chain, throws plain-language errors on 404/no-address). Wired into
`app/api/plan/route.ts` so pasting ANY of {CA, OpenSea URL, os:slug} into the control room's
single collection box just works; junk input gets "Enter a valid contract address or
OpenSea collection link." Verified live 2026-08-21: bakemono-crayons URL →
`0x4Ff63Dd0…2B29`, raw MUGS CA still adapter-detected, foreign-origin POSTs still 400.
