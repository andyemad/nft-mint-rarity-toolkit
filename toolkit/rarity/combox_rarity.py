#!/usr/bin/env python3
"""ComboX rarity engine v2 (OpenSea API source).

Pulls all 5000 ComboX token traits via OpenSea v2 API (cursor pagination),
computes trait-frequency statistical rarity, ranks, and cross-refs your
held token ids. This beats OpenSea's own rarity tab (which lags) by ranking
the same raw metadata the instant it is indexed.

Usage:
  python3 combox_rarity.py fetch     # pull all traits -> traits.json
  python3 combox_rarity.py rank      # compute rarity if traits.json exists
  python3 combox_rarity.py both      # fetch then rank (default)
  python3 combox_rarity.py mine      # my holdings ranked
"""
import json, os, sys, time, urllib.request
from collections import defaultdict, Counter

CONTRACT = "0x512faa1354c8d634cd0e78e6ec5ba1d9fe19d55c"
BASE = os.path.expanduser("~/.hermes/rarity/combox")
TRAITS = os.path.join(BASE, "traits.json")
SCORES = os.path.join(BASE, "scores.json")
# Token ids you hold (optional) — powers `mine` / the dashboard highlight.
# Provide comma-separated: HELD="12,44,91" python3 <script>.py ...
HELD = [int(x) for x in os.environ.get("HELD", "").split(",") if x.strip()]

KEY_FILE = os.path.expanduser("~/.hermes/secrets/opensea_key")
KEY = open(KEY_FILE).read().strip()
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":UA,"accept":"application/json","x-api-key":KEY})
    for attempt in range(4):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=30).read())
            if "errors" in d and "rate limit" in str(d["errors"]).lower():
                time.sleep(3); continue
            return d
        except Exception as e:
            if attempt==3: raise
            time.sleep(2**attempt)
    return {}

def fetch_all():
    os.makedirs(BASE, exist_ok=True)
    traits = {}
    cursor = None
    page = 0
    while True:
        url = f"https://api.opensea.io/api/v2/chain/robinhood/contract/{CONTRACT}/nfts?limit=50"
        if cursor: url += f"&next={cursor}"
        d = get(url)
        nfts = d.get("nfts", [])
        if not nfts: break
        for nft in nfts:
            tid = int(nft["identifier"])
            traits[tid] = [{"type":t["trait_type"],"value":t["value"]} for t in nft.get("traits",[])]
        cursor = d.get("next")
        page += 1
        if page % 20 == 0: print(f"  page {page}, {len(traits)} tokens")
        if not cursor: break
        time.sleep(0.3)
    json.dump(traits, open(TRAITS,"w"))
    print(f"Saved {len(traits)} token trait records -> {TRAITS}")
    return traits

def compute(traits):
    n = len(traits)
    freq = defaultdict(Counter)
    per = {}
    for tid,tr in traits.items():
        per[tid]=tr
        for t in tr:
            freq[t["type"]][t["value"]] += 1
    scores = {}
    for tid,tr in per.items():
        score = 0.0
        contribs=[]
        for t in tr:
            c = freq[t["type"]].get(t["value"],1)
            contrib = 1.0/(c/n)
            score += contrib
            contribs.append((t["type"],t["value"],c,round(contrib,3)))
        scores[str(tid)] = {"score":round(score,4),"traits":len(tr),"trait_items":contribs}
    ranked = sorted(scores.items(), key=lambda kv: kv[1]["score"], reverse=True)
    for i,(tid,s) in enumerate(ranked,1):
        s["rank"]=i; s["pct"]=round(i/n*100,2)
    json.dump(scores, open(SCORES,"w"))
    return scores, ranked

def rank():
    if not os.path.exists(TRAITS):
        print("No traits.json. Run fetch first."); return
    traits = json.load(open(TRAITS))
    scores, ranked = compute(traits)
    print(f"Rarity computed for {len(ranked)} tokens. TOP 30 RAREST:")
    for tid,s in ranked[:30]:
        tc = "; ".join(f"{a}:{b}(x{c})" for a,b,c,_ in s["trait_items"])
        print(f"  #{s['rank']:>4} tok {tid:<5} score {s['score']:<9} traits {s['traits']}  {tc}")

def mine():
    if not os.path.exists(SCORES):
        print("No scores yet. Run both first."); return
    scores = json.load(open(SCORES))
    held = sorted(HELD, key=lambda t: scores.get(str(t),{}).get("rank",10**9))
    avg = sum(scores.get(str(t),{}).get("rank",5000) for t in held)/len(held) if held else 0
    rarest = held[:1]
    print(f"YOUR {len(held)} ComboX holdings (rarest first). Avg rank {avg:.0f}/5000:")
    for tid in held:
        s = scores.get(str(tid),{})
        print(f"  #{s.get('rank','?')} tok {tid} score {s.get('score','?')} traits {s.get('traits','?')}")

if __name__=="__main__":
    cmd = sys.argv[1] if len(sys.argv)>1 else "both"
    if cmd in ("both",):
        fetch_all(); rank()
    elif cmd=="fetch": fetch_all()
    elif cmd=="rank": rank()
    elif cmd=="mine": mine()
