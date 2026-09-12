#!/usr/bin/env python3
"""Build the translated copies of docs/index.html.

One source of truth: the English docs/index.html. This script substitutes text
nodes, visible attributes, head strings and the app.js string table, then adds
the language menu, the script-aware stylesheet and the correct lang/dir.

Output:
  docs/index.html          English (rebuilt with the menu, text unchanged)
  docs/<code>/index.html   one per translated language

Run:
  python3 tools/i18n/build.py            # build all available languages
  python3 tools/i18n/build.py zh ar      # build a subset
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, "docs")
# The master English source. docs/index.html is a GENERATED artifact (it carries
# the language menu and alternates), so the master lives here and is never written
# by this script.
SRC = os.path.join(ROOT, "tools", "i18n", "index.en.html")
I18N = os.path.join(ROOT, "tools", "i18n")

# Mirrors extract.py. <pre> decides for itself: a "Discord prompt" block is
# translated, a terminal or settings block is code and is left alone.
SKIP_TAGS = {"code", "script", "style", "svg", "symbol", "path", "head"}
TRANSLATABLE_PRE_LABEL = "Discord prompt"
TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*)>")
ATTR_RE = re.compile(r'\b(data-label|aria-label|alt|placeholder|title)="([^"]*)"')
ONLY_PUNCT = re.compile(r"^(?:\s|[\d\W])+$")

# code -> (html lang attribute, dir, menu label)
LANGS = {
    "en": ("en", "ltr", "EN"),
    "zh": ("zh-Hans", "ltr", "\u4e2d\u6587"),
    "ar": ("ar", "rtl", "AR"),
    "fr": ("fr", "ltr", "FR"),
    "de": ("de", "ltr", "DE"),
    "ru": ("ru", "ltr", "RU"),
    "es": ("es", "ltr", "ES"),
    "he": ("he", "rtl", "HE"),
    "ur": ("ur-Latn", "ltr", "UR"),
    "ja": ("ja", "ltr", "JA"),
    "ko": ("ko", "ltr", "KO"),
}
ORDER = ["en", "zh", "ja", "ko", "ar", "es", "fr", "de", "ru", "he", "ur"]
ENGLISH_NAMES = {
    "en": "English", "zh": "\u4e2d\u6587", "ar": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629",
    "fr": "Fran\u00e7ais", "de": "Deutsch", "ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
    "es": "Espa\u00f1ol", "he": "\u05e2\u05d1\u05e8\u05d9\u05ea", "ur": "Urdu (Roman)",
    "ja": "\u65e5\u672c\u8a9e", "ko": "\ud55c\uad6d\uc5b4",
}


# Languages that do not put a space before punctuation must supply their own
# separator; everyone else gets a single leading space.
NO_SPACE_BEFORE_PUNCTUATION = {"zh", "ja", "ko"}


def normalise_tails(js, code):
    """The skill-count phrase is composed as "<n> <noun><tail>", so the tail has to
    carry its own separator. Chinese must not gain a space before its comma."""
    js = dict(js)
    for key in ("skills.ready", "skills.found"):
        if key not in js:
            continue
        value = str(js[key]).strip()
        if code in NO_SPACE_BEFORE_PUNCTUATION:
            js[key] = "\uff0c" + value.lstrip("\uff0c, ")
        else:
            js[key] = " " + value
    return js


def esc_text(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc_attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def walk(doc):
    """Yield ('text', raw_text, translatable) and ('tag', raw_tag, None).

    The stack holds (tag, skip) pairs so a <pre> can mark its own subtree as
    content (a Discord prompt) or code (a terminal command).
    """
    pos = 0
    stack = []
    for m in TAG_RE.finditer(doc):
        if m.start() > pos:
            yield ("text", doc[pos:m.start()], not any(skip for _t, skip in stack))
        yield ("tag", m.group(0), None)
        pos = m.end()
        closing, name, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if closing:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == name:
                    del stack[i:]
                    break
        elif not attrs.rstrip().endswith("/"):
            if name == "pre":
                # data-label is translated before this runs, so the block's own
                # language-independent data-kind has to decide, not its label.
                kind = re.search(r'data-kind="([^"]*)"', attrs)
                label = re.search(r'data-label="([^"]*)"', attrs)
                translatable = (
                    (kind and kind.group(1) == "prompt")
                    or (label and label.group(1) == TRANSLATABLE_PRE_LABEL)
                )
                skip = not translatable
            elif name == "code":
                # Inside a prompt block the code IS the content to translate.
                skip = not any(t == "pre" and not s for t, s in stack)
            elif name == "button" and "copy" in attrs:
                skip = True  # placeholder label, replaced by app.js
            else:
                skip = name in SKIP_TAGS
            stack.append((name, skip))
    if pos < len(doc):
        yield ("text", doc[pos:], not any(skip for _t, skip in stack))


def substitute_text(doc, table, missing):
    out = []
    for kind, payload, ok in walk(doc):
        if kind == "tag" or not ok:
            out.append(payload)
            continue
        stripped = payload.strip()
        if not stripped or ONLY_PUNCT.match(stripped):
            out.append(payload)
            continue
        key = html.unescape(stripped)
        if key.startswith("<!"):
            out.append(payload)
            continue
        if key in table:
            lead = payload[:len(payload) - len(payload.lstrip())]
            trail = payload[len(payload.rstrip()):]
            out.append(lead + esc_text(table[key]) + trail)
        else:
            if key not in missing:
                missing[key] = 0
            missing[key] += 1
            out.append(payload)
    return "".join(out)


def substitute_attrs(doc, table):
    def repl(m):
        name, value = m.group(1), html.unescape(m.group(2))
        if value.strip() in table:
            return f'{name}="{esc_attr(table[value.strip()])}"'
        return m.group(0)
    return ATTR_RE.sub(repl, doc)


def mark_pre_kinds(doc):
    """Add a language-independent data-kind so the copy button knows its label
    even after data-label is translated."""
    def repl(m):
        tag = m.group(0)
        if "data-kind=" in tag:
            return tag
        label = re.search(r'data-label="([^"]*)"', tag)
        kind = "prompt" if label and label.group(1) == "Discord prompt" else "terminal"
        return tag[:-1] + f' data-kind="{kind}">'
    return re.sub(r"<pre\b[^>]*>", repl, doc)


# The two pages of the site. Both are generated from their own master, and the
# vibe coding page reuses the guide's app.js strings so they translate once.
PAGES = {
    "guide": {
        "src": "index.en.html",
        "keys": "strings.json",
        "dict": "{code}.json",
        "out": "index.html",
    },
    "prompts": {
        "src": "prompts.en.html",
        "keys": "prompts.strings.json",
        "dict": "prompts.{code}.json",
        "out": "prompts/index.html",
    },
}


def page_prefix(code, page):
    """Depth of the generated page, relative to docs/."""
    depth = 1 if code != "en" else 0
    if page == "prompts":
        depth += 1
    return "../" * depth


def locale_href(other, code, page, prefix):
    """Where a language link points FROM this page: the same page in that
    language, so switching language keeps the reader where they were."""
    if other == code:
        return "./"
    if page == "prompts":
        return f"{prefix}prompts/" if other == "en" else f"{prefix}{other}/prompts/"
    return (prefix or "./") if other == "en" else f"{prefix}{other}/"


def language_menu(code, prefix, page):
    items = []
    for other in ORDER:
        if other not in LANGS:
            continue
        href = locale_href(other, code, page, prefix)
        current = ' aria-current="true"' if other == code else ""
        items.append(
            f'<li><a href="{href}" hreflang="{LANGS[other][0]}"{current}>'
            f'<span>{ENGLISH_NAMES[other]}</span><code>{LANGS[other][2]}</code></a></li>'
        )
    return (
        '<details class="lang" id="lang-menu"><summary aria-label="Language">'
        f'<span>{LANGS[code][2]}</span></summary>'
        '<ul class="lang-menu">' + "".join(items) + "</ul></details>"
    )


def build(code, page="guide"):
    lang_attr, direction, _label = LANGS[code]
    spec = PAGES[page]
    src = os.path.join(I18N, spec["src"])
    prefix = page_prefix(code, page)
    if not os.path.exists(src):
        sys.exit(f"master source missing: {src}")
    doc = open(src, encoding="utf-8").read()

    table, head, js = {}, {}, {}
    if code != "en":
        data = json.load(open(os.path.join(I18N, spec["dict"].format(code=code)),
                              encoding="utf-8"))
        table = {**data.get("text", {}), **data.get("attr", {})}
        head = data.get("head", {})
        # app.js strings live with the guide, so the vibe page reuses them.
        js = json.load(open(os.path.join(I18N, f"{code}.json"), encoding="utf-8")).get("js", {})
        js = normalise_tails(js, code)

    missing = {}
    doc = mark_pre_kinds(doc)
    doc = substitute_attrs(doc, table)

    # head strings
    for key, pattern, target in [
        ("title", r"<title>.*?</title>", "<title>{}</title>"),
        ("description", r'<meta name="description" content=".*?">',
         '<meta name="description" content="{}">'),
        ("og:title", r'<meta property="og:title" content=".*?">',
         '<meta property="og:title" content="{}">'),
        ("og:description", r'<meta property="og:description" content=".*?">',
         '<meta property="og:description" content="{}">'),
    ]:
        if key in head:
            is_text = key == "title"
            value = esc_text(head[key]) if is_text else esc_attr(head[key])
            doc = re.sub(pattern, target.format(value), doc, count=1, flags=re.S)

    # English keeps its own text, so leftovers are expected and not reported.
    doc = substitute_text(doc, table, missing if code != 'en' else {})

    # html lang/dir
    doc = re.sub(r'<html lang="[^"]*"', f'<html lang="{lang_attr}"', doc, count=1)
    if direction == "rtl":
        doc = re.sub(r"<html ", '<html dir="rtl" ', doc, count=1)
    else:
        doc = re.sub(r'<html dir="[^"]*" ', "<html ", doc, count=1)

    # asset + internal paths relative to this page's depth. The guide master sits
    # at the root; the vibe page master already sits one level deep.
    if page == "prompts":
        if prefix != "../":
            doc = doc.replace('href="../assets/', f'href="{prefix}assets/')
            doc = doc.replace('src="../assets/', f'src="{prefix}assets/')
            doc = doc.replace('href="../"', f'href="{prefix}"')
    elif prefix:
        doc = doc.replace('href="assets/', f'href="{prefix}assets/')
        doc = doc.replace('src="assets/', f'src="{prefix}assets/')
        # NOTE: the vibe coding link stays "prompts/" on purpose. It is relative
        # to this language's own directory, so docs/zh/ links to docs/zh/prompts/.


    # Extra stylesheet for every page, including English. Inserted as a sibling of
    # the existing link so the asset-path rewrite below carries it for free.
    doc = re.sub(
        r'(<link rel="stylesheet" href="[^"]*styles\.css">)',
        rf'\1\n<link rel="stylesheet" href="{prefix}assets/i18n.css">',
        doc, count=1,
    )

    # hreflang alternates point at the same page in each language.
    alternates = "".join(
        f'\n<link rel="alternate" hreflang="{LANGS[o][0]}"'
        f' href="{locale_href(o, code, page, prefix)}">'
        for o in ORDER if o in LANGS
    )
    payload = json.dumps(js, ensure_ascii=False).replace("<", "\\u003c")
    inject = (
        f'{alternates}\n<script type="application/json" id="i18n-data">{payload}</script>\n'
        "<script>try{window.HERMES_I18N=JSON.parse(document.getElementById('i18n-data').textContent)}catch(e){}</script>\n"
    )
    doc = doc.replace("</head>", inject + "</head>", 1)

    # language menu into the top nav
    menu = language_menu(code, prefix, page)
    doc = re.sub(r"(<nav class=\"topnav\"[^>]*>)", r"\1" + menu, doc, count=1)

    # A second, text-free language row in the footer: endonyms only, so it needs
    # no translation and works in every language.
    footer_row = (
        '<p class="lang-row">'
        + " · ".join(
            f'<a href="{locale_href(o, code, page, prefix)}" hreflang="{LANGS[o][0]}"'
            + (' aria-current="true"' if o == code else "")
            + f">{ENGLISH_NAMES[o]}</a>"
            for o in ORDER if o in LANGS
        )
        + "</p>"
    )
    doc = doc.replace("</footer>", footer_row + "</footer>", 1)

    out_dir = DOCS if code == "en" else os.path.join(DOCS, code)
    out = os.path.join(out_dir, spec["out"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(doc)
    return len(table), len(missing), missing, out


def main():
    args = [a for a in sys.argv[1:] if a not in PAGES]
    pages = [a for a in sys.argv[1:] if a in PAGES] or list(PAGES)
    codes = args or ORDER
    total_missing = {}
    for page in pages:
        spec = PAGES[page]
        if page == "prompts":
            print(f"\n--- {page} ---")
        for code in codes:
            if code != "en" and not os.path.exists(
                    os.path.join(I18N, spec["dict"].format(code=code))):
                print(f"{code:<3} SKIPPED (no {spec['dict'].format(code=code)} yet)")
                continue
            n, nmiss, missing, out = build(code, page)
            flag = "OK " if nmiss == 0 else "GAPS"
            print(f"{code:<3} {flag} keys={n:<4} untranslated={nmiss:<3}"
                  f" -> {os.path.relpath(out, ROOT)}")
            for k in list(missing)[:8]:
                total_missing.setdefault(f"{page}/{code}", []).append(k)
    if total_missing:
        print("\nUntranslated leftovers (first few per language):")
        for code, keys in total_missing.items():
            for k in keys:
                print(f"  {code}: {k[:100]}")


if __name__ == "__main__":
    main()
