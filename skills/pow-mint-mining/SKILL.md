---
name: pow-mint-mining
description: Use when an NFT mint requires mining a keccak PoW nonce.
---

# PoW-Gated NFT Mint Mining

Some free mints are gated by proof-of-work: `mint(nonce)` succeeds only if `keccak256(<packed preimage>)` has ≥N leading zero bits. The work IS the cost. Class covers: reading the contract to learn the exact preimage, writing/verifying a fast miner, scaling out cheaply, and broadcasting.

## Workflow

1. **Read verified source first.** Pull from Blockscout/Etherscan `api?module=contract&action=getsourcecode&address=0x…`. Confirm: preimage layout (`abi.encodePacked(chainid, address(this), msg.sender, nonce)` is common), floor/difficulty mechanics, per-wallet escalation (e.g. +2 bits per prior mint from same wallet — multi-minting compounds cost), retarget behavior (difficulty can be pinned at max by bot farmers).
2. **Check live state** before committing: `floor()`, `currentFloor(wallet)`, supply, gas price. Compute expected work: 2^bits hashes; at measured MH/s → expected time. Present real numbers to the user before starting.
3. **Write a C miner** (template below). Single-thread first, then OpenMP.
4. **VERIFY AGAINST THE CONTRACT, NOT JUST YOURSELF (mandatory, two layers).**
   (a) Self-test: find a low-bit nonce (24 bits, seconds), recompute its hash independently in Python (`pycryptodome` keccak, digest_bits=256). MATCH proves the miner implements YOUR spec.
   (b) Contract-test (before ANY farm spend): pull real Fabbed/Mined events via eth_getLogs from wallets that actually minted, decode their (hash, nonce, minter), and recompute the hash with your preimage layout. MUST match — if it doesn't, either your preimage spec or your event decoding is wrong; decode every topic/data field before concluding the layout differs (in one session topic1 was tokenId, not minter — five "alternate layouts" were tried against the wrong field). Self-consistency proves nothing about contract-consistency.
5. **Scale out** on Modal (`modal run farm.py`) when local Mac is too slow (~2 MH/s/core Mac M2 CPU; ~18 MH/s per 16-vCPU Modal box; 40 bits ≈ 1.1T hashes ≈ coin-flip per hour-long 48-worker run). **Go straight to GPU when difficulty is pinned at max**: one Modal H100 runs the CUDA miner at ~7 GH/s → 40-bit expected hit in ~4 minutes (~$0.30–1), vs hours of coin-flip CPU rounds. A 32-bit benchmark completes in seconds — always benchmark at low bits first and derive GH/s empirically.
6. **Broadcast** value=0 EIP-1559 tx signed locally. Dry-run via `eth_estimateGas` first — a `BelowFloor` revert with `(got, need)` data confirms plumbing AND live difficulty in one call.

## Pitfalls

- **uint256 nonce byte placement**: in `encodePacked`, uint256 is 32 bytes big-endian; a uint64 nonce occupies offsets 96–103 of the preimage, bytes 72–95 stay ZERO. Writing the nonce at 88–95 (or twice) silently produces valid-looking but wrong hashes.
- **Never hand-retype constant tables** (Keccak RC round constants etc.). Copy from a source proven correct (test empty-string keccak = c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470). One shuffled RC entry yields plausible-but-wrong hashes that still pass leading-zero checks.
- **Modal `-march=native` SIGILL**: image builds on a different host than execution. Build with plain `-O3 -fopenmp`. Exit code -4 = SIGILL from this.
- **Apple clang has no OpenMP** (`omp.h` missing). Local testing single-thread; full OpenMP build runs on Linux (Modal).
- **`modal run` needs `@app.local_entrypoint()`** calling `.remote()` — defining only an `@app.function` creates objects but executes nothing (silently completes with no output).
- **Modal budgets**: error "Workspace … exceeded its spend limit" = Workspace budget cap (usage limit BEFORE credits apply), not credit exhaustion. Fix: modal.com → Settings → Usage & Billing → Workspace budget. Only workspace owner/admin sees the control.
- **Difficulty floors race upward** on popular free mints (26→40 within hours). Quote the user the CURRENT floor's time cost, never the launch floor.
- **"Unlucky streak" is a hypothesis, not an explanation.** If expected hits ≈ 1+ and you have zero after multiple rounds, stop and audit the spec against on-chain winners before spending another round. The user WILL call this out ("we should have minted by now") — take that challenge as a trigger for a real validation pass, not reassurance.
- Subprocess timeout inside a Modal function raises TimeoutExpired and kills the shard — return partial progress / checkpoint start_nonce so hunts can resume instead of losing an hour.
- Modal free-tier containers get **preempted mid-round**; the whole `modal run` dies with RemoteError "cancelled by user or a failure". Transient "workspace is disabled"/spend-limit errors also kill runs. Just relaunch; small test jobs confirm auth/budget state between failures.

