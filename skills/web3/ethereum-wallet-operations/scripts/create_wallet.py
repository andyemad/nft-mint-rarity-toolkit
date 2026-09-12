#!/usr/bin/env python3
"""Generate a fresh EVM wallet locally and back up the private key.

Usage:
    uv run --quiet --with eth-account python3 create_wallet.py <name>

Writes ~/.hermes/secrets/<name>_key (chmod 600), then re-derives the address
from the saved file to prove the backup matches. Prints address + path only —
NEVER the private key. Then verify on-chain:
    curl -s -m 12 -X POST -H "Content-Type: application/json" \
      --data '{"jsonrpc":"2.0","method":"eth_getBalance","params":["<ADDR>","latest"],"id":1}' \
      https://eth.merkle.io
    # Robinhood Chain: https://rpc.mainnet.chain.robinhood.com
"""
import os
import stat
import sys

from eth_account import Account


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: create_wallet.py <name>")
        sys.exit(1)
    name = sys.argv[1].strip()
    if not name or "/" in name or ".." in name:
        print("invalid name")
        sys.exit(1)

    acct = Account.create()
    path = os.path.expanduser(f"~/.hermes/secrets/{name}_key")
    with open(path, "w") as f:
        f.write(acct.key.hex() + "\n")
    os.chmod(path, 0o600)

    acct2 = Account.from_key(open(path).read().strip())
    if acct.address != acct2.address:
        print("ERROR: saved key re-derives to a different address")
        sys.exit(1)

    print("ADDRESS:", acct.address)
    print("KEYFILE:", path)
    print("PERMS:", oct(os.stat(path).st_mode)[-3:])


if __name__ == "__main__":
    main()
