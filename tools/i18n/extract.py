#!/usr/bin/env python3
"""Extract every translatable string from a master page (guide or vibe coding).

Three buckets, because they are substituted by different rules:

  text  — text nodes in the body. Anything inside <pre>, <code>, <script>,
          <style>, <svg> is skipped: commands, code and icon paths must never
          be translated.
  attr  — attribute values that are visible or read aloud: data-label (rendered
          by CSS), aria-label, alt, placeholder, title. Structural attributes
          (class, id, href, data-*) are ignored.
  head  — <title> and the meta description / og tags.
  js    — user-facing strings inside assets/app.js, found by their I18N keys.

Writes tools/i18n/strings.json.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Which master document to read and where to write its key list. The generated
# pages under docs/ carry the injected language menu, so the masters are the only
# honest source for a key list.
#   python3 tools/i18n/extract.py            -> the guide
#   python3 tools/i18n/extract.py prompts    -> the vibe coding page
I18N = os.path.join(ROOT, "tools", "i18n")
DOCUMENTS = {
    "guide": ("index.en.html", "strings.json"),
    "prompts": ("prompts.en.html", "prompts.strings.json"),
}
DOC = sys.argv[1] if len(sys.argv) > 1 else "guide"
if DOC not in DOCUMENTS:
    sys.exit(f"unknown document {DOC!r}; choose from {', '.join(DOCUMENTS)}")
SRC = os.path.join(I18N, DOCUMENTS[DOC][0])
OUT = os.path.join(I18N, DOCUMENTS[DOC][1])
APPJS = os.path.join(ROOT, "docs", "assets", "app.js")

# Never translated, anywhere.
SKIP_TAGS = {"code", "script", "style", "svg", "symbol", "path", "head"}
# <pre> is special. A block labelled "Discord prompt" is copy-paste text the
# reader is meant to send, so it IS translated (the @yourbot mention is kept).
# A terminal block, a settings file or an unlabelled block is code and never is.
TRANSLATABLE_PRE_LABEL = "Discord prompt"
TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*)>", re.S)
ATTR_RE = re.compile(r'\b(data-label|aria-label|alt|placeholder|title)="([^"]*)"')
ONLY_PUNCT = re.compile(r"^(?:\s|[\d\W])+$")

# Keys defined in app.js, with the English text used as the default.
JS_KEYS = [
    "copy.discord", "copy.terminal", "copy.button", "copy.done", "copy.aria",
    "toast.copied", "toast.manual",
    "progress.count", "progress.saved", "progress.visit", "toast.complete",
    "skills.one", "skills.many", "skills.ready", "skills.found",
    "demo.rarity.prompt", "demo.rarity.answer", "demo.rarity.title",
    "demo.rarity.subtitle", "demo.rarity.foot",
    "demo.mint.prompt", "demo.mint.answer", "demo.mint.title",
    "demo.mint.subtitle", "demo.mint.foot",
    "demo.mint.row1", "demo.mint.row2", "demo.mint.row3", "demo.mint.tag",
    "demo.wallet.prompt", "demo.wallet.answer", "demo.wallet.title",
    "demo.wallet.subtitle", "demo.wallet.foot",
    "demo.wallet.row1", "demo.wallet.row2", "demo.wallet.row3", "demo.wallet.tag",
]
JS_DEFAULTS = {
    "copy.discord": "Copy Discord prompt",
    "copy.terminal": "Copy terminal command",
    "copy.button": "Copy",
    "copy.done": "Copied",
    "copy.aria": "Copied to clipboard",
    "toast.copied": "Copied. Paste it when you’re ready.",
    "toast.manual": "Automatic copying is unavailable. The text is selected so you can copy it.",
    "progress.count": "{n} of 4",
    "progress.saved": "Saved in this browser",
    "progress.visit": "Progress kept for this visit",
    "toast.complete": "Setup complete. Your next step: send your agent a message.",
    "skills.one": "skill",
    "skills.many": "skills",
    "skills.ready": " to put to work",
    "skills.found": " found",
    "demo.rarity.prompt": "rank this collection and show me the rare ones",
    "demo.rarity.answer": "Collection ranked. Here are the three rarest.",
    "demo.rarity.title": "Rarity report",
    "demo.rarity.subtitle": "Demo collection",
    "demo.rarity.foot": "Research only. No transactions sent.",
    "demo.mint.prompt": "check this mint before I connect my wallet",
    "demo.mint.answer": "I’ll check the contract, price, and supply first.",
    "demo.mint.title": "Mint research",
    "demo.mint.subtitle": "Example checklist",
    "demo.mint.foot": "Review the findings before approving a mint.",
    "demo.mint.row1": "Verify the real contract",
    "demo.mint.row2": "Read the onchain mint price",
    "demo.mint.row3": "Check remaining supply",
    "demo.mint.tag": "Check first",
    "demo.wallet.prompt": "what has this wallet been buying lately?",
    "demo.wallet.answer": "I’ll turn the wallet’s public activity into a report.",
    "demo.wallet.title": "Wallet intelligence",
    "demo.wallet.subtitle": "Example report",
    "demo.wallet.foot": "Public wallet data. No private keys needed.",
    "demo.wallet.row1": "Recent purchases",
    "demo.wallet.row2": "Collections held",
    "demo.wallet.row3": "Sales and transfers",
    "demo.wallet.tag": "Onchain",
}


def pre_is_translatable(attrs):
    m = re.search(r'data-label="([^"]*)"', attrs)
    kind = re.search(r'data-kind="([^"]*)"', attrs)
    if kind:
        return kind.group(1) == "prompt"
    return bool(m) and m.group(1) == TRANSLATABLE_PRE_LABEL


def walk(doc):
    """Yield (kind, payload, is_translatable) segments in document order.

    The stack holds (tag, skip) pairs, so a <pre> can decide for its own subtree
    whether its text is content or code.
    """
    pos = 0
    stack = []
    for m in TAG_RE.finditer(doc):
        text = doc[pos:m.start()]
        if text:
            yield ("text", html.unescape(text),
                   not any(skip for _tag, skip in stack))
        pos = m.end()
        closing, name, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if closing:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == name:
                    del stack[i:]
                    break
        elif not attrs.rstrip().endswith("/"):
            if name == "pre":
                skip = not pre_is_translatable(attrs)
            elif name == "code":
                # Inside a prompt block the code IS the content to translate.
                skip = not any(t == "pre" and not s for t, s in stack)
            elif name == "button" and "copy" in attrs:
                skip = True  # placeholder label, replaced by app.js
            else:
                skip = name in SKIP_TAGS
            stack.append((name, skip))
    tail = doc[pos:]
    if tail:
        yield ("text", html.unescape(tail), not any(skip for _tag, skip in stack))


def main():
    doc = open(SRC, encoding="utf-8").read()

    strings, seen = [], set()
    for kind, payload, ok in walk(doc):
        if kind != "text" or not ok:
            continue
        t = payload.strip()
        if not t or ONLY_PUNCT.match(t) or t.startswith("<!DOCTYPE"):
            continue
        if t in seen:
            continue
        seen.add(t)
        strings.append(t)

    attrs = []
    for m in ATTR_RE.finditer(doc):
        value = html.unescape(m.group(2)).strip()
        if not value or value in seen or ONLY_PUNCT.match(value):
            continue
        seen.add(value)
        attrs.append(value)

    head = {}
    for key, pattern in [
        ("title", r"<title>(.*?)</title>"),
        ("description", r'<meta name="description" content="(.*?)">'),
        ("og:title", r'<meta property="og:title" content="(.*?)">'),
        ("og:description", r'<meta property="og:description" content="(.*?)">'),
    ]:
        m = re.search(pattern, doc, re.S)
        if m:
            head[key] = html.unescape(m.group(1))

    appjs = open(APPJS, encoding="utf-8").read()
    # app.js writes curly quotes as JS escapes; unescape so the verbatim test works
    appjs = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), appjs)
    missing = [k for k in JS_DEFAULTS if JS_DEFAULTS[k] not in appjs
               and k not in ("progress.count", "skills.one", "skills.many",
                             "skills.ready", "skills.found")]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"strings": strings, "attrs": attrs, "head": head,
               "js_keys": JS_KEYS, "js_defaults": JS_DEFAULTS},
              open(OUT, "w"), ensure_ascii=False, indent=1)

    print(f"text strings : {len(strings)}")
    print(f"attributes   : {len(attrs)}")
    print(f"head strings : {len(head)}")
    print(f"js keys      : {len(JS_KEYS)}")
    print(f"words total  : {sum(len(s.split()) for s in strings)}")
    if missing:
        print("WARNING: js defaults not found verbatim in app.js:", missing)
    print(f"written      : {OUT}")


if __name__ == "__main__":
    main()
