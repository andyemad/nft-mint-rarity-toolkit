"""Sample an NFT collection's on-chain metadata and print per-trait-category
variant distributions (counts + % of sampled tokens). Verified 2026-08-22
against HOWLERZ (Arweave metadata) and Shadow Wolves (S3 metadata) at 150/150
success each; Pudgy Penguins IPFS path works but ipfs.io rate-limits bursts
(see PACING note).

Usage:
    python3 trait_sampler.py --rpc https://eth.rpc.blxrbdn.com \
        --ca 0x40cf6a63c35b6886421988871f6b74cc86309940 \
        --supply 5000 -n 150 [--seed 31] [--json out.json]

Requires only python3 stdlib + curl on PATH.

Key techniques baked in (all hit in practice):
- tokenURI via eth_call selector 0xc87b56dd; decode with
  re.search(rb'https?[^\\x00]+', bytes.fromhex(res[2:])) then strip NULs —
  robust against ABI offset math bugs.
- Metadata hosts vary: S3 JSON w/o .json suffix, Arweave per-token URLs,
  IPFS CID folders. This script resolves whatever tokenURI returns directly;
  for ipfs:// URIs it routes through a gateway via curl.
- ThreadPoolExecutor(10) is fine for S3/Arweave. For IPFS use --pacing 1.0+
  and workers=2 — ipfs.io 429s/blocks bursts from one machine, and once
  blocked it stays blocked for ~tens of minutes. Sequential curl with sleep
  is the reliable shape.
"""
import argparse, collections, json, random, re, subprocess, time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

def eth_call(rpc, ca, data):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                       "params": [{"to": ca, "data": data}, "latest"]}).encode()
    req = urllib.request.Request(rpc, data=body,
                                 headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=20).read())
    return r.get("result")

def token_uri(rpc, ca, tid):
    pad = tid.to_bytes(32, "big").hex()
    res = eth_call(rpc, ca, "0xc87b56dd" + pad)
    if not res:
        return None
    raw = bytes.fromhex(res[2:])
    m = re.search(rb"https?[^\x00]+", raw)
    if m:
        return m.group(0).decode().rstrip("\x00")
    m = re.search(rb"ipfs://[^\x00]+", raw)
    return m.group(0).decode().rstrip("\x00") if m else None

def fetch(url):
    if url.startswith("ipfs://"):
        url = "https://ipfs.io/ipfs/" + url[7:]
    r = subprocess.run(["curl", "-sL", "--max-time", "25", url], capture_output=True)
    try:
        meta = json.loads(r.stdout)
        return [(t.get("trait_type"), t.get("value")) for t in meta.get("attributes", [])]
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpc", required=True)
    ap.add_argument("--ca", required=True)
    ap.add_argument("--supply", type=int, required=True)
    ap.add_argument("-n", type=int, default=120)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--pacing", type=float, default=0.0,
                    help="sleep between sequential fetches (set >0 for IPFS)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    random.seed(a.seed)
    ids = random.sample(range(1, a.supply + 1), min(a.n, a.supply))

    def job(i):
        uri = token_uri(a.rpc, a.ca, i)
        if not uri:
            return None
        res = fetch(uri)
        if res and a.pacing:
            time.sleep(a.pacing)
        return res

    cats = collections.defaultdict(collections.Counter)
    n_traits = collections.Counter()
    ok = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for res in ex.map(job, ids):
            if not res:
                continue
            ok += 1
            n_traits[len(res)] += 1
            for cat, val in res:
                cats[cat][val] += 1

    print(f"SAMPLED {ok}/{len(ids)}")
    print("trait-count per token:", dict(sorted(n_traits.items())))
    for cat in sorted(cats):
        cnt = cats[cat]
        total = sum(cnt.values())
        print(f"\n== {cat} ({len(cnt)} variants) ==")
        for v, c in cnt.most_common():
            print(f"  {v}: {100 * c / total:.0f}%")
    if a.json:
        json.dump({k: dict(v) for k, v in cats.items()}, open(a.json, "w"))

if __name__ == "__main__":
    main()
