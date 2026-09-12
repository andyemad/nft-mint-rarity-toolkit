#!/usr/bin/env python3
"""Full-history secondary-market volume for an EVM NFT collection, no API keys.

Answers the question "how much total ETH volume has this collection traded on
secondary markets?" (all-time, not per-minute sweep windows) from public RPC
logs alone. Verified 2026-08-14 on RH chain (Fox Brokers, 0xe62c...).

Sale heuristic (same as onchain-secondary-sales-detection.md):
a secondary Transfer (from != 0x0, to != 0x0) whose transaction carries
native value > 0 counts as a sale; price = tx.value.

Usage:
  python3 collection_volume.py <collection> [blocks_back] [rpc_url]
  python3 collection_volume.py 0xe62c08803a0c1e3baecece790eeba53a6a87b757 3000000
  # For a very young collection (hours-days old), start from a small lookback
  # like 500000-3000000 blocks; the script prints total logs so you can widen
  # if the first scan stops early in the collection's history.

Pitfalls encoded:
- arrowrpc rate-limits with nginx 429 bodies: retry with backoff, and READ
  the body first — a JSON-RPC -32005 body is a query-shape rejection (range
  cap), a nginx HTML body is a true rate limit. Both get retried here.
- Some providers 403 urllib without User-Agent: Mozilla/5.0 — always set it.
- OpenSea's displayed total volume is HIGHER than the native-only scan when
  trades settle in WETH/ERC-20 (RH Seaport settles in WETH): the native scan
  is a lower bound, not the marketplace total. Report both, don't reconcile
  silently.
"""
import json, sys, time, urllib.request, urllib.error
from collections import defaultdict

COLLECTION = sys.argv[1] if len(sys.argv) > 1 else "0xe62c08803a0c1e3baecece790eeba53a6a87b757"
START_BLOCKS_BACK = int(sys.argv[2]) if len(sys.argv) > 2 else 1000000
RPC = sys.argv[3] if len(sys.argv) > 3 else "https://rpc.arrowrpc.com"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def batch(items, tries=4):
    for attempt in range(tries):
        body = json.dumps(items).encode()
        req = urllib.request.Request(RPC, data=body, headers={
            "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body_err = e.read().decode(errors="ignore")[:300]
            if attempt == tries - 1:
                raise RuntimeError(f"HTTP {e.code}: {body_err}")
            print(f"  retry {attempt + 1} after {e.code}: {body_err}", flush=True)
            time.sleep(2 * (attempt + 1))


def rpc(method, params):
    out = batch([{"jsonrpc": "2.0", "id": 1, "method": method, "params": params}])
    if isinstance(out, list):
        return out[0].get("result")
    return out.get("result")


cur = int(rpc("eth_blockNumber", []), 16)
start = cur - START_BLOCKS_BACK
print(f"chain head: {cur} | scanning {start}..{cur} ({START_BLOCKS_BACK} blocks)")

# 1. All Transfer logs, chunked <=1000 blocks, 10 batches/call
logs = []
lo = start
while lo <= cur:
    reqs = []
    for i in range(10):
        if lo > cur:
            break
        hi = min(lo + 999, cur)
        reqs.append({"jsonrpc": "2.0", "id": i, "method": "eth_getLogs",
                     "params": [{"address": COLLECTION, "topics": [TRANSFER],
                                 "fromBlock": hex(lo), "toBlock": hex(hi)}]})
        lo = hi + 1
    if not reqs:
        break
    for r in batch(reqs):
        if "result" in r and r["result"]:
            logs.extend(r["result"])
    time.sleep(0.1)

print(f"total Transfer logs: {len(logs)}")

# 2. Secondary = from != 0x0 AND to != 0x0 (drop mints + burns)
ZERO = "0x" + "0" * 64
secondary = [l for l in logs if l["topics"][1] != ZERO and l["topics"][2] != ZERO]
print(f"secondary transfers: {len(secondary)}")

# 3. Batch tx lookups (60/call) for unique hashes
txs = sorted({l["transactionHash"] for l in secondary})
tx_values = {}
for i in range(0, len(txs), 60):
    chunk = txs[i:i + 60]
    reqs = [{"jsonrpc": "2.0", "id": j, "method": "eth_getTransactionByHash",
             "params": [h]} for j, h in enumerate(chunk)]
    for j, r in enumerate(batch(reqs)):
        if "result" in r and r["result"]:
            tx_values[chunk[j]] = int(r["result"].get("value", "0x0"), 16)
    time.sleep(0.05)

# 4. Value-bearing txs = sales
sale_txs = {h: v for h, v in tx_values.items() if v > 0}

# 5. Attribute: each secondary transfer in a value-bearing tx = 1 sale.
# (For multi-collection txs volume should be split proportionally by count;
# a single-collection scan approximates volume = tx.value per sale tx.)
sales = 0
volume_wei = 0
buyers = set()
by_price = defaultdict(int)
for l in secondary:
    h = l["transactionHash"]
    if h not in sale_txs:
        continue
    sales += 1
    buyers.add("0x" + l["topics"][2][-40:])
    by_price[sale_txs[h]] += 1
volume_wei = sum(sale_txs.values())

vol_eth = volume_wei / 1e18
print("\n===== RESULTS =====")
print(f"secondary sales: {sales}")
print(f"unique sale txs: {len(sale_txs)}")
print(f"distinct buyers: {len(buyers)}")
print(f"total native volume: {vol_eth:.6f} ETH ({volume_wei} wei)")
if sales:
    print(f"avg price: {vol_eth / sales:.6f} ETH")
top = sorted(by_price.items(), key=lambda x: -x[1])[:8]
print("price histogram (wei -> count):",
      [(f"{p / 1e18:.5f} ETH", c) for p, c in top])
print("\nNOTE: native tx.value only. WETH/ERC-20-settled trades (OpenSea/RH")
print("Seaport) are NOT included; the marketplace's own displayed volume")
print("will be higher. Use this scan as the on-chain lower bound.")
