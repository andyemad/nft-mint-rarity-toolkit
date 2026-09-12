---
name: onchain-puzzle-solving
description: Solve computational puzzles gating on-chain mints/claims.
---

# On-Chain Puzzle Solving

## When to use

When a user wants to claim/mint an NFT or token gated behind computational puzzles ("solve the puzzle, claim the angel"), or asks "how do I mine this" for a puzzle-based project. Also covers CTF-style crypto challenges embedded in on-chain contracts.

## Genre overview

A recurring crypto genre: free-mint collections where each item is locked behind 1–4 "trials" (puzzles), the answer is checked on-chain by hash, and claiming uses a commit-reveal so nobody can front-run the answer. The puzzles are pure computation — Vigenère, SHA-256 preimage hunts, constraint grids, book ciphers — designed so any model/computer can solve, and the contract stores only hashes (not the answers).

Key mental model: the author builds each puzzle FROM its answer, so the answer is guaranteed to exist in the search space — the published hash prefix always matches the seeded answer. Do NOT conclude a hash-prefix puzzle is "unsolvable" because the prefix looks too long; the prefix length only makes collisions astronomically unlikely, it does not remove the answer.

## Recon first

1. Read the whitepaper + README + `AGENTS.md` (an AGENTS.md usually contains the exact solve recipe and unseal code).
2. Clone the repo. Look for: `corpus/` (puzzle files), a `wordlist`, `seeding/` (answer hashes), `miner/` or `scripts/` (the claim tool), `deploy.json` (chain id, RPC, contract address).
3. Read the claim tool source — it shows the exact on-chain hash encoding and mint flow. Trust it over your own reimplementation.

## Puzzle types and recipes

- **hunt** — "the word/phrase from the wordlist whose SHA-256 starts with `<hex>`." Brute-force: hash every word (1-word = 6000 tries), every pair (~36M), every triple (~2.16e11). Words space-separated, may repeat. See Brute-force engineering.
- **cipher** — Vigenère, key length given. Spaces preserved and NOT counted in key stepping. Attack: strip spaces, then (a) brute-force the key (26^keylen, score the plaintext against the wordlist + common words), or (b) known-plaintext — find a repeated ciphertext word (e.g. "tdc" appearing twice is likely "the"/"and"), derive key letters from the offsets.
- **construct** — "build a phrase matching an acrostic + word lengths + a hash prefix." Filter the wordlist by first-letter and length per slot, then nested-loop and check the hash. Space is often ~1e8, brute-forceable in about a minute.
- **hidden** — a word buried at fixed spacing. Try spacings 2–12 and every offset, check against the wordlist, confirm with the hash.
- **lattice** — a grid of conditions with exactly one arrangement. Generate all permutations, filter.
- **ottendorf** — book cipher over the published word list. First number = word index (1-based), second = letter index (1-based).
- **relic** — read colours off a named piece of art (a 32×32 pixel grid). Row/col 0-based; expand rectangle runs.
- **rule** — six worked examples; find the transformation and apply it. Try Atbash, ROT13, reverse, keep-every-other, Base64, keep-letters.
- **chain** — follow exact steps in order; watch Unicode NFC vs NFD normalization and multi-part joins (single vertical bar).

## Sealed trials (AES-256-CBC)

Only trial 1 is readable; each later trial is sealed and the key is the answer to the trial before it.

```
key   = SHA256(previousAnswer)                      # 32 bytes
iv    = SHA256(`${tokenId}|iv|${trialIndex}`)[0:16] # trialIndex counts from 1 for the 2nd trial
plain = AES-256-CBC-decrypt(base64(sealed), key, iv)
```

Pitfall: a wrong key throws a padding error ~255/256 times, but ~1/256 it returns gibberish with no error. Always confirm the output reads as English before trusting it.

## Final answer + on-chain hash

Final answer = `SHA256(hex) of "${tokenId}|${trial1}|${trial2}|..."` (join with a single `|`, no spaces).

