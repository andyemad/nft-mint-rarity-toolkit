# Case: 6529.io/sqpx vs x.com/punk6529 (2026-09-04)

Question: "is this person https://6529.io/sqpx the same as https://x.com/punk6529?"
Answer: **No** — different people. sqpx = square_pixel (@fmiasp); punk6529 = "6529",
owner/operator of 6529.io.

## What worked
1. 6529.io/sqpx is a Next.js SPA → blank after tag-strip. Extracted flight payload:
   ```python
   segs = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', raw, re.S)
   blob = '\n'.join(s.encode().decode('unicode_escape', errors='ignore') for s in segs)
   ```
   Profile statements found in blob (self-published, platform-verified):
   - SOCIAL_MEDIA_ACCOUNT/X → https://www.x.com/fmiasp
   - CONTACT/DISCORD square_pixel · CONTACT/EMAIL mfersfilmstudio@gmail.com ·
     CONTACT/WEBSITE linktr.ee/square_pixel
   - GENERAL/BIO: "found myself in a square pixel … art and memes in web3 …
     Decentralized Pizza Network (6529.io/6529pizza)"
   - NFT_ACCOUNTS/OPENSEA: sqpx-selfportraits, lonelychair, uran-collection, seizing,
     nextgenmemes, curtain-digital-echoes
   - Identity block: handle sqpx, ENS display `0x333…e09 - square-pixel.eth -
     vault.square-pixel.eth`, primary_wallet 0xe6dba9bd4e5e7ce88d8a4f4ba02e7b5ecd86b588,
     TDH ~1.05M, REP ~760k, level 62, classification PSEUDONYM
2. X side: fxtwitter for punk6529 → name "6529", bio "http://6529.io", 488,661
   followers (platform owner). fxtwitter for fmiasp → 2,073 followers, bio links the
   6529.io/sqpx profile (member).
3. Wallet characterization (blockscout token-balances on eth): wallet3 0xe6dba9…b588
   holds 117 collections incl. 6529reMemes, Timechains, Azulejo Galo by Bryan Brinkman
   (deep 6529-community member). Contract wallet 0xa413…cb holds 341 collections.
4. Coinbase of evidence: profile self-links + ENS family + ecosystem-native holdings =
   credible mid-tier 6529 artist/collector, distinct from the platform owner.

## Dead ends (don't repeat as primary path)
- OpenSea v2 `/api/v2/collections/{chain}/{slug}` returned NOT_FOUND for these slugs on
  ethereum (some collections may be on Base/non-eth or unindexed keyless).
- OpenSea v1 API permanently removed. DDG html endpoint returned HTTP 202 block.
- firecrawl keyless search intermittently wrote no file that attempt.
