---
name: onchain-puzzle-mining
description: Claim puzzle-gated NFTs; brute-force SHA-256 via Metal GPU.
---

# Onchain Puzzle Mining

Use when a user wants to "mine"/"claim" an NFT or token gated behind computational puzzles — SHA-256 prefix hunts, Vigenère ciphers, AES-sealed trial chains, lattice/construct/rule logic — or when you need fast SHA-256 brute force on Apple Silicon.

## The general shape

These mints (e.g. "Inference Angels" on Robinhood Chain) publish every puzzle up front in a repo, seal the answer hashes on-chain, and let anyone claim by solving. The mint is free plus gas; the puzzle IS the work.

1. Read the repo: the puzzle corpus, the claiming tool (`miner/mine.js`), the docs (`AGENTS.md`, `CLAIMING.md`, `PUZZLES.md`), and `deploy.json` (contract, chain id, RPC, royalty).
2. Understand the trial structure. A token holds 1–4 "trials", each a different puzzle kind (hunt / cipher / hidden / construct / lattice / rule / ottendorf / relic / chain). Only trial 1 is readable; every later trial is AES-256-CBC sealed by the SHA-256 of the previous answer.
3. Solve trial 1, unseal trial 2 with the recipe below, solve, repeat. Trials are strictly ordered — you cannot parallelise across trials.
4. Build the final answer and verify it against the published seeding hash BEFORE spending gas.
5. Claim with the repo's own tool (two-step commit-reveal) using a throwaway wallet with ~$1 of gas.

## Unseal recipe (verified)

Trial N+1 decrypts with `key = sha256(previous answer)` as hex bytes, AES-256-CBC, `iv = first 16 bytes of sha256("<tokenId>|iv|<N>")`, where N is the index of the trial being opened (1 for the second trial). Always confirm the decrypted text reads as English — a wrong key throws on padding ~255/256 times, but ~1/256 it returns nonsense with no error.

## Final answer (verified)

```
final   = sha256("<tokenId>|<ans1>|<ans2>|...")   # lowercase hex, single vertical bars, no spaces
onchain = keccak256(abi.encode(uint256 tokenId, bytes(final)))
```

