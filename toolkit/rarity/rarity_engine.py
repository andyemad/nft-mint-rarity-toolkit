#!/usr/bin/env python3
"""the rarity-test collection rarity engine + reveal watcher (Robinhood Chain).

Re-usable scaffold: collection config + rarity computation + wallet compare.
Beats OpenSea's rarity tab by computing trait-frequency rarity the moment
per-token metadata diverges (reveal), before OpenSea indexes it.

Usage:
  python3 rarity_engine.py watch          # poll tokenURI; on reveal, compute+report
  python3 rarity_engine.py compute        # force full rarity computation
  python3 rarity_engine.py my-holdings    # rank your held token ids
"""
import json, os, re, sys, time, math, urllib.request, html as htm
from collections import defaultdict, Counter

CONTRACT = "0x512faa1354c8d634cd0e78e6ec5ba1d9fe19d55c"
CHAIN = "robinhood"
SUPPLY = 5000
RPC = "https://rpc.mainnet.chain.robinhood.com"
WALLET = "0x1111111111111111111111111111111111111111"
# Token ids you hold (optional) — powers `mine` / the dashboard highlight.
# Provide comma-separated: HELD="12,44,91" python3 <script>.py ...
HELD = [int(x) for x in os.environ.get("HELD", "").split(",") if x.strip()]

BASE = os.path.expanduser("~/.hermes/rarity/raritytest")
META_DIR = os.path.join(BASE, "metadata")
os.makedirs(META_DIR, exist_ok=True)
SCORE_FILE = os.path.join(BASE, "scores.json")

IPFS_GATEWAYS = [
    "https://{cid}.ipfs.w3s.link",
    "https://nftstorage.link/ipfs/{cid}",
    "https://ipfs.io/ipfs/{cid}",
    "https://cloudflare-ipfs.com/ipfs/{cid}",
    "https://{cid}.cf-ipfs.com",
    "https://4everland.io/ipfs/{cid}",
    "https://dweb.link/ipfs/{cid}",
]

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# ---------------- RPC helpers ----------------
def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json","User-Agent":UA,"Accept":"application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in d: raise Exception(d["error"])
    return d["result"]

def call(data):
    return rpc("eth_call", [{"to":CONTRACT,"data":data},"latest"])

def decode_str(r):
    if not r or r == "0x": return None
    out = bytes.fromhex(r[2:])
    off = int(out[:32].hex(),16)
    ln = int(out[off:off+32].hex(),16)
    return out[off+32:off+32+ln].decode('utf-8','ignore')

def token_uri(tid):
    sel = "0xc87b56dd" + tid.to_bytes(32,'big').hex()
    return decode_str(call(sel))

# ---------------- Reveal detection ----------------
def is_revealed(sample_ids=(1,2,50,500,2500,4999)):
    uris = set()
    failed = 0
    for t in sample_ids:
        try:
            u = token_uri(t)
            if u: uris.add(u)
        except Exception:
            failed += 1
    return len(uris) > 1, uris, failed

# ---------------- Metadata fetch ----------------
def fetch_url(url):
    for gw in IPFS_GATEWAYS:
        try:
            target = gw.format(cid=url) if url.startswith("ipfs://") else url
            req = urllib.request.Request(target, headers={"User-Agent":UA,"Accept":"application/json"})
            resp = urllib.request.urlopen(req, timeout=25)
            body = resp.read()
            if b"<html" in body[:200].lower() and b"challenge" in body[:5000].lower():
                continue
            return body
        except Exception:
            continue
    return None

def fetch_metadata(tid, uri):
    """Return traits list from metadata JSON given token id + uri."""
    body = fetch_url(uri)
    if not body:
        # strip ipfs prefix, try raw cid file path against gateways
        cid = uri.replace("ipfs://","").strip("/")
        body = fetch_url(cid)
    if not body:
        return None
    try:
        j = json.loads(body.decode('utf-8','ignore'))
    except Exception:
        # maybe a directory/redirect: try common json detection
        m = re.search(rb'\{.*\}', body, re.S)
        if m:
            try: j = json.loads(m.group(0).decode('utf-8','ignore'))
            except Exception: return None
        else:
            return None
    traits = j.get("attributes") or j.get("traits") or []
    return traits

