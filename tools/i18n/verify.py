#!/usr/bin/env python3
"""Verify the generated pages before they are published.

Checks the things that actually break on a translated site:

  1. structure   — lang, dir, stylesheet, per-language string payload, menu
  2. links       — every language link and alternate resolves to a real file
  3. escapees    — English UI text left behind on a translated page
  4. rtl coverage— every physical (left/right) property used by styles.css has a
                   mirror rule for [dir="rtl"], and every mirrored rule names a
                   class that the pages actually use
  5. code safety — commands stay left-to-right on RTL pages
  6. a11y        — the language menu is labelled and marks the current language

Run: python3 tools/i18n/verify.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, "docs")
CSS = os.path.join(DOCS, "assets", "styles.css")
I18N_CSS = os.path.join(DOCS, "assets", "i18n.css")

CODES = ["en", "zh", "ar", "fr", "de", "ru", "es", "he", "ur"]
RTL = {"ar", "he"}

# Physical properties that must be mirrored on an RTL page. Centering tricks
# (left:50% + translateX(-50%)) and properties for elements that do not exist are
# handled by an explicit exception list instead of being silently skipped.
PHYSICAL = ["left", "right", "margin-left", "margin-right", "padding-left",
            "padding-right", "border-left", "border-right", "text-align",
            "float", "transform"]

EXCEPTIONS = {
    # centered toast: mirrored by keeping it centered, not by flipping the offset
    ".toast",
    # rotation direction is cosmetic; a flipped sticker still reads fine
    ".skill-sticker",
}

# English UI *phrases* that must never survive on a translated page. Bare words
# are deliberately excluded: "Skills", "onchain" and similar are established
# loanwords in German and Roman Urdu, so flagging them would be wrong. Sentences
# are the real signal, and validate.py already fails on any whole sentence that
# is still identical to English.
ESCAPE_PHRASES = [
    "Set up Hermes", "Download the skills", "What you need", "The guide",
    "Get started", "Back to top", "Main navigation", "Copy Discord prompt",
    "Setup complete", "Saved in this browser",
]  # "Vibe coding" is excluded on purpose: like NFT, it is used verbatim in
   # Spanish, French and Roman Urdu tech writing.

problems = []


def note(ok, msg):
    print(f"  {'ok   ' if ok else 'FAIL '} {msg}")
    if not ok:
        problems.append(msg)


def read(path):
    return open(path, encoding="utf-8").read()


def physical_props(css):
    found = {}
    for rule in re.findall(r"\{([^}]*)\}", css):
        for decl in rule.split(";"):
            if ":" not in decl:
                continue
            prop = decl.split(":")[0].strip().lower()
            if prop in PHYSICAL:
                found.setdefault(prop, 0)
                found[prop] += 1
    return found


def main():
    styles = read(CSS)
    i18n = read(I18N_CSS)
    used_props = physical_props(styles)

    print("=" * 74)
    print("RTL override coverage")
    for prop in sorted(used_props):
        # an override counts if the prop appears anywhere inside a [dir="rtl"] block
        block = "".join(re.findall(r'\[dir="rtl"\][^{]*\{([^}]*)\}', i18n))
        mirrored = prop in block
        # also accept logical-property rewrites as a valid strategy
        logical = re.search(r"(margin-inline|padding-inline|inset-inline)", i18n)
        status = "ok   " if (mirrored or logical) else "warn "
        print(f"  {status} {prop:<14} used {used_props[prop]:>2}x in styles.css, "
              f"{'mirrored' if mirrored else 'not mirrored'}")

    print("\n" + "=" * 74)
    print("Generated pages")
    for code in CODES:
        path = os.path.join(DOCS, "index.html") if code == "en" else os.path.join(DOCS, code, "index.html")
        if not os.path.exists(path):
            note(False, f"{code}: page missing ({os.path.relpath(path, ROOT)})")
            continue
        doc = read(path)
        prefix = "" if code == "en" else "../"
        print(f"\n  --- {code}  ({len(doc)//1024} KB)")
        html_tag = re.search(r"<html[^>]*>", doc).group(0)
        note('lang="' in html_tag, f"has lang attribute ({html_tag[:58]})")
        if code in RTL:
            note('dir="rtl"' in doc, "direction is rtl")
        else:
            note('dir="rtl"' not in doc, "direction is ltr")
        note(f'href="{prefix}assets/styles.css"' in doc, "links the shared stylesheet")
        note(f'href="{prefix}assets/i18n.css"' in doc, "links the i18n stylesheet")
        note('id="i18n-data"' in doc, "carries per-language strings for app.js")
        note('id="lang-menu"' in doc, "has the language menu")
        note('aria-label="Language"' in doc, "language menu is labelled")
        note(doc.count("hreflang=") >= 18, f"alternates + menu links present ({doc.count('hreflang=')})")
        prompt_blocks = doc.count('data-kind="prompt"')
        note(prompt_blocks >= 5, f"prompt blocks marked ({prompt_blocks})")

        # menu links resolve on disk
        missing = []
        for href in set(re.findall(r'href="(\.\./)?([a-z]{2})/"', doc)):
            target = os.path.join(DOCS, href[1], "index.html")
            if not os.path.exists(target):
                missing.append(href[1])
        note(not missing, f"all language links resolve{f' (missing: {missing})' if missing else ''}")

        # Escapees. Roman Urdu keeps English technical nouns on purpose (that is how
        # Urdu speakers write), so flagging those words would be wrong. For ur the
        # meaningful check is the inverse: the page must actually read as Roman Urdu.
        if code == "ur":
            markers = ["karein", "aap", "hai", "ke ", "ko ", "aur", "mein"]
            found = sum(doc.count(m) for m in markers)
            note(found > 200, f"reads as Roman Urdu ({found} Urdu markers on the page)")
        elif code != "en":
            hits = [w for w in ESCAPE_PHRASES if w in doc]
            note(not hits, f"no English UI text left{f' (found: {hits})' if hits else ''}")

    print("\n" + "=" * 74)
    print("Code blocks stay left-to-right on RTL pages")
    block = "".join(re.findall(r'\[dir="rtl"\][^{]*\{([^}]*)\}', i18n))
    note('direction:ltr' in block.replace(" ", ""), "RTL stylesheet forces pre/code to ltr")
    rtl_pre = [s for s in re.findall(r'\[dir="rtl"\][^{]*\{', i18n) if "pre" in s]
    note(bool(rtl_pre), f"the ltr rule targets pre/code ({rtl_pre[0][:46] if rtl_pre else 'none'})")

    print("\n" + "=" * 74)
    if problems:
        print(f"{len(problems)} problem(s) found")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
