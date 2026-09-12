#!/usr/bin/env python3
"""Bakemono Crayons rarity engine (OpenSea API source).
Statistical trait-frequency rarity over full supply, then cross-refs your held
token ids (0x1111…1111). Same method as raritytest_rarity.py.
Usage: bakemono_rarity.py fetch | rank | mine | both
"""
import json, os, sys, time, urllib.request
from collections import defaultdict, Counter

CONTRACT = "0x4ff63dd0d0939a02b21cbb74c18e522ec3682b29"
CHAIN = "robinhood"
WALLET = "0x1111111111111111111111111111111111111111"
BASE = os.path.expanduser("~/.hermes/rarity/bakemono")
TRAITS = os.path.join(BASE, "traits.json")
SCORES = os.path.join(BASE, "scores.json")
HELD_FILE = os.path.join(BASE, "held.json")
KEY = open(os.path.expanduser("~/.hermes/secrets/opensea_key")).read().strip()
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":UA,"accept":"application/json","x-api-key":KEY})
    for a in range(5):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=30).read())
            if isinstance(d, dict) and "errors" in d and "rate" in str(d["errors"]).lower():
                time.sleep(4); continue
            return d
        except Exception:
            if a==4: raise
            time.sleep(2**a)
    return {}

def fetch_all():
    os.makedirs(BASE, exist_ok=True)
    traits={}; cursor=None; page=0
    while True:
        url=f"https://api.opensea.io/api/v2/chain/{CHAIN}/contract/{CONTRACT}/nfts?limit=50"
        if cursor: url+=f"&next={cursor}"
        d=get(url); nfts=d.get("nfts",[])
        if not nfts: break
        for nft in nfts:
            tid=int(nft["identifier"])
            traits[tid]=[{"type":t.get("trait_type"),"value":t.get("value")} for t in nft.get("traits",[])]
        cursor=d.get("next"); page+=1
        if page%25==0: print(f"  page {page}, {len(traits)} tokens")
        if not cursor: break
        time.sleep(0.25)
    json.dump(traits, open(TRAITS,"w"))
    print(f"Saved {len(traits)} token trait records -> {TRAITS}")
    return traits

def fetch_held():
    """All NFTs in this collection currently owned by the wallet (OpenSea account endpoint)."""
    held=[]; cursor=None; page=0
    while page<20:
        url=f"https://api.opensea.io/api/v2/chain/{CHAIN}/account/{WALLET}/nfts?limit=50&collection=bakemono-crayons"
        if cursor: url+=f"&next={cursor}"
        d=get(url); nfts=d.get("nfts",[])
        if not nfts: break
        for nft in nfts:
            if nft.get("collection")=="bakemono-crayons":
                held.append(int(nft["identifier"]))
        cursor=d.get("next"); page+=1
        if not cursor: break
        time.sleep(0.25)
    json.dump(held, open(HELD_FILE,"w"))
    print(f"Held tokens: {len(held)} -> {HELD_FILE}")
    return held

def compute(traits):
    n=len(traits); freq=defaultdict(Counter); per={}
    for tid,tr in traits.items():
        per[tid]=tr
        for t in tr:
            if t["type"] is not None:
                freq[t["type"]][t["value"]]+=1
    scores={}
    for tid,tr in per.items():
        score=0.0; contribs=[]
        for t in tr:
            c=freq[t["type"]].get(t["value"],1) if t["type"] is not None else 1
            contrib=1.0/(c/n)
            score+=contrib
            contribs.append((t["type"],t["value"],c,round(contrib,3)))
        scores[str(tid)]={"score":round(score,4),"traits":len(tr),"trait_items":contribs}
    ranked=sorted(scores.items(), key=lambda kv: kv[1]["score"], reverse=True)
    for i,(tid,s) in enumerate(ranked,1):
        s["rank"]=i; s["pct"]=round(i/n*100,2)
    json.dump(scores, open(SCORES,"w"))
    return scores, ranked

def rank():
    traits=json.load(open(TRAITS)); scores,ranked=compute(traits)
    print(f"Rarity computed for {len(ranked)} tokens. TOP 20 RAREST:")
    for tid,s in ranked[:20]:
        tc="; ".join(f"{a}:{b}(x{c})" for a,b,c,_ in s["trait_items"])
        print(f"  #{s['rank']:>4} tok {tid:<5} score {s['score']:<9} traits {s['traits']}  {tc}")

def mine():
    scores=json.load(open(SCORES)); held=json.load(open(HELD_FILE))
    n=len(scores)
    held_sorted=sorted(held, key=lambda t: scores.get(str(t),{}).get("rank",10**9))
    avg=sum(scores.get(str(t),{}).get("rank",n) for t in held)/len(held) if held else 0
    avgscore=sum(scores.get(str(t),{}).get("score",0) for t in held)/len(held) if held else 0
    print(f"YOUR {len(held)} Bakemono holdings (rarest first). Avg rank {avg:.0f}/{n} (top {avg/n*100:.1f}%). Avg score {avgscore:.2f}:")
    for tid in held_sorted:
        s=scores.get(str(tid),{})
        tc="; ".join(f"{a}:{b}(x{c})" for a,b,c,_ in s.get("trait_items",[]))
        print(f"  #{s.get('rank','?')}/{n}  pct {s.get('pct','?')}%  tok {tid}  score {s.get('score','?')}  {tc}")

if __name__=="__main__":
    cmd=sys.argv[1] if len(sys.argv)>1 else "both"
    if cmd in ("both",): fetch_all(); fetch_held(); rank(); mine()
    elif cmd=="fetch": fetch_all()
    elif cmd=="held": fetch_held()
    elif cmd=="rank": rank()
    elif cmd=="mine": mine()