### GPU (CUDA on Modal) pitfalls — two silent-wrongness bugs, both found only via on-chain audit

- **uint256 nonce endianness in the state word**: preimage bytes 96–103 hold the nonce BIG-endian, but keccak state words are read little-endian. XORing the raw uint64 nonce into `s[12]` silently hashes a different preimage. Fix: `s[12] ^= bswap64(nonce)`. In CUDA use an explicit shift/mask swap — `__builtin_bswap64` fails to compile in `__global__` functions and `__byte_perm(n,0,sel)` selector guesses are easy to get wrong.
- **Digest byte order vs clzll**: reading the final state word as LE puts digest byte 7 at the MSB, so `__clzll(s[0])` counts leading zeros of the WRONG END of the hash. Byte-swap `s[0]` before `__clzll`. Symptom of either bug: miner "finds" nonces whose independently-recomputed hash has ~0 matching bits.
- **Validation ladder that catches both**: (1) mirror the exact kernel logic in Python and diff against pycryptodome for a fixed nonce — this isolates keccakf correctness from placement bugs; (2) have the kernel print s[0]/s[1] for one known nonce (`dbg<<<1,1>>>`) and compare to the mirror; (3) only then trust FOUND nonces. A "verified" 24-bit self-test is meaningless if the verification recomputes with the same wrong layout.
- **CUDA toolkit on Modal images**: apt's `nvidia-cuda-toolkit` package doesn't exist on slim; install NVIDIA's repo keyring then `cuda-nvcc-12-4 cuda-cudart-dev-12-4`, compile with `/usr/local/cuda-12.4/bin/nvcc -O3`. Image build needs wget/gnupg/ca-certificates installed BEFORE the keyring step. Build the image once per code change — stale cached layers can serve an old binary; if results look like the previous bug, suspect cache and force distinct file content.

## Files

- `templates/pow_miner.c` — verified OpenMP keccak-256 nonce hunter (preimage layout as args; self-check procedure in header comment).
- `templates/fabminer_gpu.cu` — verified CUDA miner (~7 GH/s on Modal H100). Both GPU-port bugs fixed and commented inline; adapt contract/minter/chainid constants for other collections.
- `scripts/send_mint_tx.py` — EIP-1559 value=0 mint(nonce) broadcaster with dry-run estimate mode (needs `pip install eth-account coincurve pycryptodome`).
- `references/fab4200-session.md` — session log: CPU-farm dead end → on-chain audit → CUDA bugs → verified mints.
- `references/wallet-farm-lifecycle.md` — fresh-wallet factory, coincurve-only tx signing (eth_account/pydantic breakage workaround), RLP zero-encoding bug, nonce-race-free funding, sweep-back on mint-out, mint-out race timing.

## Related

- `mlops/metal-gpu-compute` — Metal GPU path for SHA-256 puzzles on-device (this skill: keccak on CPU/Modal; keccak-on-Metal untested).
