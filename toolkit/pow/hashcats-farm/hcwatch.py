#!/usr/bin/env python3
"""hcwatch.py — continuous Metal miner for the M2 GPU. Follows the live round, verifies every
candidate with independent Python keccak, and auto-mints from the funded wallet.

  python3 hcwatch.py --minutes 240 [--key ~/.hermes/secrets/hashcats_miner_key] [--dry] [--max-mints 2]

Runs unattended. Free (uses the Mac's own GPU). Wins whenever the network target eases —
at the 32-bit epoch floor this does 2^32/153e6 ≈ 28 s per solution.
"""
import argparse, json, os, subprocess, sys, time
from Crypto.Hash import keccak

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hashcats as hc  # noqa: E402

BIN = os.path.join(HERE, "hcminer_fast")


def counter_word(c):
    even, odd = c & 0xFFFF, c >> 16
    v = 0
    for b in range(16):
        v |= (((even >> b) & 1) << (2 * b)) | (((odd >> b) & 1) << (2 * b + 1))
    return v


def nonce_for(counter):
    """nonce = 28 zero bytes || counter_word(counter) LE (bytes 48..51 of the preimage)."""
    return bytes(28) + counter_word(counter).to_bytes(4, "little")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=240)
    ap.add_argument("--key", default="~/.hermes/secrets/hashcats_miner_key")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--max-mints", type=int, default=2)
    ap.add_argument("--slice", type=int, default=12)
    args = ap.parse_args()

    key = hc.read_key(args.key)
    from eth_account import Account
    miner = Account.from_key(key).address
    log = open(os.path.join(HERE, "hcwatch.log"), "a")

    def out(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        log.write(line + "\n"); log.flush()

    out(f"hcwatch start | wallet {miner} | metal {BIN} | dry={args.dry} | max_mints={args.max_mints}")
    deadline = time.time() + args.minutes * 60
    mints = 0
    rounds = 0
    hashes = 0
    while time.time() < deadline:
        if mints >= args.max_mints:
            out(f"reached max mints {mints} — stopping"); break
        try:
            st = hc.state(miner)
        except Exception as e:
            out(f"rpc error {str(e)[:120]}"); time.sleep(2); continue
        bal = int(hc.rpc("eth_getBalance", [miner, "latest"]), 16)
        if bal < st["mintPrice"]:
            out(f"wallet cannot pay a mint (bal {bal/1e18:.6f} < price {st['mintPrice']/1e18:.6f}) — stopping"); break
        rounds += 1
        prev_hex = "%064x" % st["prevWork"]
        p = subprocess.run([BIN, "mine", miner, prev_hex, st["anchor"], "%064x" % st["target"],
                            str(args.slice)], capture_output=True, text=True, timeout=args.slice + 60)
        cands = [ln for ln in p.stdout.splitlines() if ln.startswith("CAND ")]
        rate_line = [ln for ln in p.stdout.splitlines() if ln.startswith("TIMEOUT")]
        if rate_line:
            try:
                r = float(rate_line[0].split("rate=")[1].split()[0])
                hashes += int(r * 1e6 * args.slice)
            except Exception:
                pass
        out(f"round {rounds}: minted={st['totalMinted']} bits={st['targetBits']} cands={len(cands)}"
            f"{' ' + rate_line[0] if rate_line else ''}")
        for ln in cands:
            parts = ln.split()
            counter = int(parts[1].split("=")[1])
            nonce = nonce_for(counter)
            n = int.from_bytes(nonce, "big")
            h, ok = hc.verify(miner, n, st["prevWork"], st["anchor"], st["target"])
            if not ok:
                out(f"  cand counter={counter} verified=False (skip)")
                continue
            live = hc.state(miner)
            fresh = (live["prevWork"] == st["prevWork"] and live["anchorBlock"] == st["anchorBlock"])
            out(f"  HIT counter={counter} nonce=0x{n:064x} depth={256-h.bit_length()} fresh={fresh}")
            if not fresh:
                out("  stale before send — discarded"); continue
            if args.dry:
                out("  DRY: verified + fresh, would broadcast"); continue
            try:
                tx, raw = hc.build_tx(key, n, st["anchorBlock"], live["mintPrice"])
                res = hc.rpc("eth_sendRawTransaction", ["0x" + raw.lstrip("0x")])
                out(f"  BROADCAST {res}")
                mints += 1
                with open(os.path.join(HERE, "solutions.json"), "a") as f:
                    f.write(json.dumps({"nonce": "0x%064x" % n, "tx": res if isinstance(res, str) else res,
                                        "depth": 256 - h.bit_length(), "round": st["totalMinted"],
                                        "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "source": "metal-mac"}) + "\n")
            except Exception as e:
                out(f"  broadcast failed: {str(e)[:300]}")
    out(f"hcwatch exit | rounds={rounds} mints={mints} hashes≈{hashes:.3e}")
    log.close()


if __name__ == "__main__":
    main()
