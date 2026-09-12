# NFT collection-call due diligence (keyless) + keyless X/tweet reading

Refined 2026-08-18 on the user's Maksae/GIWA "alphas" call (Upbit-backed Korean
L2, mascot NFT on Robinhood Chain) and his request to verify a holding-claim
tweet. Use whenever the user shares a mint/collection call and asks "is this a
good opportunity?" or wants a specific claim verified. Complements
`nft-mint-market-analysis.md` (which covers market data); this covers the
*narrative-and-claim* verification side and sizes the position.

## The verification framework

1. **Pin the single linchpin claim and confirm it from the right authority.**
   Extract the one fact the whole thesis depends on (e.g. "holding X
   guarantees you Y on chain Z when it opens"). Then confirm it comes from an
   account with real authority over that commitment — NOT just the brand/mascot
   account. A guarantee from @Mascot is project-claimed; a statement from the
   corporate/chain account is stronger; a written contract or official doc is
   strongest. Say plainly which tier the evidence is, and flag it as the
   difference between a bet and a near-certainty.

2. **Test the "first / scarce on the chain" narrative against supply math.**
   If the mainnet mint (e.g. 5,555 tiles) is larger than the early mint
   (1,111 scrolls), then even if each early scroll maps to one mint, early
   holders are a subset, not the rare core — *early, not scarce*. That changes
   the characterization from "flagship" to "early-access ticket", which
   changes how much it's worth.

3. **Name operational red flags you find, don't rubber-stamp past them.**
   Site down since mint, silent Twitter after mint-out, no exchange-affiliate
   people in the follower list, "official support unconfirmed" — surface each
   as a yellow flag with its implication. Combine them before calling it a
   scam vs. a slow-but-real project.

4. **Frame by net $ vs time/risk, and size accordingly.**
   A low-cost lottery-ticket entry (small size; e.g. bidding 0.0001–0.0002 ETH
   on a collection that hit 0.01) is a legitimate *cheap option* — never a
   position to size up until (a) the linchpin benefit is confirmed from an
   authoritative source AND (b) there's a dated catalyst (mainnet launch).
   An illiquid hold into an undated launch is the risk to name out loud,
   especially for a momentum trader who hates illiquid positions.

5. **End with a clear verdict.**
   Score it (thesis / evidence / risk-mgmt / positioning) and give the single
   fact that would upgrade it from ticket to position. Apply the exit rule
   regardless: never list a paid mint below break-even (price ÷ 0.89).

## Keyless tweet/post reading when web tools are down

When `web_search`/`web_extract` are unavailable (no credits, provider down)
and `xurl` is not installed, read a specific public post or a profile via
public endpoints — these need no auth:

- Single post: `https://cdn.syndication.twimg.com/tweet-result?id=<STATUS_ID>&token=a`
  returns JSON with `text`, `user.name/screen_name`, `entities.urls`.
  The `&token=a` is a fake-acceptable token; the endpoint is keyless.
  NOTE (2026-08-19): this endpoint can return bare `{}` — see the `updated`
  bullet; when it does, use the `/status` variant below.
- Profile summary: `https://api.fxtwitter.com/<screen_name>` or
  `https://api.vxtwitter.com/<screen_name>` returns user metadata
  (name, description, follower_count, verified, website, joined).
- **UPDATED (2026-08-19): the `/status` variants DO work reliably and are the
  best keyless full-post read** — `https://api.fxtwitter.com/<user>/status/<ID>`
  and `https://api.vxtwitter.com/<user>/status/<ID>` return the COMPLETE post
  text (not truncated, `tweet.text`/`raw_text.text`) AND the quoted/retweeted
  post underneath (`tweet.qrt.text` / top-level `qrt.text`). This is the way to
  recover a quoted post's full body without auth. On 2026-08-19 the
  syndication `tweet-result` endpoint returned empty `{}` for the same post
  while fxtwitter/vxtwitter `/status` both returned full main + quoted text.
  Prefer these `/status` endpoints first; fall back to the others if they
  CAPTCHA-gate (they occasionally do).
- The nitter mirrors are mostly CAPTCHA/bot-walled or 404 — don't rely on them.
- To read an org's own curated site description when the profile is terse,
  curl the linked website and strip tags (SPA site may need the JS removed; a
  real company page usually has the roadmap / "powered by" copy in HTML).

## Maksae/GIWA worked example (2026-08-18)

- GIWA Chain: OP-stack L2 run by Dunamu (Upbit's parent), Seoul, real GitHub
  org (viem fork, ERC-4337 bundler, node). Public testnet live; mainnet not yet.
  Legitimate, corporate-backed — not a hype account.
- Maksae: mascot NFT, 1,111 free scrolls on Robinhood Chain; tweets claim
  "each scroll is one guaranteed mint" of the 5,555-tile GIWA collection.
- Key finding: the guarantee tweet (`2088017924091195800`) IS in writing but
  comes from the mascot account, not Dunamu corporate → verified-then-caveated.
- Supply check: 1,111 RH scrolls → guaranteed mint in 5,555-tile collection =
  early-access subset, not scarce flagship.
- Verdict: solid low-cost lottery ticket (~$0.20–0.90/scroll), NOT a size-up
  position until mainnet date + official backing.
