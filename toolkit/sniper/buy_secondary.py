#!/usr/bin/env python3
"""
buy_secondary.py — snap-buy an NFT off OpenSea secondary on Robinhood Chain.

Dry-run by default (never spends). --live broadcasts.

Usage:
  python3 buy_secondary.py <collection_slug>
  python3 buy_secondary.py <collection_slug> --target-eth 0.001
  python3 buy_secondary.py <collection_slug> --live          # approval REQUIRED first

Layered on the know-how in ~/Projects/bunker-snipe/encode_test.py + autoflip.py.
"""
import json, sys, os, time, urllib.request, argparse

import eth_account
from eth_abi import encode as abi_encode
from eth_utils import to_checksum_address
from Crypto.Hash import keccak

BASE = "https://api.opensea.io/api/v2"
RW = "https://rpc.mainnet.chain.robinhood.com"
CHAIN_ID = 4663
PROTOCOL = "0x0000000000000068f116a894984e2db1123eb395"  # Seaport 1.6 on RH
KEYFILE = os.path.expanduser("~/.hermes/secrets/opensea_key")
WALLET_KEY = os.path.expanduser("~/.hermes/secrets/bot_wallet_key")
BUYER_PC = "0x1111111111111111111111111111111111111111"
GAS = 400000


def api_key():
    with open(KEYFILE) as f:
        return f.read().strip()


