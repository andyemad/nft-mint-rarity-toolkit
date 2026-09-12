#!/usr/bin/env python3
"""Merge split half-translations into one language file.

A language whose translation had to be split (Russian was, after provider errors
killed two single-run attempts) arrives as ru.part1.json and ru.part2.json. This
joins them, checks the key set against the source exactly, and writes ru.json.

Run: python3 tools/i18n/merge_parts.py ru
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
I18N = os.path.join(ROOT, "tools", "i18n")


def main():
    code = sys.argv[1] if len(sys.argv) > 1 else "ru"
    src = json.load(open(os.path.join(I18N, "strings.json"), encoding="utf-8"))
    expected = set(src["strings"])

    parts = sorted(
        glob.glob(os.path.join(I18N, f"{code}.part*.json"))
        + glob.glob(os.path.join(I18N, f"{code}.c[0-9].json"))
    )
    if not parts:
        sys.exit(f"no {code}.part*.json files to merge")

    text = {}
    for path in parts:
        data = json.load(open(path, encoding="utf-8"))
        block = data.get("text", {})
        # Keys must come from the source; anything else would never substitute.
        for key in block:
            if key not in expected:
                print(f"  warn: {os.path.basename(path)} has a key not in the source: {key[:60]!r}")
        text.update(block)
        print(f"  {os.path.basename(path):<16} {len(block)} keys")

    missing = sorted(expected - set(text))
    extra = sorted(set(text) - expected)
    print(f"\nmerged: {len(text)} keys   missing: {len(missing)}   extra: {len(extra)}")
    for key in missing[:10]:
        print(f"  MISSING: {key[:80]!r}")

    if missing:
        sys.exit("refusing to write a partial language file")

    # The split runs only cover body text. UI labels, the page head and the
    # app.js strings are short, so they are supplied as a companion file rather
    # than risking another long provider run.
    extra_path = os.path.join(I18N, f"{code}.extra.json")
    extra = json.load(open(extra_path, encoding="utf-8")) if os.path.exists(extra_path) else {}

    def pick(bucket):
        merged = dict(extra.get(bucket, {}))
        existing_path = os.path.join(I18N, f"{code}.json")
        if os.path.exists(existing_path):
            merged.update(json.load(open(existing_path, encoding="utf-8")).get(bucket, {}))
        return merged

    out = {
        "lang": extra.get("lang", code),
        "name": extra.get("name", code),
        "dir": extra.get("dir", "ltr"),
        "text": text,
        "attr": pick("attr"),
        "head": pick("head"),
        "js": pick("js"),
    }
    for bucket in ("attr", "head", "js"):
        if not out[bucket]:
            print(f"  warn: no {bucket} strings for {code}")
    existing = os.path.join(I18N, f"{code}.json")
    with open(existing, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {os.path.relpath(existing, ROOT)}")


if __name__ == "__main__":
    main()
