# Proof-of-work minters

Hunt the nonce that satisfies a mint contract's proof-of-work check, then
broadcast `mint(nonce)`. CPU (OpenMP), CUDA and Metal implementations.

A PoW mint is a **lottery ticket with an expected-negative cost**: at high
difficulty you are racing everyone else for a bounded reward, and you pay gas and
hash time whether you win or not. The code here is fast and correct; it does not
make the economics positive.

## Schemes implemented

**FAB4200-style** (`pow_miner.c`, `fabminer_gpu.cu`) — Robinhood Chain 4663,
contract `0xEF08089e4E082071AA39Ce99C460c0250744d758`:

```
preimage  = chainid_u32_be(32) || contract(20) || minter(20) || nonce_u256_be(32)   // 104 bytes
accept if keccak256(preimage) has >= target leading zero bits
```

**Hashcats-style** (`hcminer.c`, `hcminer.cu`) — sequential work chain:

```
preimage  = miner(20) || nonce_u256_be(32) || prev(32) || anchor(32)                // 116 bytes = ONE keccak block
accept if keccak256(preimage) < target
prev      = the work value of the previous token; the chain is sequential
```

Both are one Keccak-f permutation on a single 136-byte block, so the inner loops
are hand-unrolled and keep the state pre-absorbed — that is where the throughput
comes from.

**`metal_sha256_bruteforce.swift`** — a Metal SHA-256 brute-forcer, correct and
verified (hashes `"abc"` to `ba7816bf…`). Copy it and change the target prefixes
and wordlist path.

## Build

Linux / any machine with a real OpenMP toolchain:

```bash
gcc -O3 -fopenmp -o powminer pow_miner.c
gcc -O3 -fopenmp -o fabminer fab_keccak_pow_miner.c
gcc -O3 -fopenmp -o hcminer hcminer.c
nvcc -O3 -o hcminer_cuda hcminer.cu
```

**Do not use `-march=native` for a cloud build** — the build host is not the
execution host, and the binary dies with SIGILL (`rc=-4`). Verified the hard way.

**macOS:** stock clang has no OpenMP, so `-fopenmp` fails with
`unsupported option '-fopenmp'`. Either install it (`brew install libomp` and use
`-Xpreprocessor -fopenmp -lomp`), or build a single-threaded binary with the
4-line stub used for self-testing:

```bash
mkdir -p shim && cat > shim/omp.h <<'EOF'
#ifndef OMP_H
#define OMP_H
int omp_get_thread_num(void); int omp_get_num_threads(void);
int omp_get_max_threads(void); void omp_set_num_threads(int);
#endif
EOF
cat > shim/omp_stub.c <<'EOF'
int omp_get_thread_num(void){return 0;} int omp_get_num_threads(void){return 1;}
int omp_get_max_threads(void){return 1;} void omp_set_num_threads(int n){(void)n;}
EOF
clang -O2 -Wno-unknown-pragmas -Ishim -o powminer pow_miner.c shim/omp_stub.c
```

## Run and self-check

```bash
# FAB4200-style: start at 24 bits; it should find a nonce in seconds
./powminer 0x<minter_address> 0 24 8

# Hashcats: 200k nonces compared against the in-file reference Keccak
./hcminer selfcheck 0x<miner> 0x<prev> 0x<anchor>

# Hashcats: mine for real (target from the contract)
./hcminer mine 0x<miner> 0x<prev> 0x<anchor> 0x<target> 8 600
```

`powminer` prints `FOUND nonce=N bits=B hash=0x…` plus the ready calldata
`0xa0712d68…` (`mint(uint256)`). Broadcast it with
`../mint/send_mint_tx.py <keyfile> <nonce>` — dry-run first.

## Verification status

- `pow_miner.c` built single-threaded and run at 24 bits; the reported hash was
  reproduced byte-for-byte by an independent `pycryptodome` keccak256 of the same
  104-byte preimage, and the emitted calldata decoded to `mint(nonce)`.
- `hcminer.c` `selfcheck` compares its fast path against the in-file reference
  over 200,000 random nonces: **0 mismatches**. Its 116-byte preimage was also
  cross-checked against `pycryptodome` via the `verify` subcommand with a
  Python-computed work value: **0 mismatches**.
- The CUDA paths were validated the same way on an H100; the two classic GPU
  port bugs (nonce endianness when XORed into the state word, and the
  leading-zero test on a byte-swapped digest word) are fixed in these sources.

## Pitfalls

- **Self-check before every long run.** Run at 24 bits first. A miner that is
  subtly wrong will happily burn hours.
- **Difficulty retargets.** FAB4200's floor moved 26 → 40 (max) within a day of
  opening as bot farms arrived; `~1.1e12` hashes per solve at 40 bits.
- **Difficulty is per-sender on some contracts.** Read `targetFor(msg.sender)` /
  `currentTarget()` rather than assuming a constant.
- **Confirm plumbing without spending.** `eth_estimateGas` on the mint call with
  a dummy nonce reverts with the contract's own difficulty error — for FAB4200
  `BelowFloor(uint8,uint8)`, selector `0xfcf93064`, with got/need in the data.
  That one call proves calldata, from-address, gas path and live difficulty.
- **Never leave a broadcast-capable script in a loop unattended** — the next
  round starts the moment the last one resolves.
