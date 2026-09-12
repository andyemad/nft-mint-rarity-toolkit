# Moni Discover social-intelligence enrichment

Use this when an on-chain mint/NFT dashboard needs selective social-quality and
narrative enrichment. Moni is not an art/image API and not an on-chain source;
it is a crypto social-intelligence layer. Keep its data clearly labeled as
Moni-derived enrichment.

## Verified interface

- API host: `https://api.discover.getmoni.io`
- Authentication header: `Api-Key: <key>`
- Official agent index: `https://moni-discover-api.readme.io/llms.txt`
- Append `.md` to an individual ReadMe documentation page to obtain its
  markdown/OpenAPI definition.
- Key status (free): `GET /api/v3/status/api_key/`
- Store keys under `~/.hermes/secrets/` with mode `0600`; never place them in
  source, logs, screenshots, skills, or final responses.

Validated 2026-08-20: a `moni_...` key returned HTTP 200 from
`GET /api/v3/accounts/RobinhoodCrypto/info/full/`. The response exposed:
`meta`, `smartEngagement`, and `smartProfile`, including Moni Score, smarts
count, total/smart mentions, Smart Tier, project/category tags, chain tags,
account age, and bio-change count. The full-account call costs 8 points.

Do not confuse this API with `https://api.moni.ai`, the separate Moni Printer/
trading-account API. The latter's Swagger uses an `Authorization` header and
contains account, wallet, transaction, withdrawal, and private-key routes; a
Discover `moni_...` key does not authenticate there. Never probe money-moving,
wallet-export, or withdrawal endpoints when evaluating a Discover key.
Red-herring hosts that waste probing time (2026-08-22): `api.monitic.com`
(JSON 404 bodies that look like a real Moni API) and `moni.ai/api*` (marketing
site HTML). Only `api.discover.getmoni.io/api/v3/...` with `Api-Key` is the
Discover API. Wrong PATHS return bare `404: Not Found` plain text (not JSON) —
that reads like API absence but is usually just a wrong path (2026-08-23:
search endpoints guessed by pattern don't exist; use only documented paths).

## High-value endpoint classes

Consult `llms.txt` for current paths and schemas. Useful classes:

- Project discovery: ranked projects and broader raw project candidates.
- Global smart-mention and smart-tweet feeds.
- AI-detected project events: launches, announcements, incidents.
- Account intelligence: Moni Score, Smart Tier, smart network, tags, chains,
  interaction partners, audience/category distribution.
- Historical mentions, smart mentions, and smarts counts over H1/H24/D7/D30/
  D90/D180/Y1 windows.
- Category, chain, and project mindshare.
- Optional tweet indexing and indexed account feeds.
- Moni AI chat over the underlying crypto/social dataset.

Representative documented costs (verify current docs before use): account ID 1,
smart profile 2, full account 8, mention history 2, smart-mention history 4,
start tweet indexing 10, indexed full feed 5, AI chat message 1. Project,
event, and global-feed endpoints are generally charged per returned item.

## Response-shape gotchas (verified 2026-08-23)

- `GET /api/v3/accounts/{handle}/smarts/full/` returns `{"items": [...]}` where
  each item nests `{meta:{userId,userUrl}, smartEngagement:{moniScore,
  interactedAt,...}, smartProfile:{smartTier:{tier}, smartTags:[...]}}`. There
  is NO username field — derive it from `meta.userUrl.split('/')[-1]`.
  `interactedAt` is a unix timestamp: check staleness before calling someone a
  "current" supporter (a top smart interacted in January is historical
  association, not present endorsement).
- `GET /api/v3/accounts/{handle}/feed/smart_mentions/?limit=N` items are
  `{createdAt, type:"NEW_MENTION", data:{mentionBy:{userUrl}, postUrl,
  postId}}` with NO tweet text — resolve each postId through
  `https://api.fxtwitter.com/status/<postId>` to get text + engagement
  (likes/views vs the mentioner's follower count = real reach).
- `history/smart_mentions_count/?timeframe=D30` returns `timeframeChange`
  (+14 = rising) and `sinceFoundChange` — the cheap momentum read (4 pts).
- A brand-new project account legitimately scores 0 with zero smarts
  (@agents4fun was 2 days old) — that is absence of signal, not fakery;
  say which.

## Integration pattern

Use Moni as a selective enrichment stage, not a high-frequency polling source:

1. Detect candidates from authoritative on-chain data first.
2. Enrich only top/visible candidates with account score/profile.
3. Pull histories only when a current signal warrants trend confirmation.
4. Require agreement between on-chain activity and credible social momentum
   before producing a high-confidence alert.
5. Cache responses according to their analysis window and record point cost.
6. Check `/api/v3/status/api_key/` before and after batches; expose remaining
   monthly capacity and throttle to the plan's RPS.
7. Label scores as descriptive social signals, not proof of demand, safety,
   identity, or investment quality.

For a small Free allowance, continuous polling burns the quota quickly. A good
shape is public/on-chain detection → Moni lookup for shortlisted projects →
alert only on corroborated momentum.