The on-chain `answerHash(tokenId)` = `keccak256(abi.encode(['uint256','bytes'], [tokenId, utf8(finalShaHex)]))`.

Verify BOTH before spending gas: your computed keccak vs the seeding file's `answerHash`, AND vs the live contract `answerHash(tokenId)`. (This exact encoding was verified against a known-solved angel.)

## Commit-reveal mint flow

```
commitment = keccak256(abi.encode(['address','uint256','bytes32','bytes'], [wallet, tokenId, salt, answerBytes]))
1. commit(commitment)                  -> wait commitMinBlocks (~60)
2. mint(tokenId, answerBytes, salt)
```

The two-step seal stops answer front-running. Use the project's own claim tool as-is; don't reimplement the waiting/reveal logic (it often carries launch-day race fixes).

## Brute-force engineering (macOS / Apple Silicon)

- Software SHA-256 on an M2 is ~3M hashes/sec/core (OpenSSL one-shot or CommonCrypto). CryptoKit is slower (~1.8M/s). This is the realistic floor unless you wire hardware SHA/GPU.
- Apple clang has NO `-fopenmp`. Use pthreads. Verify real parallelism with `ps -o %cpu` — competing processes and per-hash atomic counters both collapse throughput (8 threads → ~3.8M/s instead of ~20M/s). Use per-thread local counters, not an atomic per hash.
- CommonCrypto needs no linking: `#include <CommonCrypto/CommonDigest.h>`, call `CC_SHA256`. Homebrew OpenSSL: `-I/opt/homebrew/opt/openssl@3/include -L/opt/homebrew/opt/openssl@3/lib -lcrypto`.
- A 3-word hunt over a 6000-word list = 2.16e11 hashes ≈ 5 hours at ~6M/s (4 threads); the match lands at ~50% of the space on average. Report this honestly — it is real compute, not seconds.
- To go from hours to minutes: performance cores only, then ARM SHA256 crypto intrinsics or a Metal/GPU kernel.
- **hashcat has NO mode for BIP39-mnemonic → address.** Mode 29600 is the Ethereum JSON-wallet PBKDF2-HMAC-SHA256 format, NOT the BIP39-mnemonic derivation. BIP39 → MetaMask/BIP44 address is PBKDF2-HMAC-SHA512 (2048 rounds) + secp256k1 pubkey + keccak — the chain libraries (bip_utils etc.) do it at only ~660 deriv/sec single-thread, so a 1e10-candidate sweep is ~6,000 CPU-hours. There is no stock cracking tool that short-circuits it; a serious sweep needs a custom Metal/OpenCL kernel. Before promising a "GPU sweep," check whether the tool you intend actually computes this derivation, or you'll rent a GPU and burn time on a tool that can't run the transform.
- **Rented-GPU sweeps are cheap to price but low-EV after prior exhaustion.** A catalog may rank "extend the word pool with connecting words" as its #1 lead (15-20 new words → ~1.4e10 derivs → ~3.8 GPU-h ≈ $2) even after 16.75B prior negatives. State the prior-exhaustion count and N/D honestly, price the run, and let the user decide — do not oversell a bounded 1e10 sweep as likely-to-hit.

## Race, honesty, and the user

- Public puzzle mints are first-come-first-served; bots sweep low-difficulty items within hours of launch. Re-check `ownerOf(tokenId)` (or the Solved event log) immediately before minting — a solved-but-claimed puzzle is worthless.
- Do NOT tell the user "this would mint right now" without flagging the race. State exactly what is verified (e.g. the hash matched the chain) AND the timing risk.
- Do NOT editorialize "not worth it" / "no market" on a speculative play the user is excited about. The value thesis is the user's call. Execute, report concrete numbers and risks, let them decide.

## Verification checklist

- [ ] Read the project's AGENTS.md/whitepaper + claim tool source.
- [ ] Final-answer hash matches both the seeding file and the live `answerHash(tokenId)`.
- [ ] `ownerOf(tokenId)` reverts (unclaimed) right before mint.
- [ ] Wallet has gas on the correct chain before `solve`.

