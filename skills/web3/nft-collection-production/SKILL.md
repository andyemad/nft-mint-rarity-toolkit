---
name: nft-collection-production
description: Use when creating/minting an anonymous NFT collection.
---

# NFT Collection Production (generative art + mint path)

Produce a mintable NFT collection end-to-end: procedural trait-layer art with
real generative consistency, proof-of-quality verification, metadata/IPFS
planning, and the anonymous Robinhood-chain mint path. For the DATA side of
NFT work (watching mints, market analysis, wallet P&L) see
`ethereum-data-pipelines`; for collecting reference-art/collection intel
(drop stages, floor, volume, gross mint revenue) see its
`references/opensea-collection-page-intel.md`. This skill is about
PRODUCING the collection.

## Honest gate FIRST (before writing art)

Say this plainly up front — Emad has been burned by hype-then-deflate framing:

- Art is NOT the moat. A cheap anonymous PFP launch with no buyer channel nets
  ~$0; gross mint fees (e.g. $150 on 1,593 × $0.094 mints) are tiny and NOT
  profit. The reference collections that work pull from meme-IP recognition +
  a Twitter/X distribution channel.
- Keep verdicts in net$ vs time/risk terms, give the honest race/cost, and
  let Emad decide "worth it". Do not over-promise.
- IP: NEVER 1:1 clone a copyrighted meme character (Pepe the Frog = Matt
  Furie; Milady art direction = Remilia). Recreate the STYLE with an
  ORIGINAL character and a different meme fusion. Flag takedown risk when he
  points at a collection to copy.
- **Deliver the honest gate ONCE, then BUILD — don't re-lecture.** Emad
  already knows the no-buyer-room math; when he says "make it work", he means
  build the thing that makes degens FOMO, NOT re-explain why distribution is
  the ceiling. Saying "you can't make money at 24 supply / you need a room"
  more than once reads as refusing to work and enrages him (real 2026-08-19
  blowup). State the race/cost once, record the objection, then execute the
  FOMO build. Refusing to build because the honest view is pessimistic is a
  morale failure, not diligence. He will happily pay for a degenerate-FOMO
  page even on a small supply if it's built well.
- Anonymity: mints use a fresh throwaway wallet (bot ops wallet exists at
  ~/.hermes/secrets/bot_wallet_key); no hired artists; never discuss these
  plans on Discord (Discord = tooling only, 100+ paying members).
- **Anonymity is broken the moment you FUND the deploy wallet from any wallet
  linked to Emad.** A new wallet is not anonymous on its own — it becomes
  linked the instant any on-chain tx moves value from a known wallet to it.
  Filling it from the bot wallet (or any owned wallet) leaves a permanent,
  public funding trace: botWallet → deployWallet → contract. Anyone can
  follow it and tie the collection to him. This was a real 2026-08-19 failure
  (contract 0xfC700 burned this way). To keep a launch anonymous the deploy
  wallet MUST be funded from an unrelated source Emad supplies: an exchange
  withdrawal to a brand-new wallet, a fresh fiat on-ramp, or any wallet with
  no prior tx link to him. I cannot fabricate anonymous funds — always get
  that source from Emad, and never use the bot wallet/any owned wallet to seed
  an "anonymous" mint.

## Procedural trait-layer generator (Pillow) — the pattern

Diffusion (FLUX etc.) can't hold character consistency across thousands of
tokens. The production method is PROGRAMMATIC LAYER COMPOSITION — same method
used by meme collections: flat fills, thick black outlines, trait PNG/layers
composited per token. Working example: `~/Projects/meme-mint-lab/generate.py`
(proof sheet + 6 sample tokens under `output/`).

Architecture (canvas 1000×1000, all drawn with PIL primitives):

1. **Backgrounds**: gradient + chunky dithered noise overlay (small random
   noise image upscaled NEAREST, then blend dark/light per noise bit) — gives
   the retro dither feel. Variants: sky (with cloud blobs), sunset, grass,
   void, city (building rects + lit windows).
2. **Base character**: rounded-rect head + ears + neck + torso with black
   outlines (width 8); skin/shirt colors as trait parameters.
3. **Trait layers in z-order**: bg → body → back-hair → eyes → mouth →
   front-hair → hat → accessories → shirt text. Long hair drawn BEFORE the
   face, hats/glasses AFTER.
4. **Trait dicts** per category (bg, skin, back_hair, front_hair, hat, eyes,
   mouth, accessory, shirt, shirt_text). `total_combos()` = product of all
   category sizes — must comfortably exceed supply (3.4M for a 3,333 supply).
5. **Shirt text**: chunky font (Impact/Arial Bold from
   /System/Library/Fonts/Supplemental/), centered, `stroke_width` black
   outline, meme phrases (NO SLEEP / STILL UP / 4AM CLUB / WAGMI / MINT).
