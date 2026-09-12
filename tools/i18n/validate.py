#!/usr/bin/env python3
"""Validate the translation files before they are built into pages.

Checks per language file:
  - JSON parses, top-level shape correct
  - key sets match the English source EXACTLY (no missing, no invented keys)
  - no empty or whitespace-only values
  - placeholders preserved ({n})
  - values contain no raw < or > (they are escaped at build time, so this
    catches markup that leaked in from a translation)
  - script sanity: each language actually uses its own writing system
  - Roman Urdu must contain NO Arabic-script characters
  - how many values are identical to the English (brand names and numbers are
    expected here; a high count means the file was not really translated)

Exit code 1 if any file is unusable.
"""
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
I18N = os.path.join(ROOT, "tools", "i18n")
SRC = json.load(open(os.path.join(I18N, "strings.json"), encoding="utf-8"))

EXPECT_SOURCE = SRC["strings"]

EXPECT = {
    "text": set(SRC["strings"]),
    "attr": set(SRC["attrs"]),
    "head": set(SRC["head"].keys()),
    "js": set(SRC["js_keys"]),
}

CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
ARABIC = re.compile(r"[\u0600-\u06ff\u0750-\u077f]")
HEBREW = re.compile(r"[\u0590-\u05ff]")
CYRILLIC = re.compile(r"[\u0400-\u04ff]")
LATIN = re.compile(r"[A-Za-z]")

# script expectation: (regex that must appear in a good share of values, label)
SCRIPT = {
    "zh": (CJK, "Han characters"),
    "ar": (ARABIC, "Arabic characters"),
    "he": (HEBREW, "Hebrew characters"),
    "ru": (CYRILLIC, "Cyrillic characters"),
    "fr": (LATIN, "Latin letters"),
    "de": (LATIN, "Latin letters"),
    "es": (LATIN, "Latin letters"),
    "ur": (LATIN, "Latin letters (Roman Urdu)"),
}


def inline(s):
    return " ".join(str(s).split())


# Strings that are correctly left alone in every language: they are literal UI
# paths and product names, not prose.
ALLOW_IDENTICAL = {
    "Add New → Project",
    "Windows, Mac & Linux",
    "Proof of Play research",
    "Research. Rank. Mint. Monitor.",
}


def main():
    problems = 0
    codes = [c for c in ("zh", "ar", "fr", "de", "ru", "es", "he", "ur")
             if os.path.exists(os.path.join(I18N, f"{c}.json"))]
    if not codes:
        print("no translation files found yet")
        return 1

    for code in codes:
        path = os.path.join(I18N, f"{code}.json")
        print(f"\n=== {code}  ({os.path.getsize(path)//1024} KB)")
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            print(f"  FAIL  invalid JSON: {e}")
            problems += 1
            continue

        bad = False
        for bucket, expected in EXPECT.items():
            got = set(data.get(bucket, {}).keys())
            missing = expected - got
            extra = got - expected
            if missing or extra:
                bad = True
                print(f"  FAIL  {bucket}: {len(missing)} missing, {len(extra)} invented")
                for k in list(missing)[:4]:
                    print(f"          missing: {k[:80]}")
                for k in list(extra)[:4]:
                    print(f"          invented: {k[:80]}")
            else:
                print(f"  ok    {bucket}: {len(got)} keys match")

        values = []
        for bucket in ("text", "attr", "head", "js"):
            values += [v for v in data.get(bucket, {}).values() if isinstance(v, str)]

        empty = [v for v in values if not inline(v)]
        if empty:
            bad = True
            print(f"  FAIL  {len(empty)} empty values")

        markup = [v for v in values if "<" in v or ">" in v]
        if markup:
            print(f"  warn  {len(markup)} values contain < or > : {inline(markup[0])[:60]}")

        for key in ("progress.count",):
            got = data.get("js", {}).get(key, "")
            if "{n}" not in got:
                bad = True
                print(f"  FAIL  js.{key} lost the {{n}} placeholder: {got!r}")

        # A sentence that is still word-for-word English means a paragraph was
        # never translated. Key counts alone cannot catch that: Russian passed
        # every other check while eleven prompt blocks were still in English.
        still_english = []
        for src_string in EXPECT_SOURCE:
            if len(src_string.split()) < 4:
                continue
            if src_string in ALLOW_IDENTICAL:
                continue
            if data.get("text", {}).get(src_string, "").strip() == src_string.strip():
                still_english.append(src_string)
        if still_english:
            bad = True
            print(f"  FAIL  {len(still_english)} sentence(s) still identical to English")
            for s in still_english[:4]:
                print(f"          {inline(s)[:84]}")
        else:
            print("  ok    no untranslated sentences")

        # script sanity
        uniq = list(dict.fromkeys(values))
        rx, label = SCRIPT[code]
        hits = sum(1 for v in uniq if rx.search(v))
        share = hits / max(1, len(uniq))
        status = "ok   " if share >= 0.6 else "FAIL "
        if share < 0.6:
            bad = True
        print(f"  {status} script: {share*100:.0f}% of values contain {label}")

        if code == "ur":
            leaked = [v for v in uniq if ARABIC.search(v)]
            if leaked:
                bad = True
                print(f"  FAIL  Roman Urdu contains Arabic script in {len(leaked)} values,"
                      f" e.g. {inline(leaked[0])[:60]}")

        # how much is still English
        text = data.get("text", {})
        same = [k for k, v in text.items() if v == k]
        print(f"  info  {len(same)} of {len(text)} text values identical to English "
              f"({len(same)/max(1,len(text))*100:.1f}%)")

        # a real sample so a human can eyeball fluency
        sample = [k for k in list(text)[:400] if len(k) > 60][:3]
        for k in sample:
            print(f"  · en: {inline(k)[:78]}")
            print(f"    {code}: {inline(text[k])[:78]}")

        problems += 1 if bad else 0

    print(f"\n{'ALL GOOD' if problems == 0 else f'{problems} file(s) need work'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
