---
name: web3-claim-verification
description: Use when verifying a crypto project's claims on-chain.
---

# Web3 Claim Verification ("deep dive … verify claims")

Audit a crypto project that makes claims on a website / dashboard — "autonomous
market-making desk pays holders every 15 min", "LP positions live", "telemetry is
public" — and verify them against the actual chain. Scope: token protocols,
yield/rev-share tokens, market-making/fund claims, NFT launches with dashboard
telemetry. Built 2026-09 on Arbitrage Ape (arbitrageape.app, Robinhood Chain):
site looked thin (one-page Next.js SPA, no team/legal), but `/api/status` showed a
LIVE backend (fee token, vault, 3 Uniswap v3 LP positions with tx hashes, ~$21
distributed) — the real question became telemetry-vs-chain, not vaporware-vs-real.

For MINTER-side organic-vs-manufactured forensics see `nft-minter-legitimacy-audit`.
For no-key on-chain data pipelines see `ethereum-data-pipelines`.

## When to use
- "do a deep dive on <url> smart contracts and website, verify claims"
- Judging a rev-share / yield token, trading desk, or fund claim before any buy.

## Phase 0 — Surface recon (terminal, no gateway needed)
1. `dig +short <domain> A NS CNAME` — `*.dns-parking.com` NS = parked (dead).
   `*-dns-0NN.com`/vercel CNAME = Vercel-hosted SPA. Live page + 200 ≠ active backend.
2. RDAP whois: `.app` → `curl -s https://rdap.nic.google/domain/<domain>` (reg date,
   registrar, status). Wayback: `curl -s 'http://archive.org/wayback/available?url=<domain>'`
   + CDX `http://web.archive.org/cdx/search/cdx?url=<domain>*&output=json&limit=20` for
   earliest snapshot (launch recency is a red-flag input).
3. Grab the page: `curl -sL -A 'Mozilla/5.0 …Chrome…' <url> -o /tmp/x.html`. Read meta
description/keywords (the pitch), nav links (routes to probe), and note `noindex`
(SPA pages often return the SPA shell with 404 inside — robots.txt/sitemap will 404).
4. Probe likely routes (/method /docs /terms /privacy /desks …) — SPA returns the
   shell with an inner 404; only real routes return distinct HTML.

## Phase 1 — Find the real backend (the high-value move)
A marketing SPA hides its truth in an API. Do NOT audit the copy — find telemetry.
1. Extract JS chunk URLs: `grep -oE '/_next/static/immutable/chunks/[0-9a-z]+\.js' x.html | sort -u`
2. Fetch each chunk **into a prefixed file** (`aa_<name>.js`), then grep for endpoints:
   `grep -hoE '"(/api/[a-zA-Z0-9/_.-]+|https?://…api…)' aa_*.js | sort -u`
   PITFALL: plain `/tmp/*.js` also catches leftover unrelated JS from past sessions
   (mint dashboards etc.) and pollutes results — always isolate to your prefixed set.
3. Probe each endpoint: `/api/status` is the usual goldmine → JSON with mode, fund
   address, token address, balances, LP positions + tx hashes, payout counters,
   ms-epoch timestamps. Save it: `curl -s … -o /tmp/<proj>_status.json`.

