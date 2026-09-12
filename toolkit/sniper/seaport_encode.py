#!/usr/bin/env python3
"""ABI-encode OpenSea Seaport fulfillment_data into raw calldata.
Reads /tmp/fdtx.json (the `/listings/fulfillment_data` transaction object) and
emits the encoded calldata for the `fulfillAdvancedOrder` call. Test harness —
verifies encoding correct via eth_call dry-run (no spend).
"""
import json, os, sys
from eth_abi import encode

RW = "https://rpc.mainnet.chain.robinhood.com"
PROTOCOL = "0x0000000000000068f116a894984e2db1123eb395"

def rpc(method, params):
    import urllib.request
    body = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}).encode()
    req = urllib.request.Request(RW, data=body,
        headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# --- OpenSea input_data -> Seaport AdvancedOrder args ---
def split_tuple(t):
    """Remove outermost parentheses of a tuple type string; return joiner list."""
    # not needed; we build types structurally below
    pass

# Seaport ABI (v1.6) for the args. We encode as:
# fulfillAdvancedOrder(order, criteriaResolvers, fulfillerConduitKey, recipient)
# order = (OrderParameters, numerator, denominator, signature, extraData)
# OrderParameters = (offerer, zone, offer[], consideration[], orderType,
#                    startTime, endTime, zoneHash, salt, conduitKey,
#                    totalOriginalConsiderationItems)
# offer item = (itemType, token, identifierOrCriteria, startAmount, endAmount)
# consideration item = (itemType, token, identifierOrCriteria, startAmount,
#                       endAmount, recipient)
# criteriaResolver = (orderIndex, side, index, identifier, criteriaProof[])

ORDER_PARAMS = ("(address,address,(uint8,address,uint256,uint256,uint256)[],"
                "(uint8,address,uint256,uint256,uint256,address)[],uint8,"
                "uint256,uint256,bytes32,uint256,bytes32,uint256)")
ADV_ORDER = f"({ORDER_PARAMS},uint120,uint120,bytes,bytes)"
CRITERIA_RESOLVER = "(uint256,uint8,uint256,uint256,bytes32[])"
FUNC_TYPES = [ADV_ORDER, f"{CRITERIA_RESOLVER}[]", "bytes32", "address"]

def to_hexs(v, bits=32):
    return int(v).to_bytes(bits, "big").hex()

def build_advanced_order(idat):
    ao = idat["advancedOrder"]
    p = ao["parameters"]
    order_params = [
        p["offerer"],
        p["zone"],
        [[int(i["itemType"]), i["token"], int(i["identifierOrCriteria"]),
          int(i["startAmount"]), int(i["endAmount"])] for i in p["offer"]],
        [[int(i["itemType"]), i["token"], int(i["identifierOrCriteria"]),
          int(i["startAmount"]), int(i["endAmount"]), i["recipient"]]
         for i in p["consideration"]],
        int(p["orderType"]), int(p["startTime"]), int(p["endTime"]),
        bytes.fromhex(p["zoneHash"][2:]), int(p["salt"]),
        bytes.fromhex(p["conduitKey"][2:]), int(p["totalOriginalConsiderationItems"]),
    ]
    advanced = [
        order_params,
        int(ao["numerator"]), int(ao["denominator"]),
        bytes.fromhex(ao["signature"][2:]),
        bytes.fromhex(ao["extraData"][2:]),
    ]
    return advanced

def build_args(idat):
    advanced = build_advanced_order(idat)
    resolvers = []
    for cr in idat.get("criteriaResolvers") or []:
        resolvers.append([int(cr["orderIndex"]), int(cr["side"]), int(cr["index"]),
                          int(cr["identifier"]), [bytes.fromhex(x[2:]) for x in cr["criteriaProof"]]])
    conduit = bytes.fromhex(idat["fulfillerConduitKey"][2:])
    recipient = idat["recipient"]
    return advanced, resolvers, conduit, recipient

def main():
    tx = json.load(open("/tmp/fdtx.json"))
    idat = tx["input_data"]
    args = build_args(idat)
    # encode with a leading 32-byte offset frame structure? eth-abi handles it.
    enc = encode(FUNC_TYPES, args)
    selector = tx.get("calldata_suffix") or "0x"
    if not selector.startswith("0x"): selector = "0x" + selector
    # calldata_suffix appears to be the function selector
    calldata = selector + enc.hex()
    print("encoded calldata length:", len(calldata)//2)
    print("selector:", selector)
    print("calldata:", calldata[:120], "...")
    # dry-run via eth_call to verify it would execute (no broadcast)
    try:
        call = rpc("eth_call", [{"from": "0x1111111111111111111111111111111111111111",
                                "to": PROTOCOL, "data": calldata,
                                "value": tx.get("value_hex")}, "latest"])
        res = call.get("result")
        print("eth_call result:", ("SUCCESS" if res is not None and res else str(res)))
    except Exception as e:
        print("eth_call err:", e)
    json.dump({"calldata": calldata, "value_hex": tx.get("value_hex"),
               "to": tx.get("to")}, open("/tmp/encoded_tx.json","w"), default=str)
    print("saved /tmp/encoded_tx.json")

if __name__ == "__main__":
    main()
