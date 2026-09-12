# Next 16.3 metadata / font conventions — verified in this repo

All facts verified 2026-08-14 against `node_modules/next/dist/` (Next 16.3.0,
package.json `"next": "16.3.0"`). Re-check the cited files when the Next
version bumps — do not carry these forward blindly across upgrades.

## Icons / favicon file conventions

- **`favicon` convention = `.ico` ONLY.** Filename `favicon`, extensions
  `['ico']` — see `STATIC_METADATA_IMAGES` in
  `node_modules/next/dist/lib/metadata/is-metadata-route.js`. A
  `src/app/favicon.png` is **silently ignored**: it emits no `<link>` tag and
  produces no error, which makes it look like it worked.
- **`icon` convention accepts .ico/.jpg/.jpeg/.png/.svg** → `src/app/icon.png`
  is auto-wired to `<link rel="icon" type="image/png" sizes="32x32">`.
- **Precedence trap:** when both `favicon.ico` and `icon.png` exist,
  `discover.js` (`node_modules/next/dist/build/webpack/loaders/metadata/discover.js`)
  `unshift`s the favicon FIRST — the old default `.ico` wins in emitted links.
  To rebrand the favicon: rename `favicon.png` → `icon.png` AND delete
  `favicon.ico`, or the Vercel-triangle default keeps showing.
- `apple-icon`: `.jpg/.jpeg/.png` only (no `.svg`).
- **`src/app/` is not a static dir.** Only `public/` is served as-is. A
  non-convention file (e.g. a banner SVG) placed in `src/app/` is neither a
  route nor an asset — move it to `public/` or import it from code
  (`import url from "./x.svg"`).
- Doc: `node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/01-metadata/app-icons.md`

## next/font/google (variable fonts)

- **Font inventory:** `node_modules/next/dist/compiled/@next/font/dist/google/font-data.json`
  (1942 fonts with weights/styles/axes). Verify a font exists here before
  importing it — imports of unknown fonts throw at build.
- **Syntax:** `const f = Caveat({ subsets: ["latin"], weight: "variable", variable: "--font-x" })`,
  apply `${f.variable}` as a className on `<html>` in the root layout, then
  reference `var(--font-x)` in CSS (globals or CSS modules).
- **`weight: "variable"` is build-safe for ANY variable font.** Per
  `get-font-axes.js` (`compiled/@next/font/dist/google/`), when no `axes:`
  option is passed only the `wght` axis is requested — multi-axis fonts
  (e.g. Fraunces with SOFT/WONK/opsz) do NOT error and do NOT need `axes: [...]`.
- Relevant weights (this repo): Caveat wght 400–700 normal-only; Fraunces
  100–900 normal+italic; Cormorant Garamond 300–700; DM Serif Display 400 only.
- `variable:` sets the CSS var ON THE HTML ELEMENT, and `:root` IS html — so
  `:root` rules may safely reference `var(--font-x, fallback...)` (custom
  property var() resolves at computed-value time on the same element).
- `next/font/google` downloads font files at BUILD time — needs network on the
  build host (fine on Vercel, breaks in offline/air-gapped builds).

## Worked example (the case-study collection Suites rebrand)

Brand script = Caveat (variable), brand serif small-caps = Fraunces
(`font-variant-caps: small-caps` + wide letter-spacing). Favicon chain:
`cp /tmp/casestudy_logo.png public/casestudy-logo.png` → `mv src/app/favicon.png src/app/icon.png`
→ `rm src/app/favicon.ico` → optional `sips -z 180 180 public/casestudy-logo.png --out src/app/apple-icon.png`.
Full spec: `research/casestudy-brand-system.md` in the repo.
