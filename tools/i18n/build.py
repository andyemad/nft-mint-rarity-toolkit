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

SKIP_TAGS = {"pre", "code", "script", "style", "svg", "symbol", "path", "head"}
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
}
ORDER = ["en", "zh", "ar", "es", "fr", "de", "ru", "he", "ur"]
ENGLISH_NAMES = {
    "en": "English", "zh": "\u4e2d\u6587", "ar": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629",
    "fr": "Fran\u00e7ais", "de": "Deutsch", "ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
    "es": "Espa\u00f1ol", "he": "\u05e2\u05d1\u05e8\u05d9\u05ea", "ur": "Urdu (Roman)",
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
    """Yield ('text', raw_text, translatable) and ('tag', raw_tag, None)."""
    pos = 0
    stack = []
    for m in TAG_RE.finditer(doc):
        if m.start() > pos:
            yield ("text", doc[pos:m.start()], not any(t in SKIP_TAGS for t in stack))
        yield ("tag", m.group(0), None)
        pos = m.end()
        closing, name = m.group(1), m.group(2).lower()
        if closing:
            if name in stack:
                while stack and stack.pop() != name:
                    pass
        elif not m.group(3).rstrip().endswith("/"):
            stack.append(name)
    if pos < len(doc):
        yield ("text", doc[pos:], not any(t in SKIP_TAGS for t in stack))


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


def language_menu(code, prefix):
    items = []
    for other in ORDER:
        if other not in LANGS:
            continue
        href = f"{prefix}{other}/" if other != "en" else prefix or "./"
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


def build(code):
    lang_attr, direction, _label = LANGS[code]
    prefix = "" if code == "en" else "../"
    if not os.path.exists(SRC):
        sys.exit(f"master source missing: {SRC}")
    doc = open(SRC, encoding="utf-8").read()

    table, head, js = {}, {}, {}
    if code != "en":
        data = json.load(open(os.path.join(I18N, f"{code}.json"), encoding="utf-8"))
        table = {**data.get("text", {}), **data.get("attr", {})}
        head = data.get("head", {})
        js = normalise_tails(data.get("js", {}), code)

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

    # asset + internal paths relative to this page's depth
    if prefix:
        doc = doc.replace('href="assets/', f'href="{prefix}assets/')
        doc = doc.replace('src="assets/', f'src="{prefix}assets/')
        doc = doc.replace('href="prompts/"', f'href="{prefix}prompts/"')

    # Extra stylesheet for every page, including English. Inserted as a sibling of
    # the existing link so the asset-path rewrite below carries it for free.
    doc = re.sub(
        r'(<link rel="stylesheet" href="[^"]*styles\.css">)',
        rf'\1\n<link rel="stylesheet" href="{prefix}assets/i18n.css">',
        doc, count=1,
    )

    # hreflang alternates. English lives at the site root, not at /en/.
    def locale_href(other):
        if other == "en":
            return prefix or "./"
        return f"{prefix}{other}/"
    alternates = "".join(
        f'\n<link rel="alternate" hreflang="{LANGS[o][0]}" href="{locale_href(o)}">'
        for o in ORDER if o in LANGS
    )
    payload = json.dumps(js, ensure_ascii=False).replace("<", "\\u003c")
    inject = (
        f'{alternates}\n<script type="application/json" id="i18n-data">{payload}</script>\n'
        "<script>try{window.HERMES_I18N=JSON.parse(document.getElementById('i18n-data').textContent)}catch(e){}</script>\n"
    )
    doc = doc.replace("</head>", inject + "</head>", 1)

    # language menu into the top nav
    menu = language_menu(code, prefix)
    doc = re.sub(r"(<nav class=\"topnav\"[^>]*>)", r"\1" + menu, doc, count=1)

    # A second, text-free language row in the footer: endonyms only, so it needs
    # no translation and works in every language.
    footer_row = (
        '<p class="lang-row">'
        + " · ".join(
            f'<a href="{locale_href(o)}" hreflang="{LANGS[o][0]}"'
            + (' aria-current="true"' if o == code else "")
            + f">{ENGLISH_NAMES[o]}</a>"
            for o in ORDER if o in LANGS
        )
        + "</p>"
    )
    doc = doc.replace("</footer>", footer_row + "</footer>", 1)

    out_dir = DOCS if code == "en" else os.path.join(DOCS, code)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "index.html")
    open(out, "w", encoding="utf-8").write(doc)
    return len(table), len(missing), missing, out


def main():
    codes = sys.argv[1:] or ORDER
    total_missing = {}
    for code in codes:
        if code != "en" and not os.path.exists(os.path.join(I18N, f"{code}.json")):
            print(f"{code:<3} SKIPPED (no {code}.json yet)")
            continue
        n, nmiss, missing, out = build(code)
        flag = "OK " if nmiss == 0 else "GAPS"
        print(f"{code:<3} {flag} keys={n:<4} untranslated={nmiss:<3} -> {os.path.relpath(out, ROOT)}")
        for k in list(missing)[:8]:
            total_missing.setdefault(code, []).append(k)
    if total_missing:
        print("\nUntranslated leftovers (first few per language):")
        for code, keys in total_missing.items():
            for k in keys:
                print(f"  {code}: {k[:100]}")


if __name__ == "__main__":
    main()
