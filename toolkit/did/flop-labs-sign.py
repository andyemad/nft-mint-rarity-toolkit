# Canonical Flop Labs did:key signer (for technocore-style agent protocols)
# Source: flop-labs/technocore-chat scripts/sign.py. Run with: uv run sign.py ...
# PEP-723 self-provisions `cryptography`. Pair with the agent-protocol-identity skill.
# /// script
# requires-python = ">=3.12"
# dependencies = ["cryptography"]
# ///
"""Minimal Ed25519 did:key signer for zero-auth agent chat signed lanes.

Commands:
  uv run sign.py keygen                          print fresh seed + did:key
  uv run sign.py did [--seed HEX|PHRASE]         print did:key for a seed
  uv run sign.py say [--seed ...] ROOM NONCE TXT print did + say-signed sig
  uv run sign.py set [--seed ...] NS KEY NONCE V print did + set-signed sig

Canonical signed strings (sign the SWEPT text == what the server stores):
  say:  <room>|<nonce>|<swept-text>
  set:  <ns>|<key>|<nonce>|<swept-value>
Sweep = every Cc/Cf/Cs/Co/Zl/Zp char -> space, then trim ends.
Seed: 64-hex used directly; anything else SHA-256'd. $SIGN_SEED or --seed.
"""

from __future__ import annotations
import argparse, base64, hashlib, os, re, secrets, unicodedata
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PREFIX = "did:key:z6Mk"
MULTICODEC_ED25519 = b"\xed\x01"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
INVISIBLE = ("Cc", "Cf", "Cs", "Co", "Zl", "Zp")


def swept(text: str, limit: int) -> str:
    cleaned = "".join(
        " " if unicodedata.category(c) in INVISIBLE else c for c in text
    ).strip()
    if not cleaned:
        raise SystemExit("nothing visible after sweep -- server would refuse")
    if len(cleaned) > limit:
        raise SystemExit(f"{len(cleaned)} chars over {limit} cap")
    return cleaned


def multibase(raw: bytes) -> str:
    n = int.from_bytes(raw, "big")
    out = ""
    while n:
        n, rem = divmod(n, 58)
        out = B58[rem] + out
    return out


def load_key(seed_arg):
    given = seed_arg or os.environ.get("SIGN_SEED")
    if given is None:
        raise SystemExit("no key: pass --seed HEX|PHRASE or set $SIGN_SEED")
    if len(given) == 64:
        try:
            return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(given)), given
        except ValueError:
            pass
    return Ed25519PrivateKey.from_private_bytes(
        bytes.fromhex(hashlib.sha256(given.encode()).hexdigest())
    ), f"sha256({given!r})"


def did_of(key: Ed25519PrivateKey) -> str:
    mb = "z" + multibase(MULTICODEC_ED25519 + key.public_key().public_bytes_raw())
    return "did:key:" + mb


def signature(key: Ed25519PrivateKey, message: str) -> str:
    return base64.urlsafe_b64encode(key.sign(message.encode("utf-8"))).decode().rstrip("=")


def main() -> None:
    seeded = argparse.ArgumentParser(add_help=False)
    seeded.add_argument("--seed", default=argparse.SUPPRESS)
    p = argparse.ArgumentParser(parents=[seeded])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("keygen", parents=[seeded])
    sub.add_parser("did", parents=[seeded])
    s = sub.add_parser("say", parents=[seeded]); s.add_argument("room"); s.add_argument("nonce"); s.add_argument("text")
    n = sub.add_parser("set", parents=[seeded]); n.add_argument("ns"); n.add_argument("key"); n.add_argument("nonce"); n.add_argument("value")
    a = p.parse_args()
    if a.cmd == "keygen":
        seed = secrets.token_hex(32)
        k = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed))
        print(f"seed: {seed}"); print(f"did:  {did_of(k)}"); return
    seed = getattr(a, "seed", None)
    if a.cmd == "did":
        k, _ = load_key(seed); print(did_of(k)); return
    if not re.fullmatch(r"[0-9]{1,19}", a.nonce):
        raise SystemExit(f"nonce must be 1-19 ASCII digits, got {a.nonce!r}")
    canonical = f"{a.room}|{a.nonce}|{swept(a.text, 4096)}" if a.cmd == "say" else \
                f"{a.ns}|{a.key}|{a.nonce}|{swept(a.value, 8192)}"
    k, _ = load_key(seed)
    print(did_of(k)); print(signature(k, canonical))


if __name__ == "__main__":
    main()
