#!/usr/bin/env python3
"""Broadcast a FAB-4200-style mint(nonce) tx, value=0, signed locally. VERIFIED 2026-08-21.

Usage: send_mint_tx.py <keyfile> <nonce> [--send]
  Without --send: dry-run (derives address, estimates gas, prints cost).
  eth_estimateGas reverting with data 0xfcf9306400…00NN = BelowFloor(got=0, need=0xNN)
  — that CONFIRMS the plumbing works and shows live difficulty in one call.

Requires: pip install eth-account coincurve pycryptodome
"""
import sys, json, subprocess

RPC = "https://rpc.mainnet.chain.robinhood.com"   # Robinhood Chain, chainid 4663
CONTRACT = "EF08089e4E082071AA39Ce99C460c0250744d758"  # FAB4200
SELECTOR = "a0712d68"                             # mint(uint256)
CHAIN_ID = 4663

def rpc(method, params):
    req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    out = subprocess.run(["curl", "-s", RPC, "-X", "POST",
                          "-H", "Content-Type: application/json", "--data", req],
                         capture_output=True, text=True)
    return json.loads(out.stdout)

def main():
    keyfile, nonce = sys.argv[1], int(sys.argv[2], 0)
    send = "--send" in sys.argv
    from coincurve import PrivateKey
    from Crypto.Hash import keccak as _k
    key = bytes.fromhex(open(keyfile).read().strip().replace("0x", ""))
    pk = PrivateKey(key)
    pub = pk.public_key.format(compressed=False)[1:]
    h = _k.new(digest_bits=256); h.update(pub)
    from_addr = "0x" + h.digest()[-20:].hex()

    base = int(rpc("eth_getBlockByNumber", ["latest", False])["result"]["baseFeePerGas"], 16)
    max_fee = base * 2 + 10**9
    tip_resp = rpc("eth_maxPriorityFeePerGas", [])
    max_tip = max(10**9, int(tip_resp.get("result", "0x1"), 16))
    txcount = int(rpc("eth_getTransactionCount", [from_addr, "latest"])["result"], 16)
    est = rpc("eth_estimateGas", [{"from": from_addr, "to": "0x"+CONTRACT,
                                   "data": "0x"+SELECTOR+format(nonce, "064x"), "value": "0x0"}])
    if "error" in est:
        print("ESTIMATE FAILED (mint would revert?):", est["error"]); sys.exit(2)
    gas = int(est["result"], 16)

    print(f"from {from_addr} nonce {txcount} gas {gas}")
    print(f"baseFee {base/1e9:.3f} gwei maxFee {max_fee/1e9:.3f} maxCost {gas*max_fee/1e18:.9f} ETH")

    if not send:
        print("DRY RUN — pass --send to broadcast"); return

    from eth_account import Account
    acct = Account.from_key(key)
    assert acct.address.lower() == from_addr.lower()
    tx = {"type": 2, "chainId": CHAIN_ID, "nonce": txcount,
          "to": "0x"+CONTRACT, "value": 0, "gas": gas + 20000,
          "maxFeePerGas": max_fee, "maxPriorityFeePerGas": max_tip,
          "data": "0x"+SELECTOR+format(nonce, "064x")}
    raw = acct.sign_transaction(tx).raw_transaction.hex()
    if not raw.startswith("0x"): raw = "0x"+raw
    print(json.dumps(rpc("eth_sendRawTransaction", [raw]), indent=1))

if __name__ == "__main__":
    main()
