#!/usr/bin/env python3
"""Compile-check a Solidity SeaDrop/ERC721 contract WITHOUT Foundry.

Fix for the 4 py-solc-x pitfalls hit in practice:
  1. compile_files does NOT forward --include-paths to solc  -> use compile_standard
  2. compile_standard wants a dict, not a json string
  3. source-dict KEYS must match import paths -> base = node_modules dir
  4. solc 0.8.26 handles OpenZeppelin 5.x

Setup (one-time, any temp dir):
    python3 -m venv /tmp/solcenv
    /tmp/solcenv/bin/pip install py-solc-x
    mkdir -p /tmp/oz && cd /tmp/oz && npm init -y >/dev/null && npm i @openzeppelin/contracts@5.0.2

Usage (from the contract dir, edit paths at top if needed):
    /tmp/solcenv/bin/python ~/.hermes/skills/web3/nft-collection-production/scripts/compile_check_sol.py
"""
import solcx, glob, os, json

SOLC_VERSION = "0.8.26"
CONTRACT_FILE = "StillUp.sol"
CONTRACT_NAME = "StillUp"
OZ = "/tmp/oz/node_modules/@openzeppelin/contracts"
OZ_BASE = "/tmp/oz/node_modules"          # MUST be node_modules so keys = import paths
OUT_ABI = "StillUp.abi.json"
OUT_BIN = "StillUp.bin"

solcx.install_solc(SOLC_VERSION)
sources = {CONTRACT_FILE: {"content": open(CONTRACT_FILE).read()}}
for p in glob.glob(OZ + "/**/*.sol", recursive=True):
    sources[os.path.relpath(p, OZ_BASE)] = {"content": open(p).read()}

si = {
    "language": "Solidity",
    "sources": sources,
    "settings": {
        "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}},
        "optimizer": {"enabled": True, "runs": 200},
    },
}
out = solcx.compile_standard(si, solc_version=SOLC_VERSION, allow_paths=".")

key = f"{CONTRACT_FILE}:{CONTRACT_NAME}"
if key in out.get("contracts", {}).get(CONTRACT_FILE, {}):
    c = out["contracts"][CONTRACT_FILE][CONTRACT_NAME]
    bin_ = c["evm"]["bytecode"]["object"]
    abi = c["abi"]
    open(OUT_ABI, "w").write(json.dumps(abi, indent=2))
    open(OUT_BIN, "w").write(bin_)
    print(f"COMPILE OK  bytecode_len={len(bin_)}  abi_entries={len(abi)}")
    print(f"artifacts: {OUT_ABI} ({os.path.getsize(OUT_ABI)}B), {OUT_BIN} ({os.path.getsize(OUT_BIN)}B)")
else:
    for e in out.get("errors", []):
        print(e.get("severity"), e.get("formattedMessage", "")[:400])
    raise SystemExit(1)
