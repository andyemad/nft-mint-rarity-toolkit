# OpenSea listing (sell side) — Seaport v1.6 on Robinhood chain

Status 2026-08-24 (late session): WORKING END-TO-END. A real listing was
signed and posted to OpenSea from the user's OG wallet and verified via the
orders-by-hash endpoint (HTTP 200). All wire-shape requirements below are
API-VALIDATED, not inferred.

## Validated wire shape for RH-chain listings

- Seaport protocol = v1.6 `0x0000000000000068F116a894984e2DB1123eB395`.
- **SignedZone V2 is REQUIRED**: zone `0x000056f7000000ece9003ca63978907a00ffd100`
  with `restrictedByZone: true` → seaport-js emits `orderType` 2
  (FULL_RESTRICTED). OpenSea rejects other order types outright.
- **Conduit key** must be OpenSea's RH conduit
  `0x<REDACTED-PRIVATE-KEY>`;
  zero key is rejected.
- **Fees baked into consideration items** (not seaport-js `fees:` option):
  - OpenSea fee is EXACTLY 100 bps (1%) to
    `0x0000a26b00c1F0DF003000390027140000fAa719`. The ~103 bps seen in one
    sampled live listing is NOT what the validator wants; it hard-rejects
    anything but 100.
  - Creator royalty is REQUIRED (e.g. testcollection: 690 bps to
    `0x66e0e8fc5766f4fb050332f664030c8909fabd77`). Read per-collection from
    `/api/v2/collections/{slug}` → `fees[]` (`fee` is a percent — ×100 for
    bps), skipping the OS-fee recipient.
  - Seller amount = price − osFee − royalty; reject if ≤ 0.
- All recipient addresses MUST be EIP-55 checksummed — ethers typed-data
  hashing throws `bad address checksum` otherwise.
- Post: `POST /api/v2/orders/{chain}/seaport/listings`, body =
  `{ ...signedOrder, protocol_address }`; outer envelope snake_case, inner
  `parameters` camelCase verbatim (`snakeizeBody: false`). Response carries
  `orderHash`. On HTTP 400 read the body text — errors come back as
  `{errors: ["Validation error: …", …]}` listing EVERY problem at once;
  iterate until clean 200.
- Response-key gotcha: `/listings/collection/{slug}/all` returns
  `{listings:[...]}`, `/best` returns `{orders:[...]}`.

## seaport-js configuration that made it work

```
new Seaport(signer, {
  overrides: { contractAddress: SEAPORT_V16 },
  balanceAndApprovalChecksOnOrderCreation: false,
})
createOrder({ conduitKey, zone, restrictedByZone: true, offer, consideration, endTime }, offererAddress)
```

- `balanceAndApprovalChecksOnOrderCreation: false` is REQUIRED when zone is
  set — with checks on, seaport-js crashes with
  `unsupported addressable value (argument="target", value=null)` inside its
  zone-contract resolution on RH chain.
- Clay contract quirk stands: `isApprovedForAll()` reverts even as view call.
  With approval checks off, an unapproved wallet's order posts fine but will
  not fill — surface that honestly rather than auto-broadcasting approvals.
- ethers type identity conflict (commonjs vs esm copies) still needs the
  `signer as any` cast at the constructor.

## Provider construction pitfall

`new JsonRpcProvider(url, { chainId: 4663 })` throws
`invalid network object name or chainId` on ethers 6.17 for unknown chains —
pass `undefined` as network instead. This bit both nft-listing and is why the
route-level `providerFor` should be audited if reused.

## Code state (all type-clean, 750/750 tests green)

- `lib/server/nft-listing.ts` — complete: fetchCollectionFees(), fee math,
  zone/conduit/orderType, raw-body error surfacing (parse `{errors:[...]}`).
- `app/api/nft-inventory/route.ts` — `list` action done: exactly-one-tokenId,
  price + durationSeconds (300–2592000s) validation, ownership check against
  inventory scan before signing, appendOp with `"nft-list"` action (union
  extended in wallet-ops-store.ts).
