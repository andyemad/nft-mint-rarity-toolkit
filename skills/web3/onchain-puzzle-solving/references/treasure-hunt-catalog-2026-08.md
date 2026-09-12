# Treasure-hunt catalog repo: open-crypto-puzzles (worked 2026-08-17)

Session recap for the escrow-puzzle genre (see SKILL.md "Public treasure-hunt
catalog repos" section). All escrow checks 2026-08-17, BTC ~$63k, ETH ~$1,880.

## How the repo was found

- Tweet: https://x.com/0xflorent_/status/2089004740742914145 — Florent claims
  ~0.5 Ξ + 0.01 BTC solved, catalogues the rest. Repo link was NOT in the tweet
  body (tweet text ended with the media t.co link); found via
  `curl html.duckduckgo.com/html/?q=github+0xFlorent+crypto+puzzles` → result:
  `floflo777/open-crypto-puzzles` (the author's X handle is 0xFlorent_, GitHub
  account `0xFlorent` has 0 repos — the repo lives under `floflo777`).
- Other hits: a reply tweet "Link to the repository : https://t.co/hrnRa3CDar"
  (status 2089004880300015751) which also resolves to the same repo.
- Two small images in the tweet were wallet balance screenshots (8.61 ETH /
  1.25 BTC ≈ $79k) — NOT QR codes. Alt-text described the donut chart; vision
  read the small PNGs directly.

## Live escrow state (checked this session)

Swept since the repo's own 2026-08-16 check:
- **Aoi Quizchain2 Block 76 (0.077 BTC)** — README said funded-unspent, chain
  said `funded=7700000 spent=7700000`. Manifest drift; dead puzzle.

Still funded-unspent (the real targets):
- GSMG.io: `1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe` (1.2563451 BTC, partially-spent
  by author's own move txs) + `17ucy1K9ZUAaoY6JVtM932W9jUp5LXfyHa` (3.7505531
  BTC). Small-blob oracle = sha256(X.hexdigest()) as AES-256-CBC password.
- Guntis Vitolins: `0x9C2F44EFAd0c1E852a09dF9939e6DaF061140CaF` — 8.6125 ETH,
  author still drains it occasionally (nonce 7). 3 anchors: dutch@1, fog|cloud@5,
  parrot@12; floating fiber, fork; 7 unknowns.
- Ballet cards: two 1 BTC BIP38 cards (external-physical, not solvable remotely).
- Bitaps Shamir: 1 BTC (external-info).
- Aoi Real Big Block: `14zMkTgaVXJcxdh4JdWi29MLRR44iUSG9W` — 0.777 BTC.
- BLM collage: `1KfZGvwZxsvSmemoCmEV75uqcNzYBHjkHZ` — 0.201 BTC (insight/stego).
- Peter Todd bounties: 0.59 BTC total across 4 addresses (needs hash-collision
  research breakthrough).
- Mid tier: wealth-in-poetry 0.031 BTC, veteranhodl 0.0042, keysa 0.0037,
  keir-finlow-bates EN_medium+EN_veryhard+IT_veryhard 0.006, arweave #3/#10/#11/#12.

## What was actually run

- `tools/check_escrows.py` (full run, output to file; the shell `tail -60` hid
  the drift line — pipe to a file, not tail).
- `tools/oracle.py --selftest` on gsmg + aoi: both OK.
- GSMG: tested `matrixsumlist`, `ourfirsthintisyourlastcommand`, concat variants,
  `matrix sum list` — all NO MATCH (small-blob pipeline was never swept in
  isolation before; obvious page tokens are now logged negatives).
- Aoi RBB: pulled live Wattpad chapter (`wattpad.com/720888559-second` page HTML
  contains `"storyText":"..."` JSON; 36 <p> paragraphs after unescape) and ran
  25 serializations (separators x rule-on/off x subsets) — 0 hits. Repo ledger
  had assumed 17 candidate paragraphs.
- Guntis: BIP39 word audit of the 5 planted sentences: V1 {expect easy there
  will fog lake}, V2 {you more parrot can sing song then goat}, A1 {round dutch
  cattle forest wood}, A2 {only because there fiber}, A3 {like rib roast dinner
  fresh}. Connectors untested per leads.md (their P2 estimate 1.36e10 derivations
  ≈ 3.8h on one GPU).
- YouTube scan of the 3 Guntis videos: raw page HTML contains 500+ BIP39 words
  from the UI shell — noise; only keywords/description meta are author surfaces.
- BLM: downscaled the 1600x1200 collage for vision — layout mapped (runes,
  clock, microtext) but no key reading; insight-type puzzle.

## Commands worth keeping

```bash
# venv always
python3 -m venv .venv && .venv/bin/pip install -r tools/requirements.txt mnemonic
# escrow truth (write to file, don't tail)
.venv/bin/python tools/check_escrows.py > /tmp/escrow.txt
# single candidates or stdin batch
.venv/bin/python tools/oracle.py "candidate text"
printf 'a\nb\nc\n' | .venv/bin/python tools/oracle.py --stdin
```

## Running a rented-GPU sweep (Modal bootstrap)

Local CPU derived BIP39→Ethereum at only ~660 deriv/sec — a 1.36e10 sweep is
~6,000 CPU-hours, so a GPU is mandatory. Modal (`~/.hermes/hermes-agent/venv/bin/modal`)
is the installed option but is NOT authenticated by default:

1. Auth is an interactive browser flow the USER must complete — agents cannot
   do it for them. Run `modal token new` in the **background** (it blocks
   waiting on the OAuth callback), then poll the process for a
   `https://modal.com/token-flow/<id>` URL and hand it to the user.
   `modal token new` foreground just times out.
2. `modal profile current` prints a name even when unauthenticated; the real
   auth probe is `modal run <tmpfile>.py` — fails with "Token missing" when
   not authenticated.
3. hashcat (brew-installable, uses the M2 via OpenCL) is free but has no
   BIP39→Ethereum mode — see SKILL.md brute-force section. Don't assume a stock
   tool can run the transform before promising a GPU run.
4. Always validate the derivation locally (oracle selftest + tiny slice) BEFORE
   paying for GPU time so the rented run isn't broken.

## Honest verdicts

These are years-old puzzles with millions-to-billions of candidates already
tested by the repo author. The remaining edges are (a) insight leads that make
new pools explicit, (b) bounded GPU sweeps on the new pools (Guntis connectors
≈ 3.8h one GPU for 8.6 ETH; Keysa 2-per-row ≈ 76min for 0.0037 BTC), and (c)
the GSMG small-blob pipeline which has never been swept in isolation at scale.
Never promise a solve; report the verified negatives and the priced next sweep.