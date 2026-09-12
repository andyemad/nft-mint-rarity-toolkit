# Hashcats GPU mint farm

A working proof-of-work mining farm for **Hashcats** (`hashcats.fun`), a PoW
collection on Robinhood Chain (4663). CPU verifies, H100s mine, the local machine
signs and broadcasts.

The point of this directory is that PoW minting is only slow if you mine on a CPU.
The CPU miner finds a solution in hours or never; a handful of rented H100s finds
one in seconds and the whole loop costs cents in compute.

## The scheme

```
workHash = keccak256( miner(20) ‖ nonce(uint256 BE, 32) ‖ prev(32) ‖ anchor(32) )
accept when workHash < target
```

`prev` is the work value of the previous cat, so each token links to the one
before it. The chain is sequential: you cannot parallelize across tokens, only
within one nonce search. `anchor` is the block the round is pinned to.

The preimage is 116 bytes, which is exactly one Keccak block (rate 136). That is
why the CUDA kernel is fast: no permutation chaining, one round, pre-absorbed
state, nonce XORed straight into the message words.

## Files

| File | Role |
|---|---|
| `hashcats.py` | Protocol layer: read round state, build and simulate the tx, solve on CPU, send, or loop. |
| `hashcats_modal.py` | The CUDA kernel on Modal H100s. Modes: `probe`, `bench`, `mine`. |
| `farm.py` | The farm itself: N H100 shards mining in parallel, local signing and broadcast, audit log. |
| `list_cats.py` | Walk the collection and report what has been mined. |
| `hcwatch.py` | Watch rounds so you know when a new one opens. |
| `new_wallet.py` | Fresh wallet for the run. |
| `sweep_back.py` | Return funds from the run wallet. |
| `run_until_minted.sh` | Keep trying until it lands. |
| `../hcminer.cu`, `../hcminer.c` | The kernels. `hcminer.c` has a self-check that compares its fast path against its own reference Keccak over 200,000 nonces. |

## Sequence that matters

1. **Prove the kernel against a reference before renting anything.** `probe` mode
   hashes a known nonce and compares it to the Python keccak. A GPU kernel with
   the wrong endianness mines forever and finds nothing, and you pay for every
   second of it. The two classic bugs are nonce bytes XORed into the state word in
   the wrong order, and the leading-zero test applied to a byte-swapped digest.
2. **Benchmark.** `bench` reports GH/s. On an H100 the CUDA kernel does roughly
   7 GH/s, so a 40-bit target lands in minutes, not hours.
3. **Dry run the whole loop.** `farm.py --dry` verifies each solution with the
   independent Python keccak and simulates the mint, so you never broadcast a bad
   nonce.
4. **Then farm for real.**

```bash
# 0. dependencies
pip install modal eth-account pycryptodome coincurve
modal setup

# 1. sanity: does the kernel agree with the reference?
modal run hashcats_modal.py --mode probe

# 2. how fast is it?
modal run hashcats_modal.py --mode bench

# 3. read the current round
python3 hashcats.py state
python3 hashcats.py sim

# 4. full loop, no spending: 4 shards, 30 minutes, verify and simulate only
python3 farm.py --shards 4 --minutes 30 --dry

# 5. real farm (needs a funded wallet)
python3 farm.py --shards 8 --minutes 30 --key ~/.hermes/secrets/hashcats_key
```

`farm.py` verifies every candidate against the Python reference **and** re-checks
the round (prev and anchor must still match) before broadcast. A solution from a
round that has already advanced is worthless, and paying gas for it is worse than
worthless.

## Costs, honestly

Renting H100s is not free and the target moves. Hashcats' difficulty is set by the
collection, and other miners are competing for the same rounds, so treat this as
contest entry rather than a mint button. What makes it viable is that the loop is
mechanical: verify, simulate, broadcast, log. Do the arithmetic on your own
compute spend before you start a long run, and stop when the round is stale.

## What went wrong the first time

Recorded because it is the useful part:

- The kernel was correct but the farm could not mint, because there was no RH-ETH
  in the run wallet. Mining and paying are separate problems. Fund the wallet that
  will broadcast, and check its balance before you start.
- The Robinhood RPC rate-limits per IP on reads and writes. A shard that polls the
  RPC in a tight loop gets 429s and looks like a protocol failure. Read once per
  round, then mine.
- Python `urllib` gets a 403 from that RPC without a browser `User-Agent`.

## Keys

Everything reads a key file by path, `chmod 600`, never from an argument. See the
repository `SECURITY.md`.
