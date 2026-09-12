#!/usr/bin/env python3
"""Adam Bomb Squad ingest + rarity engine (OpenSea API source).

The Hundreds' 25k-supply PFP collection, 0x7ab2...78c5 on Ethereum.
Ingested as a reference collection: full trait architecture + per-token
"Bomb Story"/"Background Story" copy, for studying what a 22.5k-ETH-volume
collection is actually made of. Same method as bakemono_rarity.py.

Usage: adambomb_rarity.py fetch | rank | traits | stories
"""
import json, os, sys, time, urllib.request
from collections import defaultdict, Counter

CONTRACT = "0x7ab2352b1d2e185560494d5e577f9d3c238b78c5"
CHAIN = "ethereum"
BASE = os.path.expanduser("~/.hermes/rarity/adam-bomb-squad")
RAW = os.path.join(BASE, "raw.jsonl")
CURSOR = os.path.join(BASE, "cursor.txt")
TRAITS = os.path.join(BASE, "traits.json")
SCORES = os.path.join(BASE, "scores.json")
KEY = open(os.path.expanduser("~/.hermes/secrets/opensea_key")).read().strip()
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":UA,"accept":"application/json","x-api-key":KEY})
    for a in range(6):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=40).read())
            if isinstance(d, dict) and "errors" in d and "rate" in str(d["errors"]).lower():
                time.sleep(5); continue
            return d
        except Exception as e:
            if a==5: raise
            time.sleep(2**a)
    return {}

def fetch_all():
    """Page the contract's NFTs, appending each token to raw.jsonl. Resumable:
    cursor.txt is written after every page, so a rate-limit death picks up where
    it left off rather than re-walking 25k tokens."""
    os.makedirs(BASE, exist_ok=True)
    cursor = open(CURSOR).read().strip() if os.path.exists(CURSOR) else None
    seen = set()
    if os.path.exists(RAW):
        for line in open(RAW):
            try: seen.add(json.loads(line)["id"])
            except Exception: pass
    out = open(RAW, "a")
    page = 0
    while True:
        url = f"https://api.opensea.io/api/v2/chain/{CHAIN}/contract/{CONTRACT}/nfts?limit=50"
        if cursor: url += f"&next={cursor}"
        d = get(url); nfts = d.get("nfts", [])
        if not nfts: break
        for nft in nfts:
            tid = int(nft["identifier"])
            if tid in seen: continue
            seen.add(tid)
            out.write(json.dumps({
                "id": tid,
                "traits": [{"type":t.get("trait_type"),"value":t.get("value")} for t in nft.get("traits",[])],
                "image": nft.get("original_image_url") or nft.get("image_url"),
                "desc": nft.get("description") or "",
            })+"\n")
        out.flush()
        cursor = d.get("next"); page += 1
        if cursor: open(CURSOR,"w").write(cursor)
        if page % 20 == 0: print(f"  page {page}, {len(seen)} tokens", flush=True)
        if not cursor: break
        time.sleep(0.3)
    out.close()
    print(f"Fetched {len(seen)} tokens -> {RAW}")

def backfill():
    """Cursor pagination over this endpoint silently skips rows (OpenSea appears to
    order by a mutable field, and re-indexing during the walk shifts the page
    boundaries). Sweep the full id range and fetch anything fetch_all() missed."""
    recs = load_raw()
    missing = [i for i in range(0, 25000) if i not in recs]
    print(f"{len(recs)} ingested, {len(missing)} ids missing — backfilling")
    out = open(RAW, "a"); added = 0
    for tid in missing:
        d = get(f"https://api.opensea.io/api/v2/chain/{CHAIN}/contract/{CONTRACT}/nfts/{tid}")
        nft = d.get("nft")
        if not nft: continue
        out.write(json.dumps({
            "id": tid,
            "traits": [{"type":t.get("trait_type"),"value":t.get("value")} for t in nft.get("traits",[])],
            "image": nft.get("original_image_url") or nft.get("image_url"),
            "desc": nft.get("description") or "",
        })+"\n")
        added += 1
        time.sleep(0.3)
    out.close()
    print(f"Backfilled {added}. Total now {len(recs)+added}")

def load_raw():
    recs = {}
    for line in open(RAW):
        r = json.loads(line); recs[r["id"]] = r
    return recs

def compute(recs):
    n = len(recs); freq = defaultdict(Counter)
    for r in recs.values():
        for t in r["traits"]:
            if t["type"] is not None: freq[t["type"]][t["value"]] += 1
    scores = {}
    for tid, r in recs.items():
        score = 0.0; contribs = []
        for t in r["traits"]:
            c = freq[t["type"]].get(t["value"], 1) if t["type"] is not None else 1
            contrib = 1.0/(c/n); score += contrib
            contribs.append((t["type"], t["value"], c, round(contrib,3)))
        scores[str(tid)] = {"score":round(score,4), "traits":len(r["traits"]), "trait_items":contribs}
    ranked = sorted(scores.items(), key=lambda kv: kv[1]["score"], reverse=True)
    for i,(tid,s) in enumerate(ranked,1):
        s["rank"]=i; s["pct"]=round(i/n*100,3)
    json.dump(scores, open(SCORES,"w"))
    json.dump({str(k):v["traits"] for k,v in recs.items()}, open(TRAITS,"w"))
    return freq, scores, ranked

def rank():
    recs = load_raw(); freq, scores, ranked = compute(recs)
    print(f"Rarity computed for {len(ranked)} tokens. TOP 15 RAREST:")
    for tid,s in ranked[:15]:
        tc = "; ".join(f"{a}:{b}(x{c})" for a,b,c,_ in s["trait_items"])
        print(f"  #{s['rank']:>3} tok {tid:<6} score {s['score']:<10} {tc}")

def traits():
    recs = load_raw(); freq,_,_ = compute(recs); n = len(recs)
    print(f"TRAIT ARCHITECTURE — {n} tokens, {len(freq)} trait categories\n")
    for cat in sorted(freq, key=lambda c: -len(freq[c])):
        vals = freq[cat]
        cover = sum(vals.values())
        print(f"{cat}: {len(vals)} distinct values, on {cover}/{n} tokens ({cover/n*100:.1f}%)")
        for v,c in vals.most_common(6):
            print(f"    {c/n*100:6.2f}%  x{c:<6} {v}")
        if len(vals) > 6:
            rare = vals.most_common()[-3:]
            print(f"    ...rarest: " + ", ".join(f"{v} (x{c})" for v,c in rare))
        print()

if __name__=="__main__":
    cmd = sys.argv[1] if len(sys.argv)>1 else "fetch"
    {"fetch":fetch_all, "backfill":backfill, "rank":rank, "traits":traits}[cmd]()