Verify `onchain == seeded answerHash` (from the corpus seeding file and/or the contract's `answerHash(tokenId)`) before spending gas. The worked example in `references/inference-angels-case.md` shows the exact ethers calls.

## Race reality

These are public and first-come, first-served. Easy/low-band puzzles get swept by bots within hours of launch. Do NOT tell the user "this would mint right now" until you have (a) a verified answer AND (b) confirmed the token is still unclaimed (`ownerOf(tokenId)` reverts / returns zero). Check both, then mint immediately.

## Fast SHA-256 on Apple Silicon

Software SHA-256 is slow: OpenSSL, CommonCrypto (`CC_SHA256`), and CryptoKit all run ~2–3 M hashes/sec/thread on an M-series Mac — none of them expose the hardware crypto path through the simple APIs. A 3-word hunt over a 6,000-word list is 6,000³ ≈ 2.16e11 hashes → hours on CPU (even well-parallelised).

The fast path is a Metal GPU compute kernel. Write standard SHA-256 in Metal, verify it against the "abc" test vector (`ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`) BEFORE trusting it, then dispatch a thread per (i,j) pair looping the third word. `scripts/metal_sha256_bruteforce.swift` is a verified-correct kernel + host.

Key insight on hunt puzzles: the published prefix is derived from the answer's OWN hash, so the answer IS guaranteed to be in the search space. "Expected ~0 matches" reasoning is wrong — the author builds each puzzle from its answer, so brute force finds exactly the answer. The prefix length only excludes accidental collisions, not the answer.

## Keccak PoW mints (keccak256 preimage search)

Some mints (e.g. FAB 4200 on Robinhood Chain) gate the mint on `keccak256(chainid ‖ contract ‖ minter ‖ nonce)` clearing a leading-zero-bits floor instead of a fixed puzzle answer. Same discipline, different hash and a dynamic target: read the verified source for the exact packed preimage layout, query live difficulty (`floorBase`, per-wallet escalation) before promising anything, and remember the floor can race to its max within hours of a free mint going viral — always quote current-floor math to the user. Full case study with measured throughput numbers and a working Modal scale-out pattern: `references/fab4200-pow-mint-case.md`.

Compute ladder when CPU is too slow (user rejects multi-hour waits outright): local C/OpenMP → Metal GPU → **rented cloud vCPUs via Modal** (~$1–3 buys minutes-scale completion). Propose the rented-compute option first.

## Pitfalls

- Metal uses `[[thread_position_in_grid]]`, NOT `get_global_id()` (that's OpenCL).
- A thread-local array passed to an inline function needs the `thread` address space, not `device`.
- Never trust a hand-written hash kernel without hashing "abc" and comparing to the known digest.
- Never trust a hand-written hash kernel without hashing "abc" and comparing to the known digest. For keccak miners: verify every found nonce by re-hashing the contract-spec preimage in independent Python before broadcasting — this catches wrong RC tables, wrong byte offsets, and padding bugs that self-consistent code hides.
- When porting a working C hash core to a new file, COPY the constant tables verbatim — retyping 24 round constants from memory corrupted two of them and produced plausible-but-wrong hashes for an hour.
- abi.encodePacked(uint256 nonce) is 32 bytes big-endian; writing a uint64 nonce at the wrong offset (or twice) silently changes the preimage. Dump and diff the exact bytes your miner hashes against a Python-assembled preimage when in doubt.
- Modal: build with plain `-O3`, never `-march=native` (image-builder CPU ≠ runner CPU → SIGILL/rc=-4); always return rc+stdout+stderr from the remote function; `modal run` needs an explicit local_entrypoint or it executes nothing.
- Verify the final hash against the seeding hash BEFORE gas; a wrong answer wastes gas and claims nothing.
- Use a throwaway wallet with ~$1 of gas — never a main wallet key.
- Set `setbuf(stdout, nil)` in the Swift host or long GPU runs look like they hang (buffered stdout never flushes).
- On speculative mints the value thesis belongs to the USER. Give the factual picture (race risk, compute cost, liquidity, fees) and let them call it — never lead with "it'll moon" or "not worth it", and never swing between the two in one assessment.
- Long brute-force jobs: quote ODDS not guarantees ("one-hour run ≈ 50% at this difficulty"), and state the per-run cost + what happens on failure before launching. If a rented-compute workspace dies mid-run with a billing/disabled error, surface it immediately — it's a user action item, not a retry loop.
- When a user hands you a raw private key in chat, save it to `~/.hermes/secrets/` (chmod 600) IMMEDIATELY and derive the address back to them for confirmation — don't leave keys sitting in scrollback uncommitted.
- Modal free-tier billing: new workspaces get $30/mo credits but a usage budget that may default to ~$1; jobs then die with `ConflictError: workspace … has exceeded its spend limit`. The fix is USER-side: modal.com → Settings → Usage & Billing → add a payment method (Stripe), THEN raise the Workspace budget (max settable budget scales with prior successful charges — no card = tiny cap). Adding the card costs nothing while credits cover usage. Walk the user through this exact path; they won't find "spend limit" on their own.
- Modal reliability: rounds can die early with `RemoteError: Function call was cancelled by user or a failure` even when the account is healthy — always test with a trivial job (`--target-bits 16`) before diagnosing deeper, then just relaunch. If cancellations recur, wrap the farm in an auto-retry loop instead of hand-relaunching per round.

## See also

- `references/inference-angels-case.md` — worked example: contract/chain, the nine puzzle kinds, a fully-solved angel, and the live race/compute numbers.
- `references/fab4200-pow-mint-case.md` — keccak PoW mint case study (FAB 4200): contract mechanics, difficulty-retarget behavior, measured throughput ladder (Python→C→Metal→Modal), and a verified Modal scale-out pattern.
- `scripts/metal_sha256_bruteforce.swift` — verified-correct Metal SHA-256 brute-forcer (copy and modify the target prefix + wordlist).
- `templates/fab_keccak_pow_miner.c` — verified-correct OpenMP keccak-256 preimage miner (copy; edit contract/minter hex, chainid, mint selector).
