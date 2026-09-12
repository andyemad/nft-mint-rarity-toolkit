---
name: nft-rarity-engine
description: Use for NFT rarity ranks, reveal snipes, rarity galleries.
---

# NFT Rarity Engine

Class playbook for: computing collection-wide rarity ranks that MATCH OPENSEA EXACTLY, detecting reveals, sweeping metadata/images, and rendering a visual gallery. Proven on ComboX (5000), Clay StonKz (6969), NECROCHROME (2000) — all Robinhood Chain.

## The one formula that matters

OpenSea's rarity tab uses **OpenRarity information-content**, NOT the naive sum-of-1/pct method:

```
score(token) = Σ over traits of -log2(trait_count / total_tokens)
rank by score descending
```

Naive trait-frequency scoring produced visible discrepancies Emad noticed vs OpenSea (#2401 showed 71 vs true 353). Info-content matched 5/5 sampled tokens exactly and 0/5000 mismatches in regression. Always use info-content.

## Pipeline (per collection)

1. **Resolve input** — accept raw CA, full OpenSea URL (any locale/`/activity` suffix/query junk), or `os:slug`. Slug→CA via OpenSea page scrape of `push(`-embedded urql JSON; prefer `chain.identifier == "robinhood"` when multi-chain. Reusable code: `~/Projects/rh-mint-command-center/lib/server/opensea-resolve.ts` (`parseCollectionInput`, `resolveOpenSeaSlug`).
2. **Supply + reveal probe** — read-only eth_call: `totalSupply()` (`0x18160ddd`), sample ~8 tokenURIs (`0xc87b56dd + uint256 id`). All URIs identical = pre-reveal; divergence = revealed.
3. **Sweep — SPEED-CRITICAL source order.** Primary: OpenSea API v2 **paged list endpoint** `/chain/<chain>/contract/<ca>/nfts?limit=200` + `next` cursor. It includes FULL TRAITS and image_url per token (per-token single-NFT calls do too, but burst-429 badly). `limit=200` measures ~0.2s/page → ~5s for 5000 tokens across 25 pages (08-24, Clay StonKz/ComboX) — meaningfully faster than `limit=50` (~3.5s/600 → 35s/5000); use 200. Never use the per-token endpoint as the primary sweep (43 MINUTES for 5000 due to sustained-burst 429s). Fallback (for the window right after a reveal before OpenSea indexes it): on-chain tokenURI at 96-way RPC concurrency (~46s for 5000, measured) + IPFS metadata via rotating-gateway worker pool. Expect ~1% RPC failures; rank what you get, report missing count.
4. **Decode ABI string** — offset 0x20, length word at byte 32+24, data from byte 64.
5. **Metadata fetch** — gateway fallback chain matters, gateways rot AND rate-limit differently by load pattern: pinata served single fetches fine but 429'd instantly on 24-way bursts of folder-style CIDs (`baseCID/{id}` = thousands of distinct URIs under one CID root). Deduplicate by distinct URI first; for folder-style collections that dedup does NOT collapse (each id is its own URI), so prefer the paged-list primary above over mass IPFS fetching.
6. **Token images** — come free with the paged list sweep (traits + image_url in one response). Standalone backfill: same paged endpoint, ~51s for 5000. Key at `~/.hermes/secrets/opensea_key`.
7. **Rank** with info-content; persist to disk immediately after computing; render.

## Gotchas

- **Robinhood RPC hostname:** `https://rpc.mainnet.chain.robinhood.com` is the reliable endpoint. `rpc.robinhoodchain.com` dies at TLS handshake ("tlsv1 unrecognized name") from both curl and python regardless of UA/SNI handling — don't debug the client, switch hosts. Backups seen in the wild: `robinhood-rpc.publicnode.com`, `robinhood.api.pocket.network`, `rpc.arrowrpc.com`.
- **Never hand-copy a CID out of ABI hex.** Transcription errors (one dropped char) look exactly like a dead gateway and burn minutes of gateway roulette. Always decode the tokenURI hex programmatically (offset 0x20 → length word → data) and feed the string straight into the fetcher.
- **OpenSea v2 endpoint auth map:** `/collections/<slug>` and `/collections/<slug>/stats` work KEYLESS (curl, no header). Everything per-token or per-listing (`/chain/<c>/contract/<ca>/nfts[/<id>]`, `/listings/collection/...`, `/events/collection/...`) returns 401 without an API key — use the key at `~/.hermes/secrets/opensea_key`. `/collections/<slug>/nfts` does not exist (404) — the paged sweep must use the contract form.
- **Listings feed (floor + per-token prices):** `/api/v2/listings/collection/<slug>/all?limit=50&next=...` pages every active listing (reduce to cheapest-per-token client-side); `/best` variant returns only each token's cheapest order but caps at ~100 rows and does NOT page reliably — use `/all` + own reduction when you need full book coverage. Listings are SLUG-keyed only: a raw CA must first resolve to a slug via `/api/v2/chain/robinhood/contract/<ca>` → `.collection`. Verified live: Necrochrome 87 rows → 75 listed tokens, floor 0.000188; ComboX 535 listed. Reusable code: `~/Projects/rh-mint-command-center/lib/server/opensea-listings.ts`.
- **OpenSea API rejects default python urllib UA with 403** even WITH a valid x-api-key — send a browser UA alongside the key on every request (curl works without one; python does not). Same for the Robinhood RPC from python — a balance/eth_call POST returns 403 without `User-Agent: Mozilla/5.0` (curl auto-sends one, so curl-only testing masks it).
- **Sniper latency is the product.** Emad's framing: "a rarity sniper is meant to be faster than seeing it on OpenSea — knowing which tokens are rares so we can bid on them; maybe even without the image at first but ranked by rarity." Design for ranks-in-seconds, images-later: rank as soon as traits land, backfill images in the background (they appear on next page load from the disk cache). A scan that takes minutes loses the edge.
- **Cache every completed scan to disk** (`.runtime/rarity/<lowercase-CA>/ranked.json`), serve memory→disk before re-sweeping. Measured reload: 45ms vs 10.5s fresh. Support `refresh=1` to force.
- Robinhood RPC rejects default python UA with 403 — send browser UA. Also rejects calldata without `0x` prefix (-32602 hexutil error).
- **eth_getLogs topic positions for ERC-721 Transfer:** topic1 = from, topic2 = to. `topics:[null, wallet]` silently filters on FROM (outgoing) and also matches Approval-style events — plausible-looking results that decode-filter to zero. Incoming = `topics:[TRANSFER_TOPIC, null, wallet]`. Sanity-check a known-active wallet over a wide window before believing a zero.
- **rawRpcCall returns payload.result verbatim** — a hex string for scalar methods but an ARRAY/object for eth_getLogs. Never JSON.parse() it; Array.isArray() first. JSON.parse-on-object throws per call and × retries across a wallet sweep turns into a minutes-long hang with clean server logs.
- One transiently-empty token in your trait dump skews EVERY count by -1 across its trait types (found: ComboX #3787). Sanity check: per-trait-type sums must equal total supply; find and refetch any empty-trait token before ranking.
- Empty URI ≠ missing token: probe id boundaries before assuming sweep range (NECROCHROME ids are exactly 1..2000).
- IPFS image URLs can be `.gif` — render as-is in `<img>`.
- Long-running Next.js route handlers: a multi-minute GET will outlive client patience and can die with "Empty reply from server". If a sweep could exceed ~60s, return fast (pre-reveal status / partial) and continue work in a background task rather than holding the response open.
- **OpenSea listing "price" fields lie if you grab the wrong element.** In a listing's `consideration` array, the LAST item is the fee recipient, not the total. The buyer pays `sum of all consideration amounts` (seller cut + OpenSea fee). For THE POOL this made floor look like 0.000018 ETH when the real cheapest buy was 0.00178 ETH — 100x off. Always sum consideration, or read `value` from fulfillment_data.
- **seaport-js bundled contract ABI has no `orders()` view** and its typed wrapper exposes only write functions + getOrderStatus/getCounter. To query on-chain orders, hand-encode via `contract.interface.encodeFunctionData` against a raw provider call — or skip on-chain order discovery entirely and use the API listings endpoint with the key.
- **Checksummed vs lowercase addresses silently break saved-collection state binding.** `parseCollectionInput` returns `getAddress()`-checksummed CAs and the API echoes them back verbatim, but persisted registries/switcher options store lowercase — a React `<select>` bound to `collection.address` then matches NO option and keeps showing the previous label with zero errors. Rule: normalize every collection address to lowercase at every API/UI boundary (`data.collection.address.toLowerCase()` before setState; registries already lowercase). Any "dropdown doesn't update when X changes" bug in this app — check case equality between bound value and option values first.
- **Name resolution must not depend on input format.** Scanning by pasted CA left `name=null` (only OpenSea-slug scans resolved names), so header + switcher fell back wrong/stale. Fix pattern in the gallery route: after resolving the input, always fill name from the registry first, then OpenSea contract endpoint (`resolveOpenSeaName`), and write any newly resolved name back into `.runtime/rarity/collections.json`. Every response carries `collection:{address(lowercase),name}`.
- **Python venv runs get poisoned by user site-packages:** `PYTHONPATH=~/Library/Python/3.9/lib/python/site-packages` is exported in the shell env and shadows venv packages with 3.9 builds (eth_abi/pydantic_core import crashes). Fix: run venv interpreters with `PYTHONPATH=` (empty), NOT just PYTHONNOUSERSITE=1.

## Reference implementations

- `references/mint-room-rarity.md` — where the live code lives in Mint Room (endpoints, pages, data files, service restart command). NOTE: after the speed fix, the sweep primary in `app/api/rarity-gallery/route.ts` is the paged list endpoint; measured 5000-token scan = 10.5s fresh / 45ms cached.
- `references/mint-room-listings.md` — the floor/listings feed added 2026-08-22 (`lib/server/opensea-listings.ts`, `/api/floor`, per-token price merge on the gallery, /rarity UI badges), verified numbers, API quirks (slug-keyed listings, python-UA-403, /best vs /all, top-level contract-endpoint shape), and the saved-scans switcher (now: every scanned collection persists pre-reveal included).
- `references/mint-room-wallet-ops.md` — /wallets 429-outage post-mortem (balance errors + 0/13 distribute from one transient RPC throttle), the retry/backoff + single-nonce fixes now in rpc.ts and wallets/route.ts, and verification steps.
- `references/mint-room-smart-wallets.md` — smart wallet tracker (GuarEmperor degen list, panel 07, /api/smart-wallets): the rawRpcCall-returns-object-not-JSON hang and the getLogs topic1-vs-topic2 incoming/outgoing trap, both with symptoms; measured scan timings; data-source refresh flow.
- `references/seaport-buy-path.md` — the WORKING programmatic buy primitive (verified via eth_call simulation on a live THE POOL listing), the bunker 49/49-revert post-mortem correction (encoding was never broken — dead orders were), guardrail design, and where the code lives (`~/Projects/rh-mint-command-center/scripts/buy.py`).
- `references/collection-artist-analysis.md` — "analyze this collection + its artist" playbook: Moni API endpoint/auth (`api.discover.getmoni.io/api/v3`, `Api-Key:` header), fxtwitter profile ratios, vision-on-local-PNG-composite workaround, identical-token churn forensics (turnover ratio, buyer concentration), stale-vs-good OpenSea key pair.
- Watcher pattern (cron no-agent script probing every 2m, iMessage alert on reveal): `~/.hermes/scripts/claystonkz_reveal_watch.py`; generic reveal watcher with auto-sweep+rank: `~/Projects/rh-mint-command-center/scripts/thepool_reveal_watch.py` (v2 — see post-mortem below).

## Live-editable sniper params in Mint Room (armed 8/24)

Emad wants the sniper's guardrails editable FROM the UI without touching code or
restarting the daemon ("i need to be able to edit parameters. for example per buy
at 0.01, if i wanted to change it to something else"). The `/sniper` Mint Room
page exposes all 7 caps as inputs; saving them must take effect immediately.

**Architecture (the durable pattern):**
- Parameters live in a JSON file (`~/.hermes/rarity/claystonkz/params.json`)
  that is the SINGLE SOURCE OF TRUTH. The Python sniper daemon calls
  `load_params()` at the TOP OF EVERY TICK (fresh read each loop), so an edit
  goes live within one poll interval with **no daemon restart**. Never keep caps
  as Python module constants if they must be UI-editable — read them per-run.
- API route `app/api/sniper/params/route.ts` (loopback-guarded, NEXT.js style):
  `GET` returns current (clamped), `POST` validates + clamps + writes the file.
- **Bounds are enforced in TWO places — the API AND the daemon's reader.** A bad
  write can only ever land within sane limits (`min(max(v,lo),hi)` in both), so
  a typo (per-buy 0.5 ETH) clamps to the ceiling (0.05) rather than silently
  loosening a spend cap. Belt + suspenders by design.
- `app/sniper/page.tsx` + `/api/sniper/status` (read-only live status: daemon
  liveness via pgrep, wallet balance, buys fired, spent) + `/api/sniper/params`
  (edit). Sniper daemon pays zero attention to the UI; it only reads the file.

**CRITICAL React pitfall (cost Emad a bug report):** a `<input type=number>`
whose `value` is derived by parsing `Number(e.target.value)` **on every keystroke
destroys decimal input** — typing `0.015` becomes `15` because the leading `0.`
is re-parsed/re-project away between keystrokes. Fix: keep inputs as **raw
draft strings** (`useState` of `Partial<Record<key, string>>`), set `value` to
the draft (or last-good value), parse ONLY on blur and on save (NaN → keep old).
So the value stays the literal text while typing; a leading-zero decimal survives.
- **Spinner step default is 1** — for ETH-denominated fields set `step` to the
  real scale (0.001) or the arrows jump by whole ETH. User expectation: ETH caps
  nudge by ~0.001 (decimal-grained), integer fields (max buys, richness pool,
  poll secs) by 1.
- **Don't put literal `\u00b7`/`\u2026`/`\u2264` escape sequences in JSX TEXT.**
  They render as the raw backslash sequence, not the symbol. Inside JS string
  literals / template literals escapes are fine; in plain JSX children use the
  real char (·, …, ≤). Caught on the /sniper page (header + footer showed raw
  `\u00b7`).
- During verification I wrote clamped test values into the live armed daemon's
  params (as part of proving the clamp path), then restored Emad's approved caps.
  Lesson: when a params file drives a SPENDING daemon, never leave test values
  live — restore approved values and re-verify before declaring done.

User preference reinforced this session: Mint Room is meant to be the ALL-IN-ONE
surface for the whole mint workflow ("mint room needs to be an all in one suite")
— integrate real tooling into it rather than keeping standalone probes; a
throwaway localhost:8139 status page is not a deliverable. Localhost is for
verification only; the permanent home is the Mint Room page.

## Reveal-watcher failure mode (THE POOL post-mortem — do not repeat)

v1 of `thepool_reveal_watch.py` worked pre-reveal but FAILED at exactly the moment
that mattered: on flip it swept all tokenURIs on-chain then fetched ~1777 IPFS
metadata files per tick, got RPC/IPFS 429-throttled EVERY run, printed nothing,
and the cron logged `ok` for hours (empty stdout = silent by design). Emad caught
it: "the pool revealed a long time ago... something broke." Rules:
- **Watcher primary source = OpenSea paged list** (`/chain/<c>/contract/<ca>/nfts?limit=50` + next cursor, traits included) — same as the sniper; never mass-fetch IPFS inside a 2-minute cron tick.
- **Alert-once state file**: after first successful rank, subsequent ticks exit silently even if ranked.json exists.
- **Index-lag guard**: if <90% of tokens have traits indexed yet, wait for a later tick rather than ranking a partial collection (partial counts skew every rank).
- **Test a watcher by running its script MANUALLY at the expected trigger moment** — "cron status ok" only means the process ran, not that it did anything. Silent-by-design watchers need one deliberate manual fire to prove the alert path.

## Reveal-snipe economics (what to actually tell Emad)

When he asks "reveal is in X hours — will Rarity Sniper rank rares ASAP so I can snipe?" the honest mechanics:

1. Artist flips baseURI/tokenURI on-chain (one tx or batched); ownership doesn't change, only what tokenURI points to.
2. OpenSea re-indexes metadata per token (minutes–hours across a full collection) and recomputes OpenRarity.
3. Rarity Sniper's crawler lands within minutes of OpenSea — sometimes faster, sometimes slower; no SLA.

The real edge is NOT watching Sniper's page: **pre-reveal, snapshot every live listing (token id + price)** — pre-reveal sellers list blind at flat prices. At reveal, first party to map ranks onto those listings buys mispriced rares; bot competitors do it in seconds. So the playbook: arm a CID-flip watcher before reveal (poll sample tokenURIs until they diverge from the shared pre-reveal CID), auto-sweep+rank on flip (~5-30s with the limit=200 paged sweep), cross-reference top ranks against the pre-reveal listing snapshot, alert with "rank #N listed at floor" targets. Buying stays a separate explicit approval always — and is now on-rails: `~/Projects/bunker-snipe/clay_sniper.py` is a guarded auto-buy reveal daemon (fresh `fulfillment_data` + eth_call dry-run per candidate, hard caps 3 buys/0.010/buy/0.030/day/0.050 reserve), with the fill primitive in `references/seaport-buy-path.md`.

THE POOL (Aug 22) was the live end-to-end run of this playbook and validated it:
watcher armed pre-reveal → detected flip → ranked all 1777 in seconds via the
OpenSea paged endpoint. The v1 watcher's IPFS-heavy sweep failed under 429s
(post-mortem above) — the paged-endpoint rewrite fixed it. Ranks landed AFTER the
reveal had already been public a while, which is exactly the failure mode the
"test the alert path manually" rule now prevents.

## Floor + listings feed in Mint Room (built 2026-08-22)

The sniper's second half — mapping ranks onto live money — is now wired into Mint
Room, closing the gap vs NFTNerds-style tooling (their pitch: realtime rarity +
trades + listings; 0.09 ETH/mo. We have the same core free, local):

- `GET /api/floor?collection=<CA | os:slug>` → `{slug, floor, listedCount, stats:{volume,totalSupply,numOwners}}`. Resolves CA→slug via the contract endpoint.
- `GET /api/rarity-gallery?...&listings=1` — listings-only refresh on a cached scan: merges best-per-token price onto every token (`token.price`, ETH string), returns `slug/listedCount/floor`. Cheap (a few API pages), keeps ranks/images cached; persists back to ranked.json so restarts keep prices.
- Fresh scans auto-merge listings after ranking.
- `/rarity` UI: floor + listed count in header, price badge per card (gold = at/near floor), "Refresh listings" button, listed-at line in detail sheet. Sniper view = sort top ranks by price: rank #550/#1423/#1533 at floor on ComboX was found this way.
- Code: `lib/server/opensea-listings.ts`; pitfall when editing the gallery route: `tokensFinal` is built AFTER image merge but BEFORE listing merge — prices attach to `tokensFinal`, not the earlier `tokens` array.

## Pre-reveal collections propagate + show listings (Emad directive, 2026-08-22)

He rejected the "switcher only shows fully-ranked collections" design: **any
collection scanned into /rarity must persist immediately, revealed or not.**
Implementation: persistent registry `.runtime/rarity/collections.json`
(`{lowercaseCA: name|null}`) written at scan time by the gallery route; the
saved endpoint unions registry + legacy ranked-scan dirs. Pre-reveal scans no
longer dead-end — they resolve slug, fetch live listings, and return the
cheapest ~300 tokens as cards (placeholder tile instead of image, price badge,
"listed" tag, floor + listedCount in header, Refresh listings button alongside
Re-check reveal). Rationale: ranks are impossible pre-reveal but the orderbook
isn't; browsing/sniping listings before reveal is expected, not degraded.
When it reveals, Scan snaps ranks next to those prices.

## Sharing the Mint Room codebase publicly (2026-08-22, EXECUTED — repos live)

Emad opened everything under Mint Room plus mint-field-guide. Audit + publish recipe, proven end to end:

**Pre-publish safety audit pattern:**
- Secrets live OUTSIDE repos in `~/.hermes/secrets/`; `.gitignore` covers `.runtime/` and `.env`. Verify with: `git log --all --diff-filter=A --name-only | grep -iE '\.env|secret|key'` and grep tracked files for hardcoded keys.
- **Final-pass 64-hex scan produces FALSE POSITIVES you must triage, not delete:** contract creation-code hex, keccak constants, EIP-7702 probe addresses, and `0xaaaa…` test wallets all match `0x[hex]{64}`. Triage by grepping context — real private keys sit in keyfiles/env, never inline next to "keccak" or inside `.creation.hex` files.
- Only public constants belong in tree (public RPC URL, zero-address). Key-file PATHS (`~/.hermes/secrets/...`) referenced by code are fine — contributors configure their own.
- Check every submodule's remote visibility (`gh repo view <owner>/<repo> --json visibility`) — but prefer VENDORING over trusting remote repos.

**Vendoring a submodule (Emad's call: "what if they take that repo down?" — right instinct):**
```
git rm --cached engine/osnm-z && rm -rf engine/osnm-z
git clone https://github.com/<owner>/<repo>.git /tmp/upstream
rsync -a --exclude target --exclude .git /tmp/upstream/ engine/osnm-z/
# add '<engine-dir>/target/' to .gitignore (Rust build cache was 2.1GB)
git add engine/ && commit
```
Vendoring also captures LOCAL modifications in the old submodule working tree (~200 lines of config/funds changes here were never pushed upstream). Keep the upstream LICENSE file in-tree + attribute in README.

**Publish steps (gh CLI):**
1. Commit pending work first (house-style message) so contributors get current code.
2. README with real setup: Node version, env vars (`OPENSEA_API_KEY`), key-file path expectations.
3. LICENSE — none = all-rights-reserved; MIT for "build upon it".
4. New repo: `gh repo create <user>/<name> --public --source=. --push`.
5. Flip existing private→public: `gh repo edit <user>/<repo> --visibility public --accept-visibility-change-consequences` (the consequences flag is REQUIRED non-interactively).
6. Before flipping, gitignore local scratch dirs (`/.hermes/`) and push, so untracked junk can never ride along.
- Answer for "can't I share private repos?": only via per-collaborator invites, not publicly.

Live results: `github.com/andyemad/rh-mint-command-center` (public, self-contained w/ vendored engine) and `github.com/andyemad/mint-field-guide` (flipped public, 98 commits of history intact).

Identity note told to Emad: these repos tie NFT tooling to his GitHub identity (already linked to ALMtracker); anonymous separation would need a fresh account.

## Approval-gate friction pattern (cron + workspace approvals)

Arming a cron that can deliver messages requires `workspace_propose` with
`actions:["cron.create"]` + matching `cron_actions` payload, then
`workspace_decide("yes")` → `workspace_consume` → retry the create WITH
`approval_id=` set on the cronjob call itself (omitting it fails again even after
consume). A consumed approval cannot be replayed — if the create errored before
the approval_id was attached, re-propose an identical slate rather than reusing
the old one. Budget one extra user "yes" for this round-trip; warn Emad when the
first yes didn't land instead of silently re-asking as if new.

## User preferences (Emad)

- Wants paste-any-collection scanning UX like the mint bot — never per-collection hardcoded tooling.
- Visual galleries with actual NFT art, rank badges, trait counts — text lists alone were "good but" insufficient; he asked for CloneX-style visualization unprompted.
- Ranks must match OpenSea exactly; he checks and notices discrepancies.
- Alert-on-reveal via iMessage to <operator-phone-redacted>; buying is always a separate explicit approval.
- He asks "how will the reveal work / can I snipe rares?" — answer with mechanics + edge strategy (see Reveal-snipe economics), not just "wait for OpenSea." Offer to arm the watcher; silent-until-flip polling, then ranked targets + live listings.
- Don't push ranked lists at him when he has no position in the collection ("i don't own any frogs why are you telling me top 10"). Rank data is only actionable for him as a BUY target list — lead with listings-vs-ranks cross-reference, not raw rankings. And never volunteer buys: he explicitly sets "check listings but i don't wanna buy anything" boundaries; read-only until he asks.
- Anything scanned into the rarity page must propagate to the switcher immediately, pre-reveal included; pre-reveal collections still show live listings. "If I put a collection into this page, it needs to propagate no matter what."