6. **Proof sheet**: 12 random tokens in a 4×3 grid, seeded RNG for
   reproducibility, then vision-check the whole sheet.

## Art direction: ON-CONCEPT **and** GENUINELY AESTHETIC — not either/or

When Emad asks "what can YOU come up with" (e.g. after Claude runs out of
credits on art), the bar is TWO things at once:

- **On-concept + expressive + memeable** (NOT technically-polished-but-generic).
  Claude's abstract 3D mechs were excellent but off-concept for a themed
  collection — generic 3D collectibles that fit any project.
- **Genuinely aesthetic / has PRESENCE** (texture, mood, light, grain, depth).
  Emad rejected flat-vector cap-art as "this sucks" and rated the ORIGINAL
  glitch/pixel sleepless-trader tokens higher because they had a vibe. His
  words: "it doesn't have to be 3d, just something really aesthetic."

**Do not use hand-coded Pillow primitives for reference-grade collectible
illustration.** Emad rejected three such passes—including a neon-on-black
Cash Dogs-inspired corgi sheet—as "MS Paint slop." Bloom, gradients, grain,
and cleaner anatomy can improve a primitive drawing, but they cannot supply
the deliberate line weight, shape language, surface finish, or illustrator-led
polish of references such as Adam Bomb Squad. Never describe a merely coherent
proof sheet as successful, collectible, or "the one" before the user judges it.

Use this tool gate:

1. Inspect the actual reference at full-item scale, not only its banner or tiny
   marketplace grid. Separate subject, silhouette, line treatment, rendering,
   palette, texture, and trait-system quality.
2. Produce ONE benchmark character with a real image-generation/illustration
   model or a human-made master base. Compare it blindly against the reference
   quality bar before building traits or a generator.
3. If the benchmark looks like geometric vector construction, stop. Do not
   iterate through more hats, props, bloom, or anatomy fixes—the rendering
   method is the bottleneck.
4. Only after the benchmark passes should production move to consistent master
   art + trait overlays, reference-conditioned generation, or a 3D renderer.
   Deterministic seed→PNG→metadata remains mandatory, but determinism is not a
   substitute for art quality.
5. Confirm whether the user is asking for the existing collection's theme or a
   completely independent art demonstration. Do not automatically re-skin the
   current project.

- **Auditing/fixing the trait taxonomy of an EXISTING collection (local images
  + catalog JSON)?** Multi-pass vision audit pipeline, tiebreak rules for
  vision self-disagreement, and the no-hand-typed-ID builder pattern:
  `references/vision-trait-audit.md`.