- UI: NftManagerView has per-token List button (`nm-list-{tokenId}`) +
  shared price input (`nm-listing-price`) + status line (`nm-listing-msg`);
  disabled until price entered; row is now a div wrapping an <a> token link.

## ⚠️ Live artifact — RESOLVED

The rehearsal listing of clay #3309 @ 0.05 ETH (order
`0xd47492ddc041005cb0a1a7f90daacb035779736d16edcec312c2b111a8b82b91`) was
cancelled by the user on 8/24. #3309 is unlisted. Lesson for future rehearsals:
confirm keep/cancel with the user immediately after any live post, and prefer
listing at a price he'd tolerate if it accidentally stays live.

## API-route bugs fixed during first REAL UI use (8/24 evening)

the user's first live use surfaced three route-level bugs the standalone tests
missed — all fixed and verified with real on-chain txs:

1. `providerFor()` in `app/api/nft-inventory/route.ts` still passed the
   `{chainId}` object (the exact pitfall above). Symptom: consolidate button
   showed `invalid network object name or chainId`. Fixed to `undefined`.
2. OG-wallet keyfile lookup: inventory rows carry `ownerName: "OG wallet"`,
   so `${ownerName}_key` resolved to a nonexistent file. Map `"OG wallet"` →
   `bot_wallet_key` before readKey.
3. Pre-transfer ownerOf check: gated contracts revert on EVERY ownerOf, so
   `!onChainOwner` blocked all transfers forever. Semantics now: null/revert
   = "cannot verify — proceed on fresh inventory scan"; a returned address
   that differs from the scanned owner = block. Verified: clay #3309 sweep
   tx confirmed on-chain after these fixes.

## Response parsing + key selection

- OpenSea POST response is snake_case: `{order_hash}` on success,
  `{errors: [...]}` on failure. The parser originally read camelCase
  `orderHash`, so successful posts reported `orderHash: null` and failures
  surfaced as bare "HTTP 400". Read BOTH snake_case keys.
- `apiKey()` in `lib/server/opensea-listings.ts`: env var first, then
  fallback reads secret files under `~/.hermes/secrets/` — prefer the newer
  `opensea_key`; the older `opensea_api_key` file returns "Invalid API key"
  from OpenSea. Without this fallback the whole inventory scan fails with
  "OpenSea API key missing" even though keys exist on disk.

## OpenSea endpoint quirks

- `/chain/{chain}/nft/{contract}/{id}` can 404 for pre-reveal collections
  (indexing lag) even when the token exists — don't use it as an existence
  test; inventory attribution uses the account endpoint instead.
- `listed_by=` filter param on collection-listings was ignored in practice
  (returned other offerers' orders). To find your own orders, page through
  and filter client-side by `protocol_data.parameters.offerer`.
- Verification pattern that works right after posting: GET
  `/orders/chain/{chain}/protocol/{seaport}/{order_hash}` — retrievable
  within seconds even when collection listing indexes lag minutes behind.

## Next.js Turbopack stale-code trap (cost ~30 min)

An orphaned `next-server` (parent pid 1, no watcher) kept serving OLD compiled
code across restarts — source edits never appeared, responses were byte-
identical pre/post restart. Detection: grep the `.next` chunks for a unique
marker string you just added to source; absent marker = stale build. Fix:
`kill -9` the server, wipe `.next`, start `npx next dev` via a tracked
background terminal (no nohup subshell — those die and orphan the worker),
wait for cold rebuild (500s during warmup are normal).

## Research technique (web tools down)

docs.opensea.io is a readme.io React shell with no scrapeable spec. The real
spec lives in official SDK sources on GitHub raw:
- `ProjectOpenSea/opensea-js/src/api/apiPaths.ts` — every v2 endpoint path
- `src/api/orders.ts` postListing() — exact mixed-casing wire shape
- seaport-js README — createOrder usage
- Discover paths: `api.github.com/repos/<org>/<repo>/git/trees/main?recursive=1`
