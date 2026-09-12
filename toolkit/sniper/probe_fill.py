#!/usr/bin/env python3
"""Diagnose RH-chain Seaport fill: fetch fulfillment_data for a LIVE Clay StonKz
listing with full HTTP error bodies, encode, and eth_call dry-run to capture the
exact revert reason. No broadcast. Read-only."""
import json, sys, urllib.request, urllib.error
from eth_abi import encode as abi_encode
from Crypto.Hash import keccak

BASE = "https://api.opensea.io/api/v2"
RW = "https://rpc.mainnet.chain.robinhood.com"
PROTOCOL = "0x0000000000000068f116a894984e2db1123eb395"
CHAIN = "robinhood"
SLUG = "claystonkz"
WALLET = "0x1111111111111111111111111111111111111111"

def api_key():
    return open("~/.hermes/secrets/opensea_key").read().strip()

def req(url, method="GET", body=None):
    headers = {"accept": "application/json", "X-API-KEY": api_key(), "User-Agent": "Mozilla/5.0"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["content-type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: parsed = json.loads(raw)
        except Exception: parsed = raw[:500].decode(errors="replace")
        return e.code, parsed

def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    r = urllib.request.Request(RW, data=body, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read())

# --- 1. get best listings ---
st, d = req(f"{BASE}/listings/collection/{SLUG}/best?limit=5")
if st != 200:
    print("LISTINGS FAIL", st, str(d)[:300]); sys.exit(1)
listings = d.get("listings", [])
print(f"got {len(listings)} best listings")
if not listings:
    print("no active listings"); sys.exit(1)

# cheapest
order = min(listings, key=lambda x: int(x["price"]["current"]["value"]))
oh = order["order_hash"]
tid = order.get("asset", {}).get("identifier")
price = int(order["price"]["current"]["value"])
print(f"cheapest listing: token #{tid} @ {price/1e18:.6f} ETH order_hash={oh}")

# --- 2. fulfillment_data with FULL error capture ---
body = {"listing": {"hash": oh, "chain": CHAIN, "protocol_address": PROTOCOL},
        "fulfiller": {"address": WALLET}}
st, fd = req(f"{BASE}/listings/fulfillment_data", "POST", body)
print(f"fulfillment_data status={st}")
if st != 200:
    print("FULL ERROR BODY:", json.dumps(fd)[:1200] if not isinstance(fd, str) else fd[:1200])
    sys.exit(2)

fdata = fd["fulfillment_data"]
tx = fdata.get("transaction") or {}
idat = tx.get("input_data")
print("to:", tx.get("to"), "value:", tx.get("value"), "has input_data:", bool(idat))
if not idat:
    print("transaction keys:", list(tx.keys()))
    print(json.dumps(tx)[:800])
    sys.exit(3)

# --- 3. encode fulfillAdvancedOrder (same encoder as autoflip.py) ---
ORDER_PARAMS = ("(address,address,(uint8,address,uint256,uint256,uint256)[],"
                "(uint8,address,uint256,uint256,uint256,address)[],uint8,"
                "uint256,uint256,bytes32,uint256,bytes32,uint256)")
ADV_ORDER = f"({ORDER_PARAMS},uint120,uint120,bytes,bytes)"
CRITERIA_RESOLVER = "(uint256,uint8,uint256,uint256,bytes32[])"
FUNC_TYPES = [ADV_ORDER, f"{CRITERIA_RESOLVER}[]", "bytes32", "address"]

def sel(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode())
    return "0x" + k.hexdigest()[:8]

ao = idat["advancedOrder"]; p = ao["parameters"]
adv = [
    [p["offerer"], p["zone"],
     [[int(i["itemType"]), i["token"], int(i["identifierOrCriteria"]),
       int(i["startAmount"]), int(i["endAmount"])] for i in p["offer"]],
     [[int(i["itemType"]), i["token"], int(i["identifierOrCriteria"]),
       int(i["startAmount"]), int(i["endAmount"]), i["recipient"]]
      for i in p["consideration"]],
     int(p["orderType"]), int(p["startTime"]), int(p["endTime"]),
     bytes.fromhex(p["zoneHash"][2:]), int(p["salt"]),
     bytes.fromhex(p["conduitKey"][2:]), int(p["totalOriginalConsiderationItems"])],
    int(ao["numerator"]), int(ao["denominator"]),
    bytes.fromhex(ao["signature"][2:]), bytes.fromhex(ao["extraData"][2:]),
]
resolvers = []
for cr in idat.get("criteriaResolvers") or []:
    resolvers.append([int(cr["orderIndex"]), int(cr["side"]), int(cr["index"]),
                      int(cr["identifier"]), [bytes.fromhex(x[2:]) for x in cr["criteriaProof"]]])
conduit = bytes.fromhex(idat["fulfillerConduitKey"][2:])
recipient = idat["recipient"]
enc = abi_encode(FUNC_TYPES, [adv, resolvers, conduit, recipient])

fn = tx.get("function") or ""
calldata = (sel(fn) if fn else "0xcc5eb2ce") + enc.hex()  # cc5eb2ce = fulfillAdvancedOrder fallback selector? verify below
# compute canonical selector for fulfillAdvancedOrder((...),(...)[],bytes32,address)
k = keccak.new(digest_bits=256)
sig_str = "fulfillAdvancedOrder(((address,address,(uint8,address,uint256,uint256,uint256)[],(uint8,address,uint256,uint256,uint256,address)[],uint8,uint256,uint256,bytes32,uint256,bytes32,uint256),uint120,uint120,bytes,bytes),(uint256,uint8,uint256,uint256,bytes32[])[],bytes32,address)"
k.update(sig_str.encode())
canon = "0x" + k.hexdigest()[:8]
print("function field from OS:", repr(fn))
print("canonical fulfillAdvancedOrder selector:", canon)

# --- 4. eth_call dry-run to Seaport on RH chain ---
call_obj = {"from": WALLET, "to": tx.get("to"), "data": calldata,
            "value": hex(int(tx.get("value") or 0))}
res = rpc("eth_call", [call_obj, "latest"])
if "result" in res:
    print("ETH_CALL SUCCESS — would fill cleanly. result:", (res["result"] or "0x")[:80])
else:
    err = res.get("error", {})
    print("ETH_CALL REVERT:", err.get("message"))
    rd = err.get("data")
    if isinstance(rd, str) and len(rd) >= 10:
        print("revert data head:", rd[:74])
        # known seaport selectors
        sels = {
            "0x2c706ec9": "InvalidTime/found?",
            "0x08c379a0": "Error(string)",
            "0x1a25720e": "NoSpecifiedOrdersAvailable",
            "0x4d90cf1e": "OrderAlreadyFilledOrCancelled",
            "0x88bb7779": "Unreachable",
            "0xb4639d54": "MismatchedOrderOrigination",
            "0x29f4bdf8": "InvalidRestrictedOrder (restricted zone rejected)",
            "0xd0d3bea3": "BadSignature",
            "0x815e1e64": "InvalidSigner",
        }
        print("selector match guess:", sels.get(rd[:10], "unknown"))
json.dump({"order_hash": oh, "token_id": tid, "price_wei": price}, open("/tmp/snipe_probe.json", "w"))
print("saved /tmp/snipe_probe.json")