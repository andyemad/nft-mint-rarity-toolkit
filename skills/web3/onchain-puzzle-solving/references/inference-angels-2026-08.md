# Inference Angels — worked example (2026-08)

A complete solve of one "Inference Angels" angel, demonstrating the full pipeline end to end.

## Project facts

- 7,777 pixel-art angels on Robinhood Chain (chain id 4663). Free mint, ~7.77% resale royalty.
- Contract `0xD982d8F175BD50B976F4Ad90562c9e38200091f9`; RPC `https://rpc.mainnet.chain.robinhood.com`.
- Repo `github.com/jacklarmer/inference-angels` (MIT). Corpus: `corpus/v3/public/band-NN.json` (101 angels per band, 77 bands), `wordlist.json` (6000 words), `seeding/band-NN-hashes.json` (the answer hashes).
- Claim tool `miner/mine.js` (ethers v6): `show` / `check --answers file` / `solve` / `status`. `PRIVATE_KEY` + `RPC_URL` env. `deploy.json` holds chain/contract/`fromBlock`.
- Difficulty tiers: 1 trial < band 20, 2 trials to 40, 3 to 60, 4 above. Hunt prefix length grows with rarity (4 hex low → 14 hex high).

## Solved angel #3444 (band 35, 2 trials)

- **Trial 1 (cipher)** — Vigenère, key length 4. Ciphertext had "tdc" (×2) and "dgu" (×3). Known-plaintext: `tdc→and`, `dgu→one` gave key `zptq`, plaintext = "a stone opens the field beside the watchman and every harvest keeps that gate beside one flame and one veil carries a shepherd under a lamp and one harvest counts one watchman within that lamp".
- **Trial 2 (construct)** — acrostic "tgpb", lengths 7,7,7,7 (28 letters), SHA-256 prefix `448d0e`. Filtered wordlist by first-letter+length, nested-loop over ~105M combos, found 9 hash-prefix matches but only ONE whose final-answer keccak matched the seed: "thingum gewgawy pikeman biodyne".
- Final answer `sha256("3444|<t1>|<t2>")` → keccak `keccak256(abi.encode(['uint256','bytes'],[3444, utf8(final)]))` matched the seeding file exactly.

**Outcome:** angel #3444 was claimed by a bot in the ~20 min before the mint could be submitted — the collection went ~6,250 → ~6,824 mints in that window. Lesson reinforced: verify `ownerOf` immediately before minting; a solved-but-claimed puzzle is worthless.

## Live-state readout (useful queries)

- `mine.js status` → `totalMinted()`, `frontier()`.
- Find unclaimed: read `Solved` events from `deploy.fromBlock` to latest, subtract those ids + the 333 genesis ids from 1..7777. Genesis = every `step`-th id per choir (from the site's `app.js` GENESIS table).
- Verify a specific id: `ownerOf(id)` reverts → unclaimed.
- `answerHash(id)` on-chain should equal the seeding file's `answerHash` (it does — both are `keccak256` of the same encoding).

## Compute reality (this hardware)

- 3-word hunts = 6000³ = 2.16e11 SHA-256. At ~6.4M/s (4 pthreads, software SHA) ≈ 5 hours, match at ~50% on average.
- The easy bands (<55) were swept within hours; what remained were band 55+ 3-trial angels, all gated by a 3-word hunt.
