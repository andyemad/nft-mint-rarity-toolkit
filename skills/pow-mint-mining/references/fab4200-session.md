# FAB 4200 Session Notes (2026-08-21/22) — worked example, RESOLVED

Live PoW mint on Robinhood Chain (4663). Contract 0xEF08…d758, verified source via
Blockscout `api?module=contract&action=getsourcecode`. **Minted successfully for both
wallets; both txs status 0x1.**

## Contract facts (read from source, don't trust the site)
- Preimage CONFIRMED against on-chain winners: `keccak256(abi.encodePacked(block.chainid,
  address(this), msg.sender, nonce))` = chainid(4663, u32 BE at bytes 28–31 of a zeroed
  32B word) ‖ contract_20 ‖ minter_20 ‖ nonce_u256_be — 104 bytes total.
- Floor: starts 26 bits, retargets toward ~90s/mint cadence, max 40. Per-wallet
  escalation: +2 bits × prior mints from same wallet.
- Nonpayable, receive()/fallback revert, no owner functions at all.
- calldata for mint(uint256): selector `0xa0712d68` + 32-byte BE nonce.
- floorBase() selector 0xc7a44a6e (returns bits, e.g. 0x28=40).
- minted() selector 0x4f02c420; OPEN_AT() 0xd8f93498.

## The audit that cracked it (2026-08-22 ~02:30 EDT)
After ~7e12 hashes with no hit, user challenged ("1500 minted since you tried").
Audit sequence:
1. eth_getLogs for Fabbed events (topic0
   0x2e670890008694ffde9555696023f6efc80d7acdcca9a4dcf6b3724df633204d) over recent
   blocks — others WERE minting at 40 bits, so difficulty wasn't the blocker.
2. Event layout: topic1 = tokenId (NOT minter!), topic2 = msg.sender. Data =
   `[workHash(32)][floorAtMint(uint8 in 32B)][nonce(u256 BE)]`.
3. Recomputed a real winner's workHash from its (minter=topic2, nonce) → **byte-exact
   MATCH**. Preimage spec was right all along; the CPU farm was just outgunned and
   unlucky (each round ≈ coin flip at 40 bits).

Earlier audit attempt failed because it used topic1 as the minter (wrong field) and
tried 5 alternate layouts — the spec was never wrong, only the event decoding was.
Lesson: when validating against events, decode EVERY topic/data field and identify
which is which before concluding the preimage is different.

## GPU port: two silent bugs (both fixed & verified)
Built CUDA miner for Modal H100 after the audit showed hardware was the bottleneck.
Validation ladder that caught them: mirror kernel logic in Python → diff vs
pycryptodome → single-thread kernel dump (`dbg<<<1,1>>>`) printing s[0]/s[1] → diff
vs mirror.

- **Bug 1 — nonce endianness**: preimage bytes 96–103 hold the nonce BIG-endian, but
  state words are LE-read; XORing raw uint64 into s[12] hashes the wrong preimage.
  Fix: bswap before XOR (`__builtin_bswap64` doesn't compile in `__global__`; use
  shift/mask swap; `__byte_perm(n,0,sel)` selector guessing also failed once).
- **Bug 2 — digest byte order**: reading final word as LE puts digest byte 7 at the
  MSB, so `__clzll(s[0])` counts leading zeros of the WRONG END. Byte-swap s[0]
  before clzll. Verified: hash starting c798… reads LE as 0000004bd12c98c7 (25 fake
  "leading zeros" from the tail).
- Symptom of either bug: FOUND nonces whose independently recomputed hash has ~0
  matching bits. A 24-bit self-test is meaningless if verification recomputes with
  the same wrong layout — verify against pycryptodome AND an on-chain winner.

## CUDA toolkit on Modal images
apt's `nvidia-cuda-toolkit` has no candidate on debian_slim. Install wget/gnupg/
ca-certificates first, add NVIDIA's repo keyring
(developer.download.nvidia.com/.../cuda-keyring_1.1-1_all.deb), then
`cuda-nvcc-12-4 cuda-cudart-dev-12-4`, compile `/usr/local/cuda-12.4/bin/nvcc -O3`.
Image layer cache can serve stale binaries after code edits — if results look like
the previous bug, suspect cache.

## Throughput measured
- Mac M2 CPU C -O3 single core: ~2 MH/s. Modal 16-vCPU box: ~18 MH/s.
- CPU farm: 24 shards × 8 vCPU ≈ 430 MH/s ≈ coin-flip per 57-min round (~$2).
- Modal H100 CUDA: ~7 GH/s → 40-bit expected hit ≈ 4 min (~$0.5). 32-bit benchmark
  found in 8.6s. When difficulty is pinned at max, GPU isn't an optimization, it's
  the difference between hours of coin flips and minutes.

## Modal specifics learned
- "Workspace … exceeded its spend limit" = Workspace budget cap (pre-credit usage
  limit), NOT credit exhaustion. Fix: modal.com → Settings → Usage & Billing →
  Workspace budget. Free plan caps the max settable budget by prior successful
  charges — adding a payment method raises it. Owner/admin only.
- Free-tier preemption kills whole runs ("cancelled by user or a failure"); expect
  round loss, relaunch. Small test jobs confirm auth/budget between failures.
- Spend observed: ~$1 per ~1.5h of 48-worker CPU farming; GPU rounds pennies.

## Outcome (final)
Both wallets minted, receipts status 0x1:
- bot wallet 0x1111…1111: nonce 21214117497163 (44-bit hash), tx 0xaa7454ee…4032e
- wallet2 0x2222•2222: nonce 13086727620657 (42-bit hash), tx 0x5667905b…7b4cd
Verified miner template: templates/fabminer_gpu.cu. Broadcaster: scripts/send_mint_tx.py.
