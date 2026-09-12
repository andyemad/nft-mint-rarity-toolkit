#!/usr/bin/env python3
"""hashcats_modal.py — Hashcats PoW mining on Modal H100s (Robinhood Chain 4663).

  modal run hashcats_modal.py --mode probe          # validate CUDA kernel vs the verified CPU reference
  modal run hashcats_modal.py --mode bench          # measure GH/s on an H100
  python3 farm.py --shards 8 --minutes 30           # real farm (local broadcast, needs funded wallet)
"""
import json, os, subprocess, time, urllib.request

import modal

HERE = os.path.dirname(os.path.abspath(__file__))
RPC = "https://rpc.mainnet.chain.robinhood.com"
COLLECTION = "0xCA75DF55Cc9C476DB27a7375D1fc8E794cf80721"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"

CUDA_IMAGE = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.11")
    .apt_install("wget", "gnupg", "ca-certificates")
    .run_commands(
        "wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/ck.deb"
        " && dpkg -i /tmp/ck.deb",
        "apt-get update && apt-get install -y cuda-nvcc-12-4 cuda-cudart-dev-12-4",
    )
    .add_local_file(os.path.join(HERE, "hcminer.cu"), "/root/hcminer.cu", copy=True)
    .run_commands("/usr/local/cuda-12.4/bin/nvcc -O3 -o /usr/local/bin/hcminer_cuda /root/hcminer.cu")
)

app = modal.App("hashcats-miner")


RPC_FALLBACKS = ["https://rpc.mainnet.chain.robinhood.com", "https://robinhood.drpc.org"]


def _rpc(method, params, url=None):
    """Multi-endpoint RPC with backoff — the RH RPC 429s hard when many shards poll at once."""
    import urllib.error, time as _t
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last = None
    for attempt in range(3):
        for u in ([url] if url else RPC_FALLBACKS):
            try:
                req = urllib.request.Request(u, data=body, headers={"content-type": "application/json", "user-agent": UA})
                out = json.load(urllib.request.urlopen(req, timeout=25))
                return out["result"] if "result" in out else out
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 502, 503, 504):
                    _t.sleep(0.5 * (attempt + 1)); continue
                raise
            except Exception as e:
                last = e; continue
    raise RuntimeError(f"rpc failed: {last}")


def _sel(sig):
    from Crypto.Hash import keccak as _k
    h = _k.new(digest_bits=256); h.update(sig.encode()); return "0x" + h.hexdigest()[:8]


def _call(sig, args=()):
    d = _sel(sig) + "".join(hex(int(a))[2:].rjust(64, "0") for a in args)
    return _rpc("eth_call", [{"to": COLLECTION, "data": d}, "latest"])


def _round(miner):
    a = _call("currentAnchor()")[2:]
    return {
        "anchorBlock": int(a[0:64], 16), "anchor": "0x" + a[64:128],
        "prevWork": int(_call("prevWork()"), 16),
        "target": int(_call("targetFor(address)", (int(miner, 16),)), 16),
        "price": int(_call("mintPrice()"), 16),
        "minted": int(_call("totalMinted()"), 16),
        "block": int(_rpc("eth_blockNumber", []), 16),
    }


@app.function(image=CUDA_IMAGE, gpu="H100", timeout=900)
def probe(miner: str, prev: int, anchor: str, nonce: int):
    out = subprocess.run(["/usr/local/bin/hcminer_cuda", "probe", miner,
                          hex(prev)[2:].rjust(64, "0"), anchor, "%064x" % nonce],
                         capture_output=True, text=True)
    return {"stdout": out.stdout.strip(), "stderr": out.stderr.strip()[-400:]}


@app.function(image=CUDA_IMAGE, gpu="H100", timeout=900)
def bench(seconds: int = 8, blocks: int = 528, threads: int = 256, mode: str = "benchh"):
    out = subprocess.run(["/usr/local/bin/hcminer_cuda", mode, str(seconds), str(blocks), str(threads)],
                         capture_output=True, text=True)
    return {"stdout": out.stdout.strip(), "stderr": out.stderr.strip()[-400:]}


@app.function(image=CUDA_IMAGE, gpu="H100", timeout=3700)
def mine_one(miner: str, max_seconds: int = 600, slice_s: int = 11, shard: int = 0):
    """Mine the live round in short slices, re-reading prev/anchor between slices so a stale
    preimage is never mined for long. Returns the first solution found (or None)."""
    t_end = time.time() + max_seconds
    slices = 0
    while time.time() < t_end:
        try:
            st = _round(miner)
        except Exception:
            time.sleep(1.0); continue
        slices += 1
        remain = int(t_end - time.time())
        if remain <= 0:
            break
        out = subprocess.run(["/usr/local/bin/hcminer_cuda", "mine", miner,
                              hex(st["prevWork"])[2:].rjust(64, "0"), st["anchor"],
                              hex(st["target"])[2:].rjust(64, "0"),
                              str(min(remain, slice_s))],
                             capture_output=True, text=True)
        if "nonce=0x" in out.stdout:
            nz = out.stdout.split("nonce=0x")[1].split()[0]
            return {"nonce": int(nz, 16), "anchorBlock": st["anchorBlock"], "anchor": st["anchor"],
                    "prevWork": st["prevWork"], "target": st["target"], "price": st["price"],
                    "minted": st["minted"], "shard": shard, "slices": slices, "t": time.time(),
                    "found_line": out.stdout.strip().splitlines()[0] if out.stdout.strip() else ""}
    return None


def _cpu_reference(miner, prev, anchor, nonce):
    from Crypto.Hash import keccak as _k
    m = bytes.fromhex(miner.replace("0x", ""))
    pre = m + int(nonce).to_bytes(32, "big") + int(prev).to_bytes(32, "big") + bytes.fromhex(anchor.replace("0x", ""))
    h = _k.new(digest_bits=256); h.update(pre)
    return h.hexdigest()


@app.local_entrypoint()
def main(mode: str = "bench", seconds: int = 8, miner: str = "0x1111111111111111111111111111111111111111"):
    if mode == "probe":
        st = _round(miner)
        nonce = 0x0000000000000000000000000000000000000000000000000000deadbeef1234
        res = probe.remote(miner, st["prevWork"], st["anchor"], nonce)
        ref = _cpu_reference(miner, st["prevWork"], st["anchor"], nonce)
        print("modal :", res["stdout"], res["stderr"])
        print("cpu   : hash=0x" + ref)
        print("MATCH :", ("hash=0x" + ref) in res["stdout"])
        return
    if mode == "bench":
        # benchh = real mining kernel w/ exact hash counter (authoritative); bench = kbench loop
        print("A) authoritative (benchh, real mine kernel):")
        print(json.dumps(bench.remote(seconds, 528, 256, "benchh"), indent=1))
        print("B) legacy kbench loop (same numbers = harness is trustworthy):")
        print(json.dumps(bench.remote(seconds, 4096, 256, "bench"), indent=1))
        return
    if mode == "mine":
        print(json.dumps(mine_one.remote(miner, seconds, 11, 0), indent=1))
        return