## Phase 2 — Chain verification (telemetry vs truth)
- RH/other blockscout explorers are Cloudflare-walled for plain curl ("Just a
  moment…"). `firecrawl scrape "<blockscout-url>" -o /tmp/out.md` passes — use it
  for both human pages and `/api/v2/…` JSON endpoints.
- Verify on explorer: creation tx + creator (EOA vs factory), is code verified,
  holders, token supply; for each claimed LP position: tx hash exists, pool matches,
  amounts ≈ claimed; trace where balances came from (funding txns) and where
  "distributions" actually went (internal txns / token transfers).
- Timestamps in telemetry are ms epoch — convert (`datetime.fromtimestamp(x/1000, timezone.utc)`)
  and measure the claimed cadence (e.g. "every 15 min" vs nextDistributionAt−lastDistributionAt).
- List every material discrepancy (telemetry says X, chain shows Y) as its own finding.

## Phase 3 — Economic sanity (yield-token red-flag math)
- Token mcap vs vault/backing assets. 1e9-supply token at $217k mcap vs $12.5k vault
  = most of the market cap is narrative, not backing — compute the ratio and say so.
- Realized profit vs mcap: ~$21 realized across $217k token = yield the math cannot
  sustain at the marketed rate. Annualize from two status fetches a few minutes apart.
- Reconcile the protocol's own counters: `feeFlow.claimedUsd 22k` vs
  `distributedUsd 21` — what did holders actually get vs what the operator collected?
- `operatorPnlUsd` negative means the desk itself is underwater — quote it.

## Phase 4 — Three parallel subagents (proven split)
Dispatch 3 in one `delegate_task` call, disjoint scopes, ALL verified up front:
- **A — On-chain forensics**: identity/creation/control of every named contract,
  LP positions, distribution txs, funding trace, telemetry-vs-chain discrepancies.
- **B — Provenance**: domain age, launch platform ("launches on X v2" → research X),
  the market premise itself (do tokenized AMC/NVDA pools really trade on this chain?
  who issues them?), X/community reception, named team/audits (usually none).
- **C — Claim verdicts + risk**: per-claim VERIFIED/PARTIAL/UNVERIFIED/FAILED/
  MISLEADING table, withdrawal/rug vectors, scam-pattern scan, bottom line.
Orchestration rules that make this work:
- Each brief = exact contract addresses, the quoted claims list, working fetch
  commands (the parent tests paths FIRST — subagents inherit broken default tools,
  so paste the commands that demonstrably work), output-file path, and required
  summary shape. Children know nothing of the conversation — say it all in `context`.
- Require each to write a report file (e.g. /tmp/aa_reportA.md) AND return an
  evidence-dense summary; parent consolidates. Verify their claimed txs/hashes before
  repeating them to the user.
- **Design for the 600s delegate cap (validated 2026-09):** forensics children doing
  many firecrawl/RPC round-trips routinely time out with status=timeout and NO summary
  even after 20-30 API calls. Make every child write its report file INCREMENTALLY as
  it goes. On timeout, salvage: read the partial report file AND the live transcript
  (`~/.hermes/cache/delegation/live/<deleg_id>/task-N.log` — tail it for the analysis
  already done), then finish the remaining verification in the parent instead of
  re-dispatching blindly.

## Phase 5 — Operator wallet forensics ("who is really behind this")

Emad's standard follow-ups after the claim verdict: *"check previous deployed coins, twitter link connections"* and *"are you sure the funding wallet is not an exchange?"* Run these on the deployer/keeper/funder EOAs the earlier phases surfaced. Verified 2026-09 on Arbitrage Ape.

1. **Full tx-history scan of each controller EOA** (blockscout `/api/v2/addresses/<addr>/transactions`, paginate to the end). Histogram distinct `to` + `method` per wallet. Prior-launch detection = any `CREATE` (contract creation) tx or any call to a launchpad factory (Pons `launchAndBuy`-style). A clean operator wallet shows 100% of txs against ONE project's contracts.
2. **Funding-tree reconstruction**: the earliest tx of a fresh wallet shows who funded it. Follow the chain up (funder → its funder → …) to the root. For a brand-new project, a root whose FIRST-EVER L1 tx is the same day as the launch = fresh same-day money on-ramped for this project — a strong anonymity/recency signal worth stating plainly.
3. **Exchange-hot-wallet vs trader/bot hub — discriminating tests** (a few hundred payouts to distinct EOAs is NOT proof of an exchange; test, don't eyeball):
   - **Inbound distinct-sender count**: exchanges receive deposits from thousands of addresses. ≤ a handful of inbound senders (1–3) = personal treasury → wallet pattern, not deposit-taking.
   - **Token-trade diversity**: 100+ different micro-cap memecoins through AMM routers (Uniswap Permit2 `permit2TransferAndMulticall`/`aggregate3Value`) = an active trader/bot wallet. CEX hot wallets do not trade memecoins on AMMs with their own inventory.
   - **Explorer tags**: search `/<explorer>/api/v2/search?q=<addr>` and check tags. Exchanges get labelled within hours; untagged = personal.
   - **Generated wallet family**: same 30+ hex mid-string across two otherwise-random addresses (e.g. …a97812cb96acdf810712aa562db8dfa3… in both the ETH root and its Arbitrum funder) is ~2^-136 coincidence — one operator algorithmically deriving a cluster. Check Arb/Eth counterparts for the shared substring.
   - **First action = bridge deposit** (`RelayDepository.depositNative` or similar into the L1→L2/alt-VM bridge): money moved in deliberately to trade, not an exchange standing up an address.
   - Truthfully label residual uncertainty: on-chain behavior never proves identity — say "trader/bot settlement wallet, NOT exchange" only after the above, and keep "same controller" claims tied to the wallet-family evidence.
4. **Twitter/identity links**: decode the X account age from its user snowflake (id → approx creation; e.g. via syndication followbutton info or fxtwitter `user.created`); read the token metadata socials; DexScreener search-by-CA for copycat pairs on OTHER chains (zero-volume BSC fourmeme clones auto-copy trending names — verify the operator's own CA, not the name). No prior crypto brand + no reused wallet = genuinely new entity, not recycled scammer identity — say so.
5. Write findings to the project report (D-style): wallet tree ASCII map, answers to each specific question, and a behavioral fingerprint paragraph (bags held across the same micro-cap casino in matching amounts across wallets = same controller).

## Scam-pattern scan checklist
Fake-yield ponzi (payouts ≪ mcap), honeypot fee token, owner-withdraw not renounced,
mintable supply, "CA revealed at launch" pre-launch marketing, self-reported telemetry
that cannot be cross-checked, no terms/legal/team/disclaimer anywhere, unverifiable
contract code (say "cannot verify — not guessing" out loud), securities framing
("profit to holders") with no entity.

## Pitfalls
- macOS has no `timeout` command (exit 127 ≠ the wrapped tool failing).
- Never trust HTTP 200 + pretty HTML as "real" — the API tells the truth.
- Single-page Next.js: one fetch = whole site; extra routes are client-side only.
- `.app` whois on the registrar line goes to IANA — use RDAP at rdap.nic.google.
- Explorer human pages via firecrawl markdown are readable but noisy; api/v2 JSON
  is cleaner when it comes through.
- Keep the audit read-only; do not interact with project contracts.