# ---------------- Rarity ----------------
def compute_scores(meta_map):
    """meta_map: {tid: [ {trait_type, value}, ... ]}"""
    freq = defaultdict(Counter)   # trait_type -> {value: count}
    per_tok = {tid: [] for tid in meta_map}
    for tid, traits in meta_map.items():
        for t in traits:
            ttype = str(t.get("trait_type") or t.get("name") or "?")
            value = str(t.get("value") or t.get("trait_value") or "?")
            freq[ttype][value] += 1
            per_tok[tid].append((ttype, value))

    n = len(meta_map) or 1
    scores = {}
    ranks = {}
    for tid, toks in per_tok.items():
        # trait-frequency rarity: sum of (1/(count/n)) per trait = weighted
        # statistical rarity (rarity.tools style uses 1/(freq) contributions)
        score = 0.0
        contributions = []
        for ttype, value in toks:
            count = freq[ttype].get(value, 1)
            contrib = 1.0 / (count / n)   # higher = rarer
            score += contrib
            contributions.append((ttype, value, count, round(contrib,3)))
        scores[tid] = {"score": round(score,4), "trait_count": len(toks), "traits": contributions}

    ranked = sorted(scores.items(), key=lambda kv: kv[1]["score"], reverse=True)
    for i,(tid,s) in enumerate(ranked,1):
        s["rank"] = i
        s["pct"] = round(i/n*100,2)
    return scores, ranked

# ---------------- Persist ----------------
def save_scores(scores):
    with open(SCORE_FILE,"w") as f:
        json.dump(scores,f,indent=2)

def load_scores():
    if not os.path.exists(SCORE_FILE): return {}
    return json.load(open(SCORE_FILE))

# ---------------- Commands ----------------
def cmd_watch():
    print(f"the rarity-test collection reveal watcher on {CHAIN} ({SUPPLY} supply). Polling tokenURI divergence...")
    while True:
        rev, uris, failed = is_revealed()
        print(f"  [{time.strftime('%H:%M:%S')}] revealed={rev} distinct_uris={len(uris)} failed={failed}")
        if rev:
            print("REVEAL DETECTED — distinct tokenURIs present. Computing rarity...")
            cmd_compute(force=True)
            return
        time.sleep(120)

def cmd_compute(force=False):
    print("Fetching metadata for all tokens (cached). This is the big pass...")
    meta_map = {}
    # quick pass: only tokenURIs that differ from the placeholder are revealed;
    # but if not revealed, abort early.
    rev, uris, failed = is_revealed()
    if not rev and not force:
        print("NOT REVEALED — all tokens share one placeholder. Nothing to rank yet.")
        print("Run 'python3 rarity_engine.py watch' to wait for reveal.")
        return
    for tid in range(SUPPLY):
        cache = os.path.join(META_DIR, f"{tid}.json")
        traits = None
        if os.path.exists(cache):
            traits = json.load(open(cache))
        else:
            try:
                uri = token_uri(tid)
                traits = fetch_metadata(tid, uri)
                if traits is None:
                    traits = []  # non-revealed/unresolvable token
                json.dump(traits, open(cache,"w"))
            except Exception as e:
                traits = []
                json.dump(traits, open(cache,"w"))
        meta_map[tid] = traits
        if tid % 500 == 0:
            print(f"  {tid}/5000")
    scores, ranked = compute_scores(meta_map)
    save_scores(scores)
    print(f"Computed rarity for {len(ranked)} tokens. Top 20:")
    for tid,s in ranked[:20]:
        print(f"  #{s['rank']:>4} tok {tid:<5} score {s['score']:<10} traits {s['trait_count']}")

def cmd_holdings():
    scores = load_scores()
    if not scores:
        print("No scores yet. Run compute first.")
        return
    held_sorted = sorted(HELD, key=lambda t: scores.get(str(t),{}).get("rank",10**9))
    print(f"Your {len(HELD)} the rarity-test collection holdings ranked (rarest first):")
    for tid in held_sorted:
        s = scores.get(str(tid)) or scores.get(tid,{})
        rank = s.get("rank","?")
        score = s.get("score","?")
        tc = s.get("trait_count","?")
        print(f"  #{rank:>4} tok {tid:<5} score {score}  traits {tc}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv)>1 else "watch"
    force = "--force" in sys.argv
    if cmd == "watch": cmd_watch()
    elif cmd == "compute": cmd_compute(force=force)
    elif cmd == "my-holdings": cmd_holdings()
    else: print(__doc__)
