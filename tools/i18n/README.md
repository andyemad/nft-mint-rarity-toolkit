# Translations

The site is published in nine languages: English, Simplified Chinese, Arabic,
Spanish, French, German, Russian, Hebrew, and Roman Urdu (Urdu in Latin script).

## The one rule

`tools/i18n/index.en.html` is the **master**. Every page under `docs/` — including
the English one — is generated from it:

```
tools/i18n/index.en.html  ──build.py──▶  docs/index.html      (English)
                                         docs/zh/index.html   (中文)
                                         docs/ar/index.html   (العربية, rtl)
                                         docs/es|fr|de|ru/…   …
```

Edit the master, then rebuild. Editing `docs/index.html` directly works locally
until the next build overwrites it.

```sh
python3 tools/i18n/extract.py     # refresh the key list from the master
python3 tools/i18n/validate.py    # check every language file
python3 tools/i18n/build.py       # rebuild all pages (or: build.py zh ar)
python3 tools/i18n/verify.py      # structural + RTL check on the output
```

## What gets translated

`extract.py` pulls four buckets out of the master:

| bucket  | what it is                                                     |
|---------|----------------------------------------------------------------|
| `text`  | body text nodes. Anything inside `<pre>`, `<code>`, `<script>`, `<style>` or `<svg>` is skipped, so commands and code are never touched. |
| `attr`  | visible or spoken attributes: `data-label`, `aria-label`, `alt`, `placeholder`, `title` |
| `head`  | `<title>`, meta description, Open Graph tags                    |
| `js`    | the `T()` string table in `docs/assets/app.js` (demo, copy buttons, progress) |

Each language file holds all four, keyed by the **exact English string**. That is
how substitution works, so keys must never be edited — only values.

## Adding a language

1. Copy `tools/i18n/<code>.json` from an existing language.
2. Translate the values. Keep keys, brand names, URLs, prices and the `{n}`
   placeholder untouched.
3. Add the code to `LANGS` and `ORDER` in `build.py`, and to the `lang-menu`
   markup in `docs/prompts/index.html`.
4. `validate.py`, `build.py`, `verify.py`.

## Things that are easy to get wrong

- **Right-to-left.** `styles.css` uses physical properties (`left`, `padding-left`),
  so `docs/assets/i18n.css` has a `[dir="rtl"]` mirror for each one. `verify.py`
  fails if a physical property used by `styles.css` has no mirror. Commands stay
  left-to-right on RTL pages: everything the reader must *type* is forced to
  `direction: ltr` so it reads exactly as it will be typed.
- **Fonts.** Sora and DM Sans ship as latin subsets, so `i18n.css` gives every
  non-latin script a real font stack. Headings use `letter-spacing: -3.7px`, which
  damages Arabic, Hebrew and CJK, so it is reset for those scripts and the line
  height is opened up.
- **Pluralisation.** English builds "31 skills to put to work". Other languages
  take the pieces from `skills.one`, `skills.many`, `skills.ready`, `skills.found`
  so the phrase can be rearranged.
- **The copy button** decides its label from `data-kind="prompt"`, not from the
  visible `data-label`, because that label is translated.

## Roman Urdu

`ur` is Urdu written in Latin script, the way Urdu speakers actually type on
WhatsApp and X: Urdu grammar and word order, with English technical nouns kept in
Latin (*mint*, *wallet*, *gas*, *skill*) because that is how people really write
it. `validate.py` fails the build if any Arabic-script characters appear in it.