## Public treasure-hunt catalog repos (escrow puzzles, not mints)

A related but distinct genre: an author locks BTC/ETH/AR at a published escrow
address and publishes a riddle; solvers derive the private key/seed and sweep
it. Reference catalog: `floflo777/open-crypto-puzzles` (~33 funded puzzles,
~$644k live as of Aug 2026). Layout: `<slug>/README.md` (full story),
`<slug>/puzzle.json` (manifest), `<slug>/analysis/tested.md` (negatives ledger),
`<slug>/analysis/leads.md` (ranked open leads), `<slug>/tools/oracle.py`
(certified candidate checker); the root `AGENTS.md` is the exact agent recipe.

Workflow:
1. Clone; `python3 -m venv .venv` + `.venv/bin/pip install -r tools/requirements.txt`
   (+ `mnemonic`; system pip is often PEP-668-blocked, always use the venv).
2. Read that folder's README in full, then tested.md and leads.md.
3. Run `tools/check_escrows.py` and trust the CHAIN, not the manifest: manifests
   go stale fast — a Quizchain Block 76 escrow listed "funded-unspent" in the
   README had been swept between the repo's own check and the session. A swept
   escrow = dead puzzle; drop it and note the drift.
4. Run `tools/oracle.py --selftest` before any search. Some oracles ship NO
   source text (copyright), certify the transform against the author's own
   published vector, and expect YOU to supply candidate text.
5. Do NOT repeat any `analysis/tested.md` row — read cumulative candidate counts
   first (16.75B derivations on one puzzle, 272M on another). Once a pool is
   exhausted at that scale, the value is in the ranked LEADS (insight), not more
   permutations.
6. A negative needs a witness (known-good input re-found through the same code),
   else label it "uncertified". Before any loop write N, measured rate D, t =
   N/D; if t > 2h, shrink N with a constraint instead of renting more compute.
7. Never broadcast a transaction or post key material; hand the private key to
   the human, who sweeps and announces after.

Techniques that paid off on this genre:
- **BIP39 word audit of clue sentences**: `from mnemonic import Mnemonic; wset =
  set(Mnemonic("english").wordlist)`, tokenize the planted sentences, split into
  in-list vs out-of-list words. Separates real candidates from prose filler,
  validates whether a hinted word (e.g. "fiber") is actually a list word, and
  reveals which untested pools exist (short connecting words — there/will/only/
  because — are a commonly untested lead).
- **Wattpad chapter extraction (book-cipher sources)**: story pages embed the
  chapter as JSON string `"storyText":"..."` in the page HTML (escaped
  `<p data-p-id="...">` blocks). Extract with
  `re.search(r'"storyText"\s*:\s*("(?:[^"\\]|\\.)*")', html)` → `json.loads` →
  `html.unescape` → split on `<p>` → paragraph list. Verify the live paragraph
  count against what the repo ledger assumed — they can differ (36 vs 17 in one
  case) and a fresh serialization sweep is cheap.
- **YouTube metadata scanning has a noise floor**: raw watch-page HTML contains
  500+ incidental BIP39 words from YouTube's UI shell — never scan raw page HTML
  for candidate words. Only author-controlled surfaces count: `<meta
  name="keywords">`, `<meta name="description">`, title.
- **Case-flip serialization attacks**: when the transform is certified (e.g.
  Aoi Quizchain: MD5 → BIP39 → BIP44, with a paragraph first/last-letter
  case-flip rule confirmed on a solved sibling), enumerate paragraph subsets ×
  separators (\n, \n\n, \r\n\r\n, + trailing NL) × rule on/off through the
  oracle. Cheap even after millions-candidate repo sweeps, because your
  paragraph segmentation of the live source may differ.

## Supporting material

- `references/inference-angels-2026-08.md` — worked example: Inference Angels (Robinhood Chain), solved angel + full pipeline transcript.
- `references/treasure-hunt-catalog-2026-08.md` — worked example: open-crypto-puzzles repo (tweet → repo discovery, escrow drift finding, per-target status with live escrows, oracle commands).
