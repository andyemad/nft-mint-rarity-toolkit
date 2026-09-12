---
name: pseudonym-identity-research
description: Profile pseudonymous identities across X, ENS, and wallets.
---

# Pseudonym Identity Research ("is this the same person as …?")

Use when Emad asks whether two online identities are the same person, or who a
pseudonymous artist/collector/trader/project account really is. Ground the answer
in the person's OWN self-published, platform-verified links (profile statements,
ENS, linked X handle) — never infer identity from display names or branding alone.

Built and verified 2026-09-04 on: "is https://6529.io/sqpx the same as
https://x.com/punk6529?" → **NO**: sqpx is pseudonymous mfer-ecosystem artist
square_pixel (@fmiasp); punk6529 ("6529", 488k followers) runs 6529.io itself.
Full worked case: `references/6529-sqpx-case.md`.

## Method
1. **Fetch both targets** with a browser UA (`curl -sL -A 'Mozilla/5.0 …Chrome…'`).
   For JS-rendered Next.js pages the HTML strips to near-blank — mine the flight payload:
   - `re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)`, then
     `s.encode().decode('unicode_escape', errors='ignore')` per segment, join → blob.
   - Grep the blob for `statement_group`/`statement_type` records (6529.io identity
     pages): SOCIAL_MEDIA_ACCOUNT/X, CONTACT (discord/email/website), NFT_ACCOUNTS/OPENSEA,
     GENERAL/BIO — these are self-published verified profile statements.
   - Grep `primary_wallet`, `"wallet":"0x…"`, ENS display strings, TDH/REP/level fields.
2. **The profile's own X-handle statement is authoritative**: a platform identity page
   that lists handle + ENS + discord + linktree + email forms one coherent identity.
3. **X identity of the other party**: `https://api.fxtwitter.com/<handle>` gives name,
   followers, bio, url. A bio pointing at the platform plus a huge follower count =
   platform OWNER; a small-follower handle hosted ON the platform = a member.
4. **Wallet/ENS cross-check**: blockscout `/api/v2/addresses/<wallet>/token-balances`;
   characterize the collection mix — ecosystem-native tokens (6529reMemes, Timechains)
   in quantity mark a deep community member vs a tourist. Multiple linked wallets are
   normal (primary + vault + old EOA); check all the profile lists.
   - **Fastest single-call wallet identity (when you hold an OpenSea key):**
     `GET https://api.opensea.io/api/v2/accounts/{address}` with `x-api-key` returns
     `username`, `ens_name`, `bio`, `website`, and `social_media_accounts[]` in one shot.
     X handle = `[s['username'] for s in (socials or []) if s.get('platform') == 'twitter']`.
     This is the right tool for bulk profiling (hundreds of wallets) and for checking the
     other side of an identity question without a browser. Pace ~0.5 s/call and write the
     results incrementally (every ~25) so a timeout does not lose the batch — a 430-wallet
     sweep runs ~5 min. Bulk cohort work built on this: see the `ethereum-data-pipelines`
     skill's `references/cross-collection-wallet-cohort-forensics.md`.
5. **Deliver verdict + evidence chain** (profile self-links → ENS → holdings), and say
   the platform context out loud: "profile hosted on 6529.io ≠ 6529 himself."

## Pitfalls
- Display names/branding are NOT identity: square_pixel's name literally contains mfer
  goggles (⌐◧-◧) but he is neither mfers nor 6529. Trust linked handles over looks.
- OpenSea v2 collection endpoints 404 for non-ethereum slugs and 401 keyless — do not
  block on them; use blockscout holdings and the platform's own NFT_ACCOUNTS statements.
- If DuckDuckGo-HTML or firecrawl keyless search fail (202/no-file), the page flight
  payload + first-party APIs are the reliable path — do not conclude "not found" from
  search failures alone.
- web_search/web_extract may be down; curl + payload mining works without them.
- Separate "identity" (who controls the handle) from "standing" (TDH/REP/followers /
  ecosystem-native holdings) — report both, clearly labeled.
- **A `bio` verification-gate code is NOT identity.** Strings like `VULCAN-x6dg1b5d`,
  `VERIFY-…`, `GREMLIN-…`, `DRIP-…`, or a `gated` / `Collab.Land` mention are third-party
  gate/verification-bot tags. They are useful as a *population* signal (one such tag ran
  26.6% in a multi-launch NFT cohort vs 13.6% in a single-collection baseline) but they do
  not identify a person or prove two wallets share an operator. Report the over-representation
  as a correlation and label the meaning as unresolved unless you actually resolved it.
- **An OpenSea handle is not X presence.** In a 497-wallet sweep, 426 had an OpenSea
  `username` but only **45** had a linked X handle. Never write as if the crowd is on X
  unless you resolved the handle — and say the split explicitly when the user wants
  "their social medias".
