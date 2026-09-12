# FAB 4200 — keccak PoW mint case study (2026-08-21)

Site: https://fab4200.vercel.app · Contract 0xEF08089e4E082071AA39Ce99C460c0250744d758 · Robinhood Chain (chainId 4663) · RPC https://rpc.mainnet.chain.robinhood.com

## Mechanics (from verified Blockscout source)

- 4,200 supply ERC-721, fully on-chain SVG via separate ownerless renderer contract.
- `mint(uint256 nonce)` nonpayable, `receive()/fallback()` revert. Value always 0, zero approvals.
- `workHash = keccak256(chainid ‖ address(this) ‖ msg.sender ‖ nonce)` — all fields abi.encodePacked: chainid is **32 bytes** big-endian, addresses 20 bytes, nonce is **uint256 = 32 bytes** big-endian (low bytes at offsets 96–103 of a 104-byte preimage; bytes 72–95 stay ZERO).
- Valid iff `leadingZeroBits(workHash) >= currentFloor(minter)`; the hash IS the token seed/art.
- Per-wallet escalation: floor = `floorBase + walletMints * 2` → each extra mint from the same wallet costs 4x more work. One die per wallet is the cheap play.
- Retarget: EMA of mint interval vs 90s target, checked every 16 mints; ±1 or fast-clamp +2 bits, bounds [26,40].

## Live state observed (2026-08-21)

- Floor raced 26→40 (max) within ~a day of opening — bot farmers. Selectors: `minted()` 0x4f02c420, `burntCount()` 0x46b260ac, `OPEN_AT()` 0xd8f93498, `currentFloor(address)` 0x6e5b24a5, `walletMints(address)` 0xf0293fd3, `mint(uint256)` 0xa0712d68.
- Retarget events (topic0 0xc7a5c03d…) show the difficulty timeline; Fabbed topic0 0x2e670890…
- At 40 bits expect ~1.1e12 hashes per die.

## Compute economics (measured)

| Path | Rate | 40-bit expected time |
|---|---|---|
| Python pycryptodome loop | 0.23 MH/s | months |
| M2 single core C | ~1.9 MH/s | ~week |
| M2 all cores C/OpenMP-class | ~15 MH/s | ~20 h |
| M2 Metal GPU kernel | est 100–200 MH/s | ~2–4 h |
| Modal 16-vCPU box | **18 MH/s measured** | ~17 h single box |
| Modal ~24 parallel 16-vCPU shards | ~430 MH/s | **~45 min, $1–3** |

User verdict: any plan over ~minutes gets rejected ("no way I am waiting 20 hours") — lead with the rented-compute option.

## Modal pattern that worked (verified)

```python
image = (modal.Image.debian_slim(python_version="3.11")
    .apt_install("gcc")
    .add_local_file("/tmp/fabminer.c", "/root/fabminer.c", copy=True)
    .run_commands("gcc -O3 -fopenmp -o /root/fabminer /root/fabminer.c"))

@app.function(image=image, cpu=16, timeout=60*60)
def mine(start_nonce: int, target_bits: int) -> str:
    import subprocess
    proc = subprocess.run(["/root/fabminer", str(start_nonce), str(target_bits), "16"],
                          capture_output=True, text=True, timeout=3500)
    return f"rc={proc.returncode} STDOUT={proc.stdout} STDERR={proc.stderr[-2000:]}"

@app.local_entrypoint()
def main(start_nonce: int = 0, target_bits: int = 24):
    result = mine.remote(start_nonce, target_bits)
    print(result)
```

Run: `modal run fab_modal.py --start-nonce N --target-bits B`. Scale out by launching many `.spawn()` calls with disjoint start_nonce ranges (prime stride), then poll.

Gotchas hit: `-march=native` built on image-builder CPU → SIGILL (rc=-4) on runner; build plain `-O3`. `run_cmd` doesn't exist (use `run_commands`). `modal run` without an explicit `local_entrypoint` silently does nothing. Apple clang has no OpenMP (`omp.h` missing) — compile locally with pthreads or just test on Modal. Return full rc/stdout/stderr from the function or failures are invisible.

## Verification discipline that caught two bugs

Every found nonce must be re-hashed in independent Python (`pycryptodome.keccak`, digest_bits=256, preimage assembled per contract spec) before broadcasting. This is what exposed (1) a corrupted hand-retyped RC round-constant table and (2) the nonce written at wrong byte offset. Never trust a hand-written hash kernel against itself — same rule as the Metal SHA-256 "abc" vector.

## Broadcast plumbing (verified end-to-end)

Dry-run the mint tx BEFORE the nonce exists: `eth_estimateGas` with a dummy nonce returns the contract's `BelowFloor(uint8,uint8)` revert (selector 0xfcf93064, data shows got/need) — that confirms from-address, gas path, and calldata encoding are all correct without spending anything. Signer stack: `coincurve` for pubkey derivation + `eth-account` for EIP-1559 signing; neither preinstalled (`pip3 install coincurve eth-account`). Sender script pattern: read key from `~/.hermes/secrets/<wallet>_key` (chmod 600), derive address, fetch baseFee + maxPriorityFee, estimateGas, print full cost breakdown, require explicit `--send` flag to actually broadcast. the user pasted a raw private key in chat mid-task; save it immediately to secrets with chmod 600 and derive the address to confirm it's the wallet he means.

## Multi-hour farm reality (2026-08-21 session)

- Two-wallet job: each wallet needs its OWN mined nonce (preimage includes minter). Run two parallel farms with disjoint nonce spaces.
- Round 1: 48 Modal workers × ~57 min ≈ 1.4e12 hashes → no hit. At 40 bits a one-hour farm run is roughly a COIN FLIP, not a guarantee — set expectations accordingly ("~45 min expected" ≠ will finish in 45 min).
- Mid-run failure mode: Modal workspace can get DISABLED between runs or mid-job (`ConflictError: workspace ac-… is disabled`) — likely credit/billing cutoff. The miner code and image survive; relaunching is free of build cost but blocked until billing is fixed. If it happens, tell the user to check modal.com billing — don't burn hours retrying blind.
- Long-run ops pattern: background `modal run … > log 2>&1` with notify_on_complete, then poll every ~10 min with `grep FOUND <log>`. Keep relaunching rounds unless the user says stop; each round reuses the cached image so startup is seconds.
- User checks in ("are you still mining") during long waits — answer with an honest status line: round number, hashes done, odds so far, blockers, and the next decision point.

## Session addendum (2026-08-21 late)

- Rounds 3–5: four more full/failed rounds, still no hit at 40 bits (~5.6e12 hashes total ≈ 19% chance of that drought — unlucky, not broken). Confirms the coin-flip framing; per-wallet round ledger kept in memory.
- Modal spend limit: workspace died AGAIN with `exceeded its spend limit` even though $30 credits remained — the Workspace *budget* (usage cap, before credits) defaulted to ~$1. Docs: max settable budget scales with prior successful charges, so a card must be added first. the user added card + raised budget to $10 after being walked through Settings → Usage & Billing step by step.
- Round 4 both farms: `RemoteError: Function call was cancelled by user or a failure` on healthy account — transient Modal flake, trivial job confirmed healthy, relaunch fixed it. Don't misread this as billing.
