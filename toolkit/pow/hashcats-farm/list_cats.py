#!/usr/bin/env python3
"""list_cats.py — list (or price) mined Hashcats on OpenSea (Robinhood chain).

  python3 list_cats.py --check                 # owned cats + live floor, no signing
  python3 list_cats.py --list --undercut 0.03  # list every owned cat 3% under the live floor
  python3 list_cats.py --list --token 34 --price 0.11

Reuses the relist path proven in bunker-snipe/autoflip.py:
  POST /listings/actions  -> EIP-712 signatureRequest -> sign locally -> POST /orders/robinhood/seaport/listings
The private key never leaves this machine; only the signed order is posted.
"""
import argparse, json, os, sys, time, urllib.request

from eth_account import Account
from eth_account.messages import encode_typed_data

BASE = "https://api.opensea.io/api/v2"
RPC = "https://rpc.mainnet.chain.robinhood.com"
COLLECTION = "hash-cats"
CONTRACT = "0xCA75DF55Cc9C476DB27a7375D1fc8E794cf80721"
CHAIN = "robinhood"
KEYFILE = os.path.expanduser("~/.hermes/secrets/opensea_key")
WALLET_KEY = os.path.expanduser("~/.hermes/secrets/hashcats_miner_key")
UA = "Mozilla/5.0"


def api_key():
    return open(KEYFILE).read().strip()


def req(url, body=None):
    hdr = {"accept": "application/json", "X-API-KEY": api_key(), "User-Agent": UA}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        hdr["content-type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=hdr)
    with urllib.request.urlopen(r, timeout=45) as resp:
        return json.loads(resp.read())


def get(url):
    return req(url)


def post(url, body):
    return req(url, body)


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    r = urllib.request.Request(RPC, data=body, headers={"content-type": "application/json", "user-agent": UA})
    with urllib.request.urlopen(r, timeout=30) as resp:
        out = json.loads(resp.read())
    return out.get("result")


def owned(address):
    """Enumerate token ids held by `address` straight from the contract (Transfer logs)."""
    from Crypto.Hash import keccak
    h = keccak.new(digest_bits=256); h.update(b"Transfer(address,address,uint256)")
    topic = "0x" + h.hexdigest()
    head = int(rpc("eth_blockNumber", []), 16)
    owners = {}
    for start in range(head - 300000, head, 20000):
        end = min(start + 19999, head)
        logs = rpc("eth_getLogs", [{"address": CONTRACT, "topics": [topic], "fromBlock": hex(start), "toBlock": hex(end)}]) or []
        for L in logs:
            frm = "0x" + L["topics"][1][-40:]
            to = "0x" + L["topics"][2][-40:]
            tid = int(L["topics"][3], 16)
            owners[tid] = to
    return sorted(t for t, o in owners.items() if o.lower() == address.lower())


def floor():
    d = get(f"{BASE}/listings/collection/{COLLECTION}/best?limit=20")
    prices = []
    for x in d.get("listings", []):
        cur = (x.get("price") or {}).get("current") or {}
        v = cur.get("value")
        if v:
            prices.append(int(v) / 1e18)
    return (min(prices), sorted(prices)[:5]) if prices else (None, [])


def list_one(acct, token_id, price_eth):
    body = {"address": acct.address,
            "items": [{"chain": CHAIN, "contract": CONTRACT, "token_id": str(token_id), "quantity": 1,
                       "price": {"amount": f"{price_eth:.6f}",
                                 "currency": "0x0000000000000000000000000000000000000000"}}]}
    d = post(f"{BASE}/listings/actions", body)
    sr = d["steps"][0]["createListingsAction"]["signatureRequest"]
    m = json.loads(sr["message"])
    sig = acct.sign_message(encode_typed_data(full_message=m))
    order = {"parameters": m["message"], "protocol_address": m["domain"]["verifyingContract"],
             "signature": sig.signature.hex()}
    return post(f"{BASE}/orders/{CHAIN}/seaport/listings", order)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--token", type=int, default=None)
    ap.add_argument("--price", type=float, default=None, help="absolute ETH price; default = floor - undercut")
    ap.add_argument("--undercut", type=float, default=0.03)
    ap.add_argument("--key", default=WALLET_KEY)
    args = ap.parse_args()

    key = open(os.path.expanduser(args.key)).read().strip()
    acct = Account.from_key(key)
    fl, cheapest = floor()
    print(f"wallet   {acct.address}")
    print(f"floor    {fl} ETH  (cheapest listings: {cheapest})")
    cats = owned(acct.address)
    print(f"owned    {len(cats)} cats {cats[:20]}")
    if not args.list:
        return 0
    if not cats:
        print("nothing to list"); return 1
    targets = [args.token] if args.token else cats
    for t in targets:
        price = args.price if args.price else (fl * (1 - args.undercut) if fl else None)
        if not price:
            print("no floor reference; pass --price"); return 1
        try:
            out = list_one(acct, t, price)
            print(f"listed #{t} @ {price:.6f} ETH -> order {json.dumps(out)[:160]}")
        except Exception as e:
            print(f"list #{t} failed: {str(e)[:300]}")
        time.sleep(0.4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
