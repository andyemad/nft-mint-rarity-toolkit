#!/usr/bin/env python3
"""NFT minter legitimacy audit. Usage: minter_legitimacy.py <contract_address> <deploy_block>
Scans all Transfer logs from deploy to head (RH chain), classifies mints vs secondary,
reports recipient/submitter concentration, payment mix by actual tx.value, and wash-ring tells.
Verified 2026-08-24 on Terminal Kids (Robinhood). Run in background for large spans."""
import json, urllib.request, time, collections, sys

RPC = "https://rpc.mainnet.chain.robinhood.com"
BASE = "https://robinhoodchain.blockscout.com/api/v2"
TransferTopic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

def rpc(method, params, ntr=5):
    for a in range(ntr):
        try:
            req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
                                         headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=25).read())["result"]
        except Exception:
            time.sleep(1.2*a)
    return None

def get(url):
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=25).read())
        except Exception:
            time.sleep(1.0*a)
    return None

def main():
    CA = sys.argv[1].lower()
    DEPLOY = int(sys.argv[2])
    Z = "0"*64
    head = int(rpc("eth_blockNumber",[]),16)
    print(f"head={head} deploy={DEPLOY} span={head-DEPLOY} blocks", flush=True)

    mints=[]; transfers=[]
    fromblk=DEPLOY; CH=1000
    while fromblk<=head:
        toblk=min(fromblk+CH-1,head)
        lg = rpc("eth_getLogs",[{"fromBlock":hex(fromblk),"toBlock":hex(toblk),"address":CA,"topics":[TransferTopic]}])
        if lg:
            for e in lg:
                frm="0x"+e["topics"][1][-40:]; to="0x"+e["topics"][2][-40:]
                tok=int(e["topics"][3],16); h=e["transactionHash"]
                if frm=="0x"+"0"*40:
                    mints.append((int(e["blockNumber"],16),to,tok,h))
                else:
                    transfers.append((int(e["blockNumber"],16),frm,to,tok,h))
        fromblk=toblk+1
    print(f"mint_events={len(mints)} secondary_transfers={len(transfers)}", flush=True)
    json.dump({"mints":[[m[0],m[1],m[2],m[3]] for m in mints],
               "transfers":[[t[0],t[1],t[2],t[3],t[4]] for t in transfers]},
              open("/tmp/mf_mints.json","w"))

    recip=collections.Counter(a[1] for a in mints)
    print(f"\n=== MINT RECIPIENTS ===\nunique={len(recip)} total={len(mints)}")
    for w,c in recip.most_common(20): print(f"  {w} {c}")

    mint_txs=list(dict.fromkeys(a[3] for a in mints))
    vals={}
    for i in range(0,len(mint_txs),20):
        batch=mint_txs[i:i+20]
        body=[{"jsonrpc":"2.0","id":k,"method":"eth_getTransactionByHash","params":[t]} for k,t in enumerate(batch)]
        try:
            req=urllib.request.Request(RPC,data=json.dumps(body).encode(),headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
            res=json.loads(urllib.request.urlopen(req,timeout=25).read())
            for rr in res:
                if rr and "result" in rr and rr["result"]:
                    vals[rr["result"]["hash"].lower()]=rr["result"]
        except Exception: pass
        time.sleep(0.4)

    pay=collections.Counter(); submitters=collections.Counter()
    for h,tx in vals.items():
        pay[int(tx["value"],16)]+=1
        submitters[tx["from"].lower()]+=1
    print("\n=== PAYMENT BY ACTUAL TX VALUE ===")
    for v,c in sorted(pay.items(),reverse=True):
        print(f"  value={v} ({v/1e18:.6f} ETH) count={c}")
    print(f"mint_tx_hashes={len(mint_txs)} resolved={len(vals)} unique_submitters={len(submitters)}")
    for w,c in submitters.most_common(15): print(f"  SUB {w} {c}")

    ft=collections.Counter(a[1] for a in transfers); tt=collections.Counter(a[2] for a in transfers)
    txh=collections.Counter(a[4] for a in transfers)
    both=set(ft)&set(tt)
    print(f"\n=== SECONDARY ===\nsellers={len(ft)} buyers={len(tt)} txs={len(txh)} transfers={len(transfers)} both_buy+sell={len(both)}")
    for w in list(both)[:15]: print(f"  BOTH {w} sold={ft[w]} bought={tt[w]}")
    print("packed txs (transfer_count>1):")
    for h,c in txh.most_common(15):
        if c>1: print(f"  {h} {c}")

    gross=sum(v*c for v,c in pay.items())
    print(f"\nGROSS MINT TAKE: {gross/1e18:.4f} ETH across {len(mint_txs)} mint txs")
    json.dump({"recip":dict(recip),"pay":{str(k):v for k,v in pay.items()},"submitters":dict(submitters),
               "both":list(both),"txpack":dict(txh.most_common(20))}, open("/tmp/mf_forensics.json","w"))
    print("DONE")

if __name__=="__main__":
    main()
