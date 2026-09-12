#!/usr/bin/env python3
"""Create the dedicated Hashcats mint wallet. Prints ONLY the address; key never echoed."""
import json, os, secrets, stat
from Crypto.Hash import keccak

PATH = os.path.expanduser("~/.hermes/secrets/hashcats_miner_key")
META = os.path.expanduser("~/.hermes/secrets/hashcats_miner_wallet.json")

if os.path.exists(PATH):
    key = open(PATH).read().strip()
    created = False
else:
    key = secrets.token_hex(32)
    fd = os.open(PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key + "\n")
    created = True

raw = bytes.fromhex(key.replace("0x", ""))
try:
    from eth_account import Account
    addr = Account.from_key(raw).address
except Exception:
    from coincurve import PrivateKey
    pub = PrivateKey(raw).public_key.format(compressed=False)[1:]
    h = keccak.new(digest_bits=256); h.update(pub)
    addr = "0x" + h.digest()[-20:].hex()

os.chmod(PATH, stat.S_IRUSR | stat.S_IWUSR)
meta = {"address": addr, "keyfile": PATH, "purpose": "hashcats PoW mint wallet",
        "collection": "0xCA75DF55Cc9C476DB27a7375D1fc8E794cf80721", "chain": "robinhood (4663)",
        "created": "2026-09-11"}
if not os.path.exists(META):
    json.dump(meta, open(META, "w"), indent=1)
    os.chmod(META, 0o600)

print("created new wallet" if created else "reusing existing wallet")
print("address:", addr)
print("keyfile:", PATH, "(chmod 600)")
