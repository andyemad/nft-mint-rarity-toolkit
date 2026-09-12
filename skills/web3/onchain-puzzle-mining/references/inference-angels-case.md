# Worked example: Inference Angels (Aug 2026)

A "free mint, do the puzzle to claim" NFT on Robinhood Chain. Good template for the whole class.

## Deploy facts (from corpus/v3/deploy.json)

- Contract `0xD982d8F175BD50B976F4Ad90562c9e38200091f9`, chain id 4663
- RPC `https://rpc.mainnet.chain.robinhood.com`
- 7,777 angels; 333 genesis (reserved); 7,444 claimable
- 7.77% royalty (ERC-2981); two-step commit-reveal claim (commit, wait 60 blocks, reveal)
- Gas ~0.043 gwei → a mint costs ~0.000003–0.000011 ETH (effectively free)

## Nine puzzle kinds and how to solve each

| kind | approach |
|---|---|
| hunt | hash each word/pair/triple from the 6,000-word list, match the SHA-256 prefix |
| cipher | Vigenère; key length given; frequency analysis or brute-force the 26^keylen key space |
| hidden | word buried at fixed spacing; try spacings 2–12 × offsets, check against wordlist |
| construct | acrostic + word lengths + hash prefix; filter wordlist per slot, walk combos, test hash |
| lattice | grid of conditions, exactly one arrangement; brute force all permutations |
| rule | six worked examples → infer transformation (Atbash/ROT13/reverse/…) → apply to new word |
| ottendorf | book cipher: (word index, letter index) pairs into the wordlist |
| relic | read colours off a 32×32 pixel angel, row/col |
| chain | follow exact steps in order (watch NFC vs NFD normalisation) |

## Verified solved angel (#3444, band 35, 2 trials) — proves the pipeline

- Trial 1 (cipher, Vigenère, key length 4 → key "zptq") answer:
  "a stone opens the field beside the watchman and every harvest keeps that gate beside one flame and one veil carries a shepherd under a lamp and one harvest counts one watchman within that lamp"
- Trial 2 (construct, acrostic "tgpb", 7-7-7-7 letters, sha256 prefix 448d0e) answer:
  "thingum gewgawy pikeman biodyne"  (note: 9 candidate phrases matched the 448d0e prefix; only ONE matched the full on-chain seed — always verify against the seed, not just the puzzle's stated prefix)
- Final on-chain form matched the seeded `answerHash` for tokenId 3444. ✓

## The race is real

- Solved #3444 fully (hash verified) but it was claimed by someone else in the ~20 min before we could mint — collection went ~6,250 → ~6,824 mints in that window (heavy bot activity).
- Lesson: a verified solve is worthless unless the token is STILL unclaimed at mint time. Re-check `ownerOf` immediately before submitting.

## Compute reality (why software SHA is the wrong tool)

- 3-word hunt = 6,000³ = 2.16e11 SHA-256 hashes.
- Software SHA on M2: ~2.9 M/s single-thread (OpenSSL one-shot), CryptoKit ~1.8 M/s, ~6 M/s with 4 threads. → ~5–9 hours per angel.
- Metal GPU kernel (see scripts/metal_sha256_bruteforce.swift) is the fix; it verifies correct against "abc".
- Lower bands (1–2 trial, 1-word/2-word hunts) got swept first; what remains is 3–4 trial with 3-word hunts = the hard tier.
