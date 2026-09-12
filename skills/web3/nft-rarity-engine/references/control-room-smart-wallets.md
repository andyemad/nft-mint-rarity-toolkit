# Smart wallet tracker (GuarEmperor degen list) — built 2026-08-22

Feature: the control room tracks 159 externally-published "smart money" NFT wallets,
scans their incoming ERC-721 activity on Robinhood Chain, and surfaces
coordinated-mint signals (≥3 tracked wallets minting the same collection inside
the scan window).

## Where the code lives

- `lib/server/smart-wallet-store.ts` — typed load/save of
  `.runtime/smart-wallets.json` (`{source, notion, fetched, wallets:[{address,rank,tag}]}`),
  address validation + dedupe, atomic write (0600).
- `lib/server/smart-scan.ts` — `scanSmartWalletActivity(windowBlocks)`: reads head block,
  one sequential `eth_getLogs` per wallet, decodes incoming Transfers with an
  ethers Interface, groups mints by collection, emits signals where ≥3 distinct
  tracked wallets minted from zero in-window. Errors collected per wallet, never fatal.
- `app/api/smart-wallets/route.ts` — GET = scan (60s in-memory cache, `?window=`
  500–100000 blocks clamped, `?refresh=1` bypass); POST = replace the wallet list
  (validates + caps at 2000). Loopback-guarded like every other route.
- Dashboard: panel **07 SMART WALLETS** in `components/CommandCenter.tsx` —
  tracked/active counts, top signals as buttons that drop the collection into
  the mint box, Rescan button. Startup fetch validates the response shape before
  setState (the ui.test fetch stub returns a plan object for unknown URLs — a
  blind `setState(json)` crashed the test; validate or guard every new client
  fetch against foreign shapes).

## THE two bugs that cost the session (do not repeat)

1. **rawRpcCall returns payload.result VERBATIM.** For `eth_blockNumber` that's a
   hex string; for `eth_getLogs` it is ALREADY AN ARRAY (object), not JSON text.
   `JSON.parse(raw)` on it throws → retry ×3 with backoff per wallet → 159
   wallets × retries = multi-minute API hang and "Empty reply from server".
   Symptom: status endpoint fine, new endpoint times out, server logs clean.
2. **eth_getLogs topic positions:** Transfer(address indexed from, address indexed to, uint256 tokenId)
   → topic1 = FROM, topic2 = TO. Querying `topics:[null, topicTo]` matches
   topic1 == to-position, which actually filters on FROM (outgoing transfers)
   AND matches any event whose second indexed arg equals the wallet (Approvals
   included) — results look plausible but decodeIncoming filters them all out
   and you report "0 active" while real activity exists. Incoming transfers:
   `topics:[TRANSFER_TOPIC, null, topicTo]`. Verify with a known-active wallet
   over a wide window (one wallet had 26 incoming transfers / 100k blocks but
   showed 0 under the wrong query) BEFORE trusting a zero.

Also fixed en route (pre-existing, not ours): `app/api/rarity-gallery/route.ts`
had `catch(() => null ? null : null)` — an always-falsy expression that failed
`next build` type check. If the build suddenly fails after pulling unrelated
changes, run `npx tsc --noEmit` and grep for TS2873-class errors.

## Measured performance

159 wallets, sequential getLogs (no concurrency needed):
- 10k-block window: ~10s end-to-end via API.
- 100k-block window (~2 weeks): ~11s.
Python probe earlier measured ~35s for the same sweep — Node/undici keep-alive
is faster; either way no batching required at this wallet count.

## Data source

Wallets scraped from @GuarEmperor's public Notion "GE Smart Money Wallets"
(tweet 2091211118257774910): 5 tag groups ×~32 wallets (QUOTRONS, RH MACHINES,
Stackers, bulls runners, zaibatsu wagies). Scraping method (Notion API walls +
r.jina.ai view-render route): `research/terminal-web-research/references/notion-public-database-scrape.md`.
Master copy: `~/.hermes/rarity/ge_smart_wallets.json`; runtime copy:
`.runtime/smart-wallets.json`. Refresh by re-running the jina scrape and POSTing
to `/api/smart-wallets`.

## Verification checklist

1. `npm run check` full pass (test+lint+build+e2e) — all green 2026-08-22.
2. `launchctl kickstart -k gui/501/com.the agent.rh-mint-room`, wait for `/api/status` 200.
3. `curl 'http://127.0.0.1:3000/api/smart-wallets?window=100000'` → expect
   walletCount 159, active >0 (if 0 with no errors, suspect bug #2 above),
   errors [].
4. Second call within 60s returns `cachedForMs` — cache working.
