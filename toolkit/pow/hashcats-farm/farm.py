#!/usr/bin/env python3
"""farm.py — Hashcats farm: N Modal H100 shards, local signing + broadcast, full audit log.

  python3 farm.py --shards 8 --minutes 30 [--key ~/.hermes/secrets/bot_wallet_key] [--dry]

Every solution is verified with the independent Python keccak reference BEFORE broadcast, and
re-checked against the live round (prev/anchor must still match) so we never pay for a dead tx.
Logs to farm.log + solutions.json.
"""
import argparse, json, os, queue, threading, time
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import hashcats as hc          # noqa: E402
import hashcats_modal as hm    # noqa: E402


def addr_of(key_hex):
    from eth_account import Account
    return Account.from_key(key_hex).address


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", type=int, default=4)
    ap.add_argument("--minutes", type=float, default=30)
    ap.add_argument("--key", default="~/.hermes/secrets/bot_wallet_key")
    ap.add_argument("--dry", action="store_true", help="verify + simulate, never broadcast")
    ap.add_argument("--window", type=int, default=900, help="seconds a shard mines before returning")
    ap.add_argument("--max-mints", type=int, default=99, help="stop after this many successful mints")
    ap.add_argument("--slice", type=int, default=13, help="seconds per mining slice inside a shard")
    args = ap.parse_args()

    key = hc.read_key(args.key)
    miner = addr_of(key)
    logf = open(os.path.join(HERE, "farm.log"), "a")
    solf = open(os.path.join(HERE, "solutions.json"), "a")

    def log(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        logf.write(line + "\n"); logf.flush()

    q = queue.Queue()
    stop = threading.Event()

    def shard_worker(sid):
        while not stop.is_set():
            try:
                r = hm.mine_one.remote(miner, args.window, args.slice, sid)
            except Exception as e:
                q.put(("err", {"shard": sid, "error": str(e)[:300]}, sid)); time.sleep(3); continue
            if r:
                q.put(("hit", r, sid))
            else:
                q.put(("idle", {"shard": sid}, sid))

    bal = int(hc.rpc("eth_getBalance", [miner, "latest"]), 16) / 1e18
    st = hc.state(miner)
    log(f"farm start | wallet {miner} | balance {bal:.6f} RH-ETH | shards {args.shards} | {args.minutes} min | dry={args.dry}")
    log(f"round: block={st['block']} anchor={st['anchorBlock']} prevBits={hc.bits_of(st['prevWork'])} "
        f"targetBits={st['targetBits']} minted={st['totalMinted']} price={st['mintPrice']/1e18:.6f} ETH")

    handles = [threading.Thread(target=shard_worker, args=(i,), daemon=True) for i in range(args.shards)]
    for t in handles:
        t.start()

    deadline = time.time() + args.minutes * 60
    hits = 0
    mints = 0
    while time.time() < deadline:
        try:
            kind, payload, sid = q.get(timeout=1.0)
        except queue.Empty:
            continue
        if kind == "err":
            log(f"shard {sid} error: {payload['error']}")
        elif kind == "idle":
            continue
        else:
            hits += 1
            nonce = payload["nonce"]
            h, ok = hc.verify(miner, nonce, payload["prevWork"], payload["anchor"], payload["target"])
            log(f"HIT shard {payload['shard']} nonce=0x{nonce:064x} depth={256-h.bit_length()} "
                f"below={ok} slices={payload['slices']}")
            live = hc.state(miner)
            fresh = (live["prevWork"] == payload["prevWork"] and live["anchorBlock"] == payload["anchorBlock"])
            rec = {"nonce": hex(nonce), "verified": ok, "fresh_at_check": fresh,
                   "hash": hex(h), "round": {k: (hex(v) if isinstance(v, int) else v) for k, v in payload.items() if k != "found_line"},
                   "live_prevBits": hc.bits_of(live["prevWork"]), "live_targetBits": live["targetBits"],
                   "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            if not ok:
                log("  -> discarded (hash did not verify)"); solf.write(json.dumps(rec) + "\n"); solf.flush(); continue
            if not fresh:
                log("  -> discarded (round moved on before we could send)"); solf.write(json.dumps(rec) + "\n"); solf.flush(); continue
            if args.dry:
                log("  -> DRY: verified + round fresh, would broadcast"); solf.write(json.dumps(rec) + "\n"); solf.flush(); continue
            try:
                price = live["mintPrice"]
                tx, raw = hc.build_tx(key, nonce, payload["anchorBlock"], price)
                res = hc.rpc("eth_sendRawTransaction", ["0x" + raw.lstrip("0x")])
                rec["tx"] = res if isinstance(res, str) else res
                log(f"  -> BROADCAST {res} (value {price/1e18:.6f} ETH)")
                solf.write(json.dumps(rec) + "\n"); solf.flush()
                mints += 1
                if mints >= args.max_mints:
                    log(f"reached --max-mints {args.max_mints}; stopping farm")
                    break
            except Exception as e:
                log(f"  -> broadcast failed: {str(e)[:400]}")
                solf.write(json.dumps(rec) + "\n"); solf.flush()
    stop.set()
    log(f"farm stop | hits {hits} | mints broadcast {mints}")
    logf.close(); solf.close()


if __name__ == "__main__":
    # Modal functions can only be called from a script while the App is hydrated/running.
    with hm.app.run():
        main()