def sel(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode())
    return "0x" + k.hexdigest()[:8]


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
        headers={"accept": "application/json", "content-type": "application/json",
                 "X-API-KEY": api_key(), "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def get(url):
    req = urllib.request.Request(url, headers={
        "accept": "application/json", "X-API-KEY": api_key(),
        "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(RW, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def wei_to_eth(w):
    return int(w) / 1e18


def buyer_balance():
    b = rpc("eth_getBalance", [BUYER_PC, "latest"])["result"]
    return int(b, 16) / 1e18


def chain_ok():
    return int(rpc("eth_chainId", [])["result"], 16) == CHAIN_ID


# --- Seaport fulfillAdvancedOrder encoding (from bunker-snipe/encode_test.py) ---
ORDER_PARAMS = ("(address,address,(uint8,address,uint256,uint256,uint256)[],"
                "(uint8,address,uint256,uint256,uint256,address)[],uint8,"
                "uint256,uint256,bytes32,uint256,bytes32,uint256)")
ADV_ORDER = f"({ORDER_PARAMS},uint120,uint120,bytes,bytes)"
CRITERIA_RESOLVER = "(uint256,uint8,uint256,uint256,bytes32[])"
FUNC_TYPES = [ADV_ORDER, f"{CRITERIA_RESOLVER}[]", "bytes32", "address"]


def build_advanced_order(idat):
    ao = idat["advancedOrder"]
    p = ao["parameters"]
    order_params = [
        p["offerer"], p["zone"],
        [[int(i["itemType"]), i["token"], int(i["identifierOrCriteria"]),
          int(i["startAmount"]), int(i["endAmount"])] for i in p["offer"]],
        [[int(i["itemType"]), i["token"], int(i["identifierOrCriteria"]),
          int(i["startAmount"]), int(i["endAmount"]), i["recipient"]]
         for i in p["consideration"]],
        int(p["orderType"]), int(p["startTime"]), int(p["endTime"]),
        bytes.fromhex(p["zoneHash"][2:]), int(p["salt"]),
        bytes.fromhex(p["conduitKey"][2:]), int(p["totalOriginalConsiderationItems"]),
    ]
    return [order_params, int(ao["numerator"]), int(ao["denominator"]),
            bytes.fromhex(ao["signature"][2:]), bytes.fromhex(ao["extraData"][2:])]


def build_args(idat):
    resolvers = []
    for cr in idat.get("criteriaResolvers") or []:
        resolvers.append([int(cr["orderIndex"]), int(cr["side"]), int(cr["index"]),
                          int(cr["identifier"]),
                          [bytes.fromhex(x[2:]) for x in cr["criteriaProof"]]])
    conduit = bytes.fromhex(idat["fulfillerConduitKey"][2:])
    return build_advanced_order(idat), resolvers, conduit, idat["recipient"]


# Basic order (the format cheap floor listings use): flat parameters struct.
BASIC_TUPLE = ("(address,uint256,uint256,address,address,address,uint256,uint256,"
               "uint8,uint256,uint256,bytes32,uint256,bytes32,bytes32,uint256,"
               "(uint256,address)[],bytes)")


def build_basic_params(idat):
    p = idat["parameters"]
    return [
        p["considerationToken"], int(p["considerationIdentifier"]),
        int(p["considerationAmount"]), p["offerer"], p["zone"], p["offerToken"],
        int(p["offerIdentifier"]), int(p["offerAmount"]), int(p["basicOrderType"]),
        int(p["startTime"]), int(p["endTime"]), bytes.fromhex(p["zoneHash"][2:]),
        int(p["salt"]), bytes.fromhex(p["offererConduitKey"][2:]),
        bytes.fromhex(p["fulfillerConduitKey"][2:]),
        int(p["totalOriginalAdditionalRecipients"]),
        [[int(r["amount"]), r["recipient"]] for r in p["additionalRecipients"]],
        bytes.fromhex(p["signature"][2:]),
    ]


def encode_fill(tx):
    """Encode a fulfillment transaction -> raw calldata. Handles both the
    basic-order format (flat `parameters`) and the advanced-order format
    (`advancedOrder`). Selector = keccak of tx['function'] (NOT calldata_suffix)."""
    idat = tx["input_data"]
    fn = tx["function"]
    if isinstance(idat, dict) and "parameters" in idat and "advancedOrder" not in idat:
        enc = abi_encode([BASIC_TUPLE], [build_basic_params(idat)])
    else:
        args = build_args(idat)
        enc = abi_encode(FUNC_TYPES, args)
    return sel(fn) + enc.hex()


def dry_run(calldata, value_hex):
    try:
        res = rpc("eth_call", [{"from": BUYER_PC, "to": PROTOCOL,
                                "data": calldata, "value": value_hex}, "latest"])
        r = res.get("result")
        if r and r != "0x":
            print("DRY-RUN: SUCCESS (fill would execute)")
            return True
        print("DRY-RUN: reverted or empty —", r)
        return False
    except Exception as e:
        print("DRY-RUN: error:", e)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--target-eth", type=float, default=None)
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()

    if not chain_ok():
        print("FATAL: RPC not RH chain"); sys.exit(1)

    stats = get(f"{BASE}/collections/{a.slug}/stats")
    floor = stats.get("total", {}).get("floor_price")
    print(f"collection: {a.slug} | floor: {floor} ETH")
    print(f"buyer {BUYER_PC[:10]}… balance: {buyer_balance():.6f} ETH")

    listings = get(f"{BASE}/listings/collection/{a.slug}/best?limit=5").get("listings", [])
    if not listings:
        print("no active listings found via /best for this RH collection.")
        sys.exit(0)

    cand = None
    for li in listings:
        cur = li.get("price", {}).get("current", {}).get("value")
        if cur is None:
            continue
        eth = int(cur) / 1e18
        if a.target_eth and eth > a.target_eth:
            print(f"  skip {eth:.4f} > target {a.target_eth}")
            continue
        cand = li
        print(f"  CANDIDATE {eth:.4f} ETH | maker {li.get('maker',{}).get('address','')[:10]} | hash {li.get('order_hash','')[:16]}")
        break

    if not cand:
        print("no listing within budget/target"); sys.exit(0)

    order_hash = cand["order_hash"]
    acct = eth_account.Account.from_key(open(WALLET_KEY).read().strip())
    fdata = post(f"{BASE}/listings/fulfillment_data",
                 {"listing": {"hash": order_hash, "chain": "robinhood",
                              "protocol_address": PROTOCOL},
                  "fulfiller": {"address": BUYER_PC}})
    tx = fdata["fulfillment_data"]["transaction"]
    calldata = encode_fill(tx)
    value_hex = tx.get("value_hex")

    print("encoded calldata len:", len(calldata) // 2, " bytes")
    ok = dry_run(calldata, value_hex)

    if not a.live:
        print("DRY RUN — pass --live (after approval) to broadcast.")
        print(f"saved /tmp/secondary_buy.json")
        json.dump({"calldata": calldata, "value_hex": value_hex, "to": tx.get("to"),
                   "order_hash": order_hash, "dry_ok": ok},
                  open("/tmp/secondary_buy.json", "w"))
        return

    if not ok:
        print("ABORT: dry-run failed — not broadcasting."); sys.exit(1)

    acct = eth_account.Account.from_key(open(WALLET_KEY).read().strip())
    nonce = int(rpc("eth_getTransactionCount", [BUYER_PC, "latest"])["result"], 16)
    gp = int(rpc("eth_gasPrice", [])["result"], 16)
    t = {"from": BUYER_PC, "to": to_checksum_address(tx["to"]), "data": calldata,
         "value": value_hex or "0x0", "nonce": hex(nonce),
         "gasPrice": hex(gp), "gas": hex(GAS)}
    s = acct.sign_transaction(t)
    res = rpc("eth_sendRawTransaction", ["0x" + s.raw_transaction.hex()])
    print("broadcast:", res.get("result", res))


if __name__ == "__main__":
    main()
