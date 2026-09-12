#!/usr/bin/env python3
"""sweep_back.py — send the miner wallet's full balance back to its verified funder.

Usage: python3 sweep_back.py [--send]
Reads the key locally, signs locally, broadcasts via the Robinhood Chain RPC.
Never writes the key anywhere.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashcats as hc

MINER = "0x4444444444444444444444444444444444444444"
DEST = "0x3333333333333333333333333333333333333333"
KEY = "~/.hermes/secrets/hashcats_miner_key"
GAS = 21000


def main():
    do_send = "--send" in sys.argv
    key = hc.read_key(KEY)
    from eth_account import Account
    acct = Account.from_key(key)
    assert acct.address.lower() == MINER.lower(), f"key is for {acct.address}, not {MINER}"

    bal = int(hc.rpc("eth_getBalance", [MINER, "latest"]), 16)
    nonce = int(hc.rpc("eth_getTransactionCount", [MINER, "latest"]), 16)
    blk = hc.rpc("eth_getBlockByNumber", ["latest", False])
    base = int(blk["baseFeePerGas"], 16)
    try:
        tip = int(hc.rpc("eth_maxPriorityFeePerGas", []) or "0x0", 16)
    except Exception:
        tip = 0
    maxfee = int(base * 1.5) + 50_000_000          # base*1.5 + 0.05 gwei
    value = bal - GAS * maxfee
    print(f"balance   {bal/1e18:.9f} ETH")
    print(f"nonce     {nonce}")
    print(f"baseFee   {base/1e9:.6f} gwei | maxFee {maxfee/1e9:.6f} gwei | worst-case gas {GAS*maxfee/1e18:.9f} ETH")
    print(f"SEND      {value/1e18:.9f} ETH -> {DEST}")
    if value <= 0:
        print("nothing to send"); return 1
    if not do_send:
        print("DRY RUN (pass --send)"); return 0

    tx = {"type": 2, "chainId": hc.CHAIN_ID, "nonce": nonce, "to": DEST, "value": value,
          "gas": GAS, "maxFeePerGas": maxfee, "maxPriorityFeePerGas": max(tip, 0)}
    signed = acct.sign_transaction(tx)
    raw = signed.raw_transaction.hex()
    raw = raw if raw.startswith("0x") else "0x" + raw
    res = hc.rpc("eth_sendRawTransaction", [raw])
    print("BROADCAST ->", res if isinstance(res, str) else json.dumps(res))
    if not isinstance(res, str):
        return 2
    for _ in range(60):
        time.sleep(2)
        try:
            rc = hc.rpc("eth_getTransactionReceipt", [res])
        except Exception:
            rc = None
        if rc:
            print("RECEIPT status=", rc.get("status"), "block=", int(rc["blockNumber"], 16),
                  "gasUsed=", int(rc["gasUsed"], 16))
            break
    bal2 = int(hc.rpc("eth_getBalance", [MINER, "latest"]), 16)
    bald = int(hc.rpc("eth_getBalance", [DEST, "latest"]), 16)
    print(f"miner balance now {bal2/1e18:.9f} ETH")
    print(f"dest  balance now {bald/1e18:.9f} ETH")
    return 0


if __name__ == "__main__":
    sys.exit(main())
