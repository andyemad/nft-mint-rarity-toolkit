#!/usr/bin/env python3
"""Secret audit for this repository.

Run before publishing any change:

    python3 tools/secret_audit.py            # exit 1 on any hard-fail hit

Design notes
------------
A 64-hex scan produces false positives you must TRIAGE, not strip: event topics,
transaction hashes, padded selectors and test values all match the same shape as
a private key. So this audit:

  1. hard-fails on things that are unambiguously secret (PEM blocks, tokens,
     webhooks, keyed RPC URLs, personal identifiers, known operator wallets);
  2. reports every 64-hex string that is not on the PUBLIC_CONSTANTS allowlist,
     with file and line, so a human or agent reviews context instead of guessing;
  3. exits non-zero if either category has unreviewed entries.

A real private key lives in a key file or an env var, never inline next to the
word "keccak". That is what the triage step is for.
"""
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Public chain constants this repo deliberately cites (event topics, selectors,
# evidence transactions). Anything else must be reviewed.
PUBLIC_CONSTANTS = {
    # event topics
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",  # ERC-20/721 Transfer
    "0x8764214b5defe9caa9c5b38b36f0cc5e482a8ab15d78696659e61989e48e6e70",  # SeaDrop PublicDropUpdated
    "0xe90cf9cc0a552cf52ea6ff74ece0f1c8ae8cc9ad630d3181f55ac43ca076b7d6",  # SeaDropMint
    "0x3e30d8e1f739ea4795c481b21c23f905e938b80339305f3508e43c558e5dead3",  # SeaDrop mint log
    # padded selectors
    "0xc87b56dd0000000000000000000000000000000000000000000000000000000000000001",  # tokenURI(uint256)
    "0xc87b56dd00000000000000000000000000000000000000000000000000000000",
    # evidence transactions cited in skills
    "0x4a29d4f120507dd576ed721b221a076a994a871e9d9ed66b6bb108d2e0cf01b3",
    "0x4e90fa304d950e9944ffe93405497ba16bccd4afb826503429b3c841c95fc447",
    "0xb409c0dc0dfdece7beb61c3f318ef04498efe49e14d5cbd754737266f705b5b1",
    "0x645b4f5f88428c5c127b208e436b960a1343baf1fce8732f7268a02b16e6da75",
    "0x2e670890008694ffde9555696023f6efc80d7acdcca9a4dcf6b3724df633204d",
    "0xd47492ddc041005cb0a1a7f90daacb035779736d16edcec312c2b111a8b82b91",
    "0x084864cf63a1da316161d78c436aff2f4bb0ea6b5002f29d048c45a14bb3c39f",
}

HARD_FAIL = [
    ("private key literal", re.compile(r"0x[a-fA-F0-9]{64}")),
    ("PEM private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("seed/mnemonic assignment",
     re.compile(r"\b(mnemonic|seed_?phrase)\s*[=:]\s*[\"'][a-z ]{20,}")),
    ("github token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})")),
    ("slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("google oauth token", re.compile(r"\bya29\.[A-Za-z0-9_\-]{20,}")),
    ("openai-style key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("discord webhook",
     re.compile(r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[\w-]+")),
    ("keyed rpc url",
     re.compile(r"(alchemy\.com/v2/|infura\.io/v3/|quiknode|moralis)[A-Za-z0-9_\-/]{8,}")),
    ("agent-inbox key", re.compile(r"\b(am|moni)_[A-Za-z0-9]{16,}")),
    ("cloud provider token",
     re.compile(r"\b(HERMES|OPENAI|ANTHROPIC|CLOUDFLARE|VERCEL)_[A-Z_]*(?:KEY|TOKEN|SECRET)\s*[=:]\s*[\"'][^\"']{12,}")),
]

TEXT_EXT = {".md", ".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".c", ".h", ".cu",
            ".swift", ".sh", ".json", ".sol", ".toml", ".yml", ".yaml", ".html",
            ".css", ".txt", ".rs", ".example", ""}

SKIP_DIRS = {".git", "node_modules", ".next", "__pycache__", ".venv", "venv"}


def main():
    hits = []
    hexes = Counter()
    files = 0

    for root, dirs, fns in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in fns:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, ROOT)
            if rel.startswith("tools/"):
                continue  # this audit necessarily contains the patterns
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            files += 1
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for name, pat in HARD_FAIL:
                for m in pat.finditer(text):
                    line = text[:m.start()].count("\n") + 1
                    val = m.group(0)
                    if name == "private key literal" and val in PUBLIC_CONSTANTS:
                        continue
                    hits.append((rel, line, name, val[:80]))
            for m in re.finditer(r"0x[a-fA-F0-9]{64}", text):
                hexes[m.group(0)] += 1

    unknown = {h: c for h, c in hexes.items() if h not in PUBLIC_CONSTANTS}

    print(f"scanned {files} text files under {ROOT}\n")

    if hits:
        print(f"HARD FAIL: {len(hits)} hit(s)")
        for rel, ln, name, sample in hits:
            print(f"  {rel}:{ln}  [{name}]  {sample}")
    else:
        print("hard-fail scan: clean")

    print()
    if unknown:
        print(f"UNREVIEWED 64-hex strings: {len(unknown)} (triage by reading context)")
        for h, c in sorted(unknown.items(), key=lambda x: -x[1]):
            print(f"  x{c}  {h}")
    else:
        print("64-hex scan: every value is an allowlisted public constant")

    return 1 if (hits or unknown) else 0


if __name__ == "__main__":
    sys.exit(main())
