#!/usr/bin/env python3
"""hashcats.py — round watcher, exact verifier and mint broadcaster for Hashcats (RH chain 4663).

workHash(miner,nonce,prev,anchor) = keccak256(monitor||nonce||prev||anchor), accept iff < target.
Verified 2026-09-11 against 446 real Mined events (100% exact hash reproduction).

CLI:
  state                       print the live round (prev, anchor, target, price, pace)
  sim <nonce>                 eth_call mine(nonce,anchorBlock) with the CURRENT round -> expect
                              execution-reverted BadSolution (proves ABI + validation plumbing)
  solve <seconds>             run the local CPU miner against the live round, verify, print nonce
  send <nonce> <anchorBlock>  broadcast (DRY by default; --send to actually broadcast)
  loop                        watch rounds, mine locally, auto-verify (never broadcasts unless --send)
"""
import json, os, subprocess, sys, time
from Crypto.Hash import keccak as _k

RPC_FALLBACKS = ["https://rpc.mainnet.chain.robinhood.com", "https://robinhood.drpc.org"]
COLLECTION = "0xCA75DF55Cc9C476DB27a7375D1fc8E794cf80721"
CHAIN_ID = 4663
HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def keccak256(b: bytes) -> bytes:
    h = _k.new(digest_bits=256); h.update(b); return h.digest()


def sel(sig: str) -> str:
    return "0x" + keccak256(sig.encode()).hex()[:8]


def enc(*args) -> str:
    return "".join(hex(int(a))[2:].rjust(64, "0") for a in args)


_rpc_url = RPC_FALLBACKS[0]


def rpc(method, params, timeout=30):
    """Multi-endpoint RPC with 429/5xx backoff. The RH RPC throttles hard under load."""
    global _rpc_url
    import urllib.request, urllib.error, time as _t
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    urls = [_rpc_url] + [u for u in RPC_FALLBACKS if u != _rpc_url]
    last = None
    for attempt in range(3):
        for url in urls:
            try:
                req = urllib.request.Request(url, data=body, headers={"content-type": "application/json", "user-agent": UA})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    out = json.load(r)
                _rpc_url = url
                if "error" in out:
                    return out
                return out["result"]
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 502, 503, 504):
                    _t.sleep(0.6 * (attempt + 1))
                    continue
                raise
            except Exception as e:
                last = e
                continue
        _t.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"all RPCs failed: {last}")


def call(sig, args=(), to=COLLECTION):
    return rpc("eth_call", [{"to": to, "data": sel(sig) + enc(*args)}, "latest"])


def u(x):
    return int(x, 16) if x and x != "0x" else None


def bits_of(v):
    return None if v is None else 256 - v.bit_length()


def state(miner=None):
    """Live round state. prevWork/anchor/target are what a miner must hash against."""
    anchor_raw = call("currentAnchor()")
    a = anchor_raw[2:]
    st = {
        "block": int(rpc("eth_blockNumber", []), 16),
        "totalMinted": u(call("totalMinted()")),
        "mintPrice": u(call("mintPrice()")),
        "prevWork": u(call("prevWork()")),
        "target": u(call("targetFor(address)", (int(miner, 16),))) if miner else u(call("currentTarget()")),
        "currentTarget": u(call("currentTarget()")),
        "baseTarget": u(call("baseTarget()")),
        "currentEpoch": u(call("currentEpoch()")),
        "anchorBlock": int(a[0:64], 16),
        "anchor": "0x" + a[64:128],
        "lastMintBlock": u(call("lastMintBlock()")),
        "lastMintTime": u(call("lastMintTime()")),
        "myBurst": u(call("personalBurst(address)", (int(miner, 16),))) if miner else None,
    }
    st["targetBits"] = bits_of(st["target"])
    return st


def work_hash(miner_hex, nonce, prev, anchor_hex):
    m = bytes.fromhex(miner_hex.lower().replace("0x", ""))
    assert len(m) == 20
    pre = m + int(nonce).to_bytes(32, "big") + int(prev).to_bytes(32, "big") + bytes.fromhex(anchor_hex.replace("0x", ""))
    assert len(pre) == 116, len(pre)
    return int.from_bytes(keccak256(pre), "big")


def verify(miner_hex, nonce, prev, anchor_hex, target):
    h = work_hash(miner_hex, nonce, prev, anchor_hex)
    return h, h < int(target)


def local_mine(miner_hex, prev, anchor_hex, target, seconds=60, threads=8):
    """Run the verified CPU miner for one round. Returns (nonce, hash) or (None, None)."""
    tgt = hex(int(target))[2:].rjust(64, "0")
    p = subprocess.run([os.path.join(HERE, "hcminer"), "mine", miner_hex,
                        hex(int(prev))[2:].rjust(64, "0"), anchor_hex, tgt, str(threads), str(seconds)],
                       capture_output=True, text=True, timeout=seconds + 60)
    if "nonce=0x" in p.stdout:
        nz = p.stdout.split("nonce=0x")[1].split()[0]
        n = int(nz, 16)
        h, ok = verify(miner_hex, n, prev, anchor_hex, target)
        return (n, h) if ok else (None, None)
    return (None, None)