- **Learning a style from example collections ("design my own based on high
  quality art")?** Reference-sample fetching workflow (keyless OpenSea
  collection endpoint → on-chain tokenURI → metadata/image pull), the
  extracted style DNA of submitted references (Shadow Wolves, HOWLERZ,
  Pudgy Penguins + the cross-reference "collectible-grade bar" synthesis and
  lane matrix), and the verified RPC/gateway workarounds:
  `references/style-profile-shadow-wolves.md` (profiles appended
  2026-08-22; append future collections' profiles to this file).
- **Trait-system anatomy (the "bits and parts", not whole-token art)?** Emad
  corrected the framing: style study is about TRAIT ANATOMY — slot structure,
  variant-pool shapes, weighting, cross-layer named sets. Measured
  distributions from Shadow Wolves / HOWLERZ / Pudgy Penguins plus the
  design checklist: `references/trait-anatomy-top-collections.md`. Run the
  measurements yourself with `scripts/trait_sampler.py` (stdlib-only;
  usage in its docstring; use --pacing and workers=2 for IPFS-hosted
  metadata, parallel is fine for S3/Arweave).
- **Trait-system anatomy (the "bits and parts", not whole-token art)?** Emad
  corrected the framing: style study is about TRAIT ANATOMY — slot structure,
  variant-pool shapes, weighting, cross-layer named sets. Measured
  distributions from Shadow Wolves / HOWLERZ / Pudgy Penguins plus the
  design checklist: `references/trait-anatomy-top-collections.md`. Run the
  measurements yourself with `scripts/trait_sampler.py` (stdlib-only;
  usage in its docstring; use --pacing and workers=2 for IPFS-hosted
  metadata, parallel is fine for S3/Arweave).

Technical Pillow debugging notes remain in
`references/art-direction-on-concept.md`, but they are prototype/debugging
techniques—not evidence that Pillow primitives can reach premium PFP quality.

## Verification (mandatory before calling it done)

- Render a 12-token proof sheet and vision-analyze it: character consistency
  across tokens, layer z-order correct, no broken/floating elements.
- Verify trait-combo count > supply.
- Emad rejects static mockups — the deliverable is the working generator +
  real rendered tokens, given as exact absolute local paths for Path Finder.

## Pitfalls (all hit in practice)

- **Hardcoded color vs trait parameter**: the "sleepy eyes" eyelid used a
  global skin constant, so darker skins got pale eyelids. Any trait-drawn
  detail that must match another trait (eyelid/skin, brim/cap) must take the
  trait value as a parameter.
- **seadn.io collection media is often AVIF**: `file` says "ISO Media, AVIF
  Image"; convert on macOS with `sips -s format png in.avif --out out.png`.
  Some preview_media URLs 404 — confirm bytes before vision-checking.
- **vision_analyze rejects ~1MB+ images**: keep proof sheets at 12 tokens
  (4000×3000 was fine at ~250KB PNG); downscale if larger.
- **Fiverr-style "NFT art" gigs are already AI-assisted** — recreating that
  tier of art in-house is trivial and $0; don't let art cost/effort be the
  blocker in any go/no-go conversation.

## Mint path (when Emad says go)

1. Art: generator producing N unique combos > supply (above).
2. Metadata: per-token JSON (name, description, image IPFS URI, trait
   attributes); batch-upload images + metadata to IPFS (pinata or local ipfs).
3. Contract: ERC-721 SeaDrop-style on Robinhood chain. RH gas is ~0.04 gwei —
   a full EVM deploy is realistically $1–12 total, so gas cost is NOT a
   gate. See `ethereum-data-pipelines` pitfalls for the verified numbers.

**VERIFY the contract compiles BEFORE proposing deploy — no Foundry needed.**
With only `python3` + OpenZeppelin from npm you can compile-check via
`py-solc-x`'s `compile_standard` (the standard-json path). Working source in
`scripts/compile_check_sol.py`, run from the contract dir after
`python3 -m venv /tmp/solcenv && /tmp/solcenv/bin/pip install py-solc-x` and
`npm i @openzeppelin/contracts@5.0.2` in a temp dir. Gotchas that cost 4
failed attempts (all real, all fixed in that script):
- py-solc-x's `compile_files` does NOT forward `--include-paths` to solc
  (`UnknownOption`) — you must use `compile_standard` instead.
- `compile_standard` wants a Python dict; passing a json string throws
  `AttributeError: 'str' object has no attribute 'get'`.
- Source-dict KEYS must equal the import path, so the relpath `base` must be
  the `node_modules` dir (keys become `@openzeppelin/contracts/...`), NOT the
  `@openzeppelin` parent — otherwise `ParserError: Source
  "@openzeppelin/... not found`.
- solc 0.8.26 handles OZ 5.x; install via `solcx.install_solc("0.8.26")`.
- Deliverables: `contracts["<file>.sol"]["<Contract>"]["evm"]["bytecode"]
  ["object"]` = deploy bytecode; persist `.abi.json` + `.bin` as artifacts.
- Pinning the ALPHA/rare token to owner + a guaranteed buy-back floor is the
  mechanism that gives a paid small-supply mint real expected value (FOMO
  driver), separate from distribution — write it into the contract.
- **Emad's preferred paid-mint mechanic: AGENT-GATED mint.** `mint()` reverts
  unless the caller carries an agent-signed EIP-712 permit — the off-chain agent
  server is the ONLY mint key, so "you need an agent to mint" IS the hook and
  replaces hype. Full pattern (EIP-712 permit, agent gateway, eth-account
  gotchas: `encode_typed_data(full_message=...)`, `_supply` counter vs
  `totalSupply()`, `raw_transaction`, 1.5× gasPrice vs base-fee) in
  `references/agent-gated-mint.md`.
- **When Emad says "make it FOMO", build the pressure page — see
  `references/fomo-mint-page.md`** for the six-trigger stack (live mint feed,
  climbing price, draining supply, countdown, growing jackpot, sold-out reveal)
  and the ANTI-FAKE-MECHANISM rule (never advertise a jackpot/curve/alpha the
  contract doesn't implement — strip it to honest copy instead).
- **Sizing supply / free-wave / price to hit a revenue target — see
  `references/mint-pricing-ladder.md`.** Emad's shape: supply in the thousands
  (4444), a SMALL free wave (44, not 444), VERY cheap entry (half a penny),
  cents-scale climb to a few-dollars top. Key trap: a zero-base ladder averages
  at half the top and can't hit ≥1 ETH without a crazy price — start the paid
  ladder from a real base after the free wave.
- **Jackpot / prize-pool design and marketplace-terms risk — see
  `references/jackpot-mechanics-and-terms.md`.** RANDOM-winner jackpot = lottery
  → OpenSea ban risk; MINT-ORDER/deterministic = distribution → safe. Equal
  split-across-cohort is a trap (pennies per person + eats revenue). Winner-per-
  milestone weighted escalating pots give the real FOMO (up to ~500x) at a
  50%-of-mint-fees pool.
- **The final cycle-jackpot economy + local-EVM verification — see
  `references/cycle-jackpot-economy.md`.** Emad's locked shape (2026-08-20, supersedes
  the 8/19 design): 8,880 supply = ten 888-cycles, FLAT 0.0010 ETH, escalating
  40%→85% pot share (DATA), one random winner per cycle, cycle closes at 888 mints
  OR a 7-day timer (permissionless — the timer fallback stops the old
  advertise-a-jackpot-they-never-pay bug), draw separate + permissionless seeded by
  `blockhash(closeBlock+10)` with a re-anchor path on seed expiry, no per-wallet
  cap (a random draw makes farming unprofitable: net expectation (s−1)·k·P < 0 for
  all k). Proven 26/26 via `test/dryrun.py` — an eth-tester+py-evm harness (MUST
  include py-evm or estimateGas silently fails; raw Accounts need a manual
  signed_call helper; timeTravel for timers; struct getters flatten dynamic arrays).
- **Decaying-price (time-decay) mint — see `references/decaying-price-mint.md`.**
  Emad's non-jackpot mechanic of choice (2026-08-20): currentPrice = start −
  decay·blocks since last mint, clamped at floor, **reset on every mint** (the
  FOMO oscillation). Spec: start 0.1 / floor 0.0001 / decay 0.003 per block.
  Exact wei math puts delta 33 at 0.001 ETH and first reaches the 0.0001 floor
  at delta 34 (use ceiling division, never call it “33 blocks to floor”). The
  reference now covers the production-grade local ERC-721, malicious-receiver
  tests, localhost-only Hardhat deployment, and real headless-browser mint gate.
- **Whitelist/wallet-collection intake (IRC, one wallet per message):** when
  Emad pastes a stream of wallets one per message for a whitelist cap, write
  them to a running file (e.g. ~/Downloads/whitelist_wallets.txt) as they
  arrive instead of holding only in conversation — the file is the source of
  truth and survives session resets. Acknowledge each with its count
  ("N/ <addr> — logged"); batch-append 2–3 at once if messages arrive faster
  than replies. Dedupe check before finalizing (bot ops wallet 0x1111…1111 is
  a legit entry when he's whitelisting his own fleet). Non-EVM strings
  (base58 Solana) can appear mid-stream — flag and ask rather than silently
  appending. He'll state the target count up front ("30 mints") and may cut
  early; confirm before finalizing.
- **When Emad reverses a plan, the NEWEST spec supersedes prior handoffs.** Before
  building any economy/contract, check for a newer `docs/superpowers/specs/...`
  file and any "supersedes the ... handoff" note — the session's locked economics
  may have changed (e.g. the 8/20 spec reversed the 8/19 24-supply/no-jackpot
  design to 8,880/ten-cycles BEFORE build). Building the stale handoff's design is
  a wrong deliverable. Also remove obsolete paths (e.g. `agentMint(to)`) per the
  latest spec.
4. Deploy with a FRESH anonymous wallet (see the Anonymity bullet: that
   wallet MUST be funded from an unrelated source Emad supplies — an exchange
   withdrawal / fresh on-ramp — NEVER from the bot wallet or any owned wallet,
   or the funding tx permanently links the contract back to him). Set mint
   price ~$0.05–0.10 meme tier; keep deployer control of the fee splitter.
5. Distribution is the actual product: Twitter/X channel, meme fusion pull,
   momentum window. Emad's standing rule: never list a paid mint below
   break-even (mint price ÷ 0.89 to cover ~10% royalty + 1% fee), and coach
   him to hold runners instead of exiting at break-even in the volume window.

## Competitor launches ("devise a plan just like this")

When Emad drops a live collection/X account and wants the same play, run
forensics BEFORE planning: logged-out X timeline scrape → resolve the t.co
mint link → parse the OpenSea collection page's embedded GraphQL stats
(totalSupply, ownerCount, mint USD price, floor USD, all-time volume) →
honest gross/floor math. Cyclops Eyrix case (2026-08-15): $0.19 mint,
8,558 minted, $1.6K gross, floor $0.16 BELOW mint = the no-distribution
ceiling, not "easy money". Full workflow, the verified day-by-day launch
playbook (D-21 setup → kill gate → hype ladder → post-mint), and the
parody/likeness boundary: `references/competitor-launch-forensics.md`.
Contract compile-check without Foundry: `scripts/compile_check_sol.py`.
