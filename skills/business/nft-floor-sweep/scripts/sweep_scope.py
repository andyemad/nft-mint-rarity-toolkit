#!/usr/bin/env python3
"""
sweep_scope.py — zero-spend scoping pass for an NFT floor sweep.

Usage:
  python3 sweep_scope.py <collection_slug>
  python3 sweep_scope.py <collection_slug> --usd 2264.77

Does NOT buy anything. Outputs:
  - buyer wallet balance (RH RPC)
  - full price ladder (wei -> count) across the ENTIRE active book (paginated)
  - floor-group count + cheapest-N cumulative quotes (ETH and USD)
  - floor-stuffer detection (repeat makers at floor)

API key read from ~/.hermes/secrets/opensea_key (never printed to chat).
"""
import json, sys, urllib.request, time, collections

KEY = open("~/.hermes/secrets/opensea_key").read().strip()
UA = "Mozilla/5.0"
BASE = "https://api.opensea.io/api/v2"
RW = "https://rpc.mainnet.chain.robinhood.com"
BUYER = "0x1111111111111111111111111111111111111111"

def get(url):
    req = urllib.request.Request(url, headers={"accept": "application/json",
                                                "X-API-KEY": KEY, "User-Agent": UA})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            print("retry:", e); time.sleep(2)
    return {}

def rpc(m, p):
    body = json.dumps({"jsonrpc": "2.0", "method": m, "params": p, "id": 1}).encode()
    req = urllib.request.Request(RW, data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def main():
    slug = sys.argv[1]
    usd = 2264.77
    if "--usd" in sys.argv:
        usd = float(sys.argv[sys.argv.index("--usd") + 1])

    bal = int(rpc("eth_getBalance", [BUYER, "latest"])["result"], 16) / 1e18
    print(f"Bot wallet {BUYER[:10]}... balance: {bal:.6f} ETH (${bal*usd:.2f})\n")

    stats = get(f"{BASE}/collections/{slug}/stats")
    print(f"collection: {slug} | floor: {stats.get('total',{}).get('floor_price')} ETH")

    all_listings, cursor = [], None
    for _ in range(200):
        u = f"{BASE}/listings/collection/{slug}/best?limit=50"
        if cursor:
            u += f"&next={cursor}"
        d = get(u)
        ls = d.get("listings", [])
        if not ls:
            break
        all_listings += ls
        cursor = d.get("next")
        if not cursor:
            break
    print(f"total active listings: {len(all_listings)}\n")

    ladder = collections.Counter(l["price"]["current"]["value"] for l in all_listings)
    print("--- Price ladder (wei -> count) ---")
    for v, c in sorted(ladder.items(), key=lambda x: int(x[0])):
        print(f"{int(v)/1e18:.6f} ETH  x{c}")

    floor = stats.get('total', {}).get('floor_price')
    floor_wei = str(int(floor * 1e18)) if floor else None
    if floor_wei:
        floor_items = [l for l in all_listings if l["price"]["current"]["value"] == floor_wei]
        print(f"\nfloor-listed count: {len(floor_items)}")
        makers = collections.Counter(l.get("maker", {}).get("address", "?") for l in floor_items)
        if len(makers) == 1:
            m = next(iter(makers))
            print(f"FLOOR-STUFFER: all {len(floor_items)} floor listings are one maker {m[:10]}...")
        else:
            print(f"floor makers: {len(makers)} distinct")
        tot = sum(int(l["price"]["current"]["value"]) for l in all_listings) / 1e18
        print(f"ALL listings total cost: {tot:.4f} ETH (${tot*usd:.2f})")
        s = sorted(all_listings, key=lambda l: int(l["price"]["current"]["value"]))
        for n in [5, 10, 15, 20, 25, 30]:
            if n <= len(s):
                c = sum(int(l["price"]["current"]["value"]) for l in s[:n]) / 1e18
                print(f"cheapest {n}: {c:.5f} ETH (${c*usd:.2f})")

if __name__ == "__main__":
    main()
