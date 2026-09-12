# Worked example: Inference Angels (Robinhood Chain puzzle mint)

A free-mint NFT where each of 7,777 angels is locked behind 1–4 "trials"
(computational puzzles). Solved fully offline on 2026-08-13. This is the recipe.

## Facts

- Site: https://inferenceangels.com  ·  repo: https://github.com/jacklarmer/inference-angels
- Contract `0xD982d8F175BD50B976F4Ad90562c9e38200091f9`, chain id 4663,
  RPC `https://rpc.mainnet.chain.robinhood.com` (all in `corpus/v3/deploy.json`).
- `fromBlock` 35606631. Genesis: 333 held back. Claim cost ≈ 0.000006 ETH (gasPrice ~0.043 gwei).

## Puzzle structure (per token, in `corpus/v3/public/band-NN.json`)

```json
{ "tokenId": 3444, "band": 35, "trials": [
    { "n": 1, "kind": "cipher", "statement": "..." },
    { "n": 2, "kind": "construct", "sealed": "<b64>", "hint": "..." }
], "finalStep": "..." }
```

- Only trial 1 is readable. Trial `n+1` is AES-256-CBC sealed; key = `sha256(prevAnswer)`,
  iv = first 16 bytes of `sha256("<tokenId>|iv|<trialIndex>")`, trialIndex counting from 1 for trial 2.
- Final answer = `sha256("<tokenId>|<a1>|<a2>|...")` (hex).
- On-chain form = `keccak256(abi.encode(["uint256","bytes"], [tokenId, utf8(finalSha)]))`.
  Verified format by solving the trivial single-trial angel #1 (hunt → "mortiser") and matching its seed hash.

## The two pitfalls that cost time

1. **Construct puzzles yield multiple prefix matches.** Angel #3444's trial 2 asked for a
   4-word phrase (acrostic "tgpb", 7-7-7-7, sha256 prefix `448d0e`). Brute-forcing
   96×63×138×126 combos found **9** phrases matching the prefix; only
   `thingum gewgawy pikeman biodyne` passed the full final-answer hash.

2. **A `frontier()` view is NOT the claimable frontier.** It read 7777 (max) while bands
   32+ still had unclaimed angels. The claimable set = all ids minus `Solved` event ids
   minus the genesis set (genesis = every `step`-th id in each choir, from app.js).

## Claimable-set derivation (ethers, works)

```js
const ia = new Contract(addr, ['event Solved(uint256 indexed tokenId, address indexed solver, uint256 band)'], provider);
const logs = await ia.queryFilter('Solved', deploy.fromBlock, await provider.getBlockNumber());
const solved = new Set(logs.map(l => Number(l.args.tokenId)));
// subtract genesis (per-choir step/count), then any id in 1..7777 not in solved and not genesis is claimable
```

## Angel #3444 (solved; may be claimed by now — use as a format example only)

- Trial 1 Vigenère, key `zptq` (recovered from repeated `tdc`→`and`, `dgu`→`one`):
  "a stone opens the field beside the watchman and every harvest keeps that gate beside one
  flame and one veil carries a shepherd under a lamp and one harvest counts one watchman within that lamp"
- Trial 2 construct answer: `thingum gewgawy pikeman biodyne`
- Final hash verified MATCH against seed `0xa6e1a2...`.

## Gate

Claim = `node miner/mine.js solve 3444` with `RPC_URL` + `PRIVATE_KEY` (throwaway wallet, a
few cents of Robinhood Chain gas). Two-step commit→reveal (60-block wait) handled by the repo tool.
Do not reimplement the commit/reveal — use the shipped `mine.js` as-is.