def build_tx(key_hex, nonce, anchor_block, value_wei, gas=None):
    from eth_account import Account
    acct = Account.from_key(key_hex)
    txcount = int(rpc("eth_getTransactionCount", [acct.address, "latest"]), 16)
    data = sel("mine(uint256,uint256)") + enc(nonce, anchor_block)
    if gas is None:
        est = rpc("eth_estimateGas", [{"from": acct.address, "to": COLLECTION, "data": data,
                                       "value": hex(int(value_wei))}])
        gas = int(est, 16) * 125 // 100 if isinstance(est, str) else 400000
    base = int(rpc("eth_getBlockByNumber", ["latest", False])["baseFeePerGas"], 16)
    tip = int(rpc("eth_maxPriorityFeePerGas", []) or "0x1", 16)
    tx = {"type": 2, "chainId": CHAIN_ID, "nonce": txcount, "to": COLLECTION,
          "value": int(value_wei), "gas": gas,
          "maxFeePerGas": base * 2 + max(tip, 10**9), "maxPriorityFeePerGas": max(tip, 10**9), "data": data}
    signed = Account.from_key(key_hex).sign_transaction(tx)
    return tx, signed.raw_transaction.hex()


def simulate(key_hex, nonce, anchor_block):
    from eth_account import Account
    acct = Account.from_key(key_hex)
    data = sel("mine(uint256,uint256)") + enc(nonce, anchor_block)
    price = u(call("mintPrice()"))
    res = rpc("eth_call", [{"from": acct.address, "to": COLLECTION, "data": data, "value": hex(price)}, "latest"])
    return res


def read_key(path):
    return open(os.path.expanduser(path)).read().strip().replace("0x", "").split()[0]


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return 1
    cmd = args[0]
    keypath = "~/.hermes/secrets/bot_wallet_key"
    miner_hex = None
    if "0x" in " ".join(args):
        for a in args:
            if a.startswith("0x") and len(a) == 42:
                miner_hex = a
    if os.path.exists(os.path.expanduser(keypath)):
        from eth_account import Account
        miner_hex = miner_hex or Account.from_key(read_key(keypath)).address

    if cmd == "state":
        st = state(miner_hex)
        for k, v in st.items():
            if k in ("target", "currentTarget", "baseTarget", "prevWork") and isinstance(v, int):
                print(f"{k:16} {v}  bits={bits_of(v)}")
            else:
                print(f"{k:16} {v}")
        return 0

    if cmd == "sim":
        nonce = int(args[1], 0) if len(args) > 1 else 0
        st = state(miner_hex)
        print("round:", st["anchorBlock"], st["anchor"], "prevBits", bits_of(st["prevWork"]))
        print("eth_call mine(nonce=0x%x, anchorBlock=%d) ->" % (nonce, st["anchorBlock"]))
        print(json.dumps(simulate(read_key(keypath), nonce, st["anchorBlock"]), indent=1))
        return 0

    if cmd == "solve":
        secs = int(args[1]) if len(args) > 1 and args[1].isdigit() else 60
        st = state(miner_hex)
        print(f"round block={st['block']} anchorBlock={st['anchorBlock']} targetBits={st['targetBits']}")
        n, h = local_mine(miner_hex, st["prevWork"], st["anchor"], st["target"], secs)
        if n is None:
            print("no solution in window (expected on CPU)")
            return 3
        print("SOLVED nonce=0x%064x" % n)
        print("hash      0x%064x" % h)
        print("target    0x%064x" % st["target"])
        print("anchorBlock", st["anchorBlock"])
        return 0

    if cmd == "send":
        nonce = int(args[1], 0); anchor_block = int(args[2], 0)
        do_send = "--send" in args
        st = state(miner_hex)
        price = u(call("mintPrice()"))
        h, ok = verify(miner_hex, nonce, st["prevWork"], st["anchor"], st["target"])
        print(f"verify vs LIVE round: hash=0x{h:064x} below={ok} (prev may have moved)")
        tx, raw = build_tx(read_key(keypath), nonce, anchor_block, price)
        print(json.dumps({k: (hex(v) if isinstance(v, int) else v) for k, v in tx.items()}, indent=1))
        if not do_send:
            print("DRY RUN (pass --send)")
            return 0
        if not raw.startswith("0x"):
            raw = "0x" + raw
        print(json.dumps(rpc("eth_sendRawTransaction", [raw]), indent=1))
        return 0

    if cmd == "loop":
        do_send = "--send" in args
        secs = 900
        end = time.time() + secs
        rounds = 0
        while time.time() < end:
            try:
                st = state(miner_hex)
            except Exception as e:
                print("rpc error", e); time.sleep(2); continue
            rounds += 1
            print(f"[{time.strftime('%H:%M:%S')}] round {rounds} anchor={st['anchorBlock']} "
                  f"prevBits={bits_of(st['prevWork'])} targetBits={st['targetBits']} "
                  f"minted={st['totalMinted']} price={st['mintPrice']/1e18:.6f}")
            n, h = local_mine(miner_hex, st["prevWork"], st["anchor"], st["target"],
                              seconds=15, threads=8)
            if n is not None:
                print("SOLVED 0x%064x (hash 0x%064x)" % (n, h))
                if do_send:
                    tx, raw = build_tx(read_key(keypath), n, st["anchorBlock"], u(call("mintPrice()")))
                    res = rpc("eth_sendRawTransaction", ["0x" + raw.lstrip("0x")])
                    print("broadcast ->", json.dumps(res))
        return 0
    print("unknown command", cmd); return 1


if __name__ == "__main__":
    sys.exit(main())
