---
name: nft-trait-taxonomy
description: "Build/audit NFT trait taxonomies with vision passes."
version: 1.0.0
metadata:
  hermes:
    tags: [nft, traits, rarity, vision, metadata]
---

# Building and auditing NFT trait taxonomies

Use when grouping an NFT collection's artwork into structured trait categories
(Background, Eyes, Expression, Motifs...) for review dashboards, rarity scoring,
or canister/marketplace metadata — especially when classification depends on
looking at images instead of on-chain attributes.

## Proven workflow

1. **Derive the population programmatically first.** Read the normalized catalog,
   compute which tokens each category applies to (e.g. "Finished Character"
   excludes sketch-tier tokens and out-of-scope 1/1s). Never hand-type token ID
   ranges.
2. **Survey with contact sheets.** Render all applicable tokens into numbered
   grid sheets (~12 cells, labeled `#<id>` in yellow) with PIL and ask the vision
   model for terse per-token feature descriptions across every candidate axis.
3. **Verify every claim at high resolution.** Contact-sheet reads are hypotheses
   only. Re-render claimed tokens as larger crops (400–900px cells) and ask for
   CONFIRM/REJECT per feature with explicit decision rules (e.g. "glasses =
   visible frames or lenses; a plain eyelid line is NOT glasses").
4. **Tiebreak contradictions with single-token zooms.** If two passes disagree
   (they will — see pitfalls), render just the disputed tokens near-full-size and
   ask narrow, answerable questions ("is there a distinct floating ring above the
   head?").
5. **Encode assignments in a builder script**, not by editing JSON. A Node/Python
   script that writes the draft JSON lets every rebuild be reproducible and
   assertion-checked.
6. **Assert coverage in the builder.** For exclusive categories assert every
   expected token appears exactly once (missing/repeated/extra all fail). For
   non-exclusive motifs assert membership validity only, and accept that
   unassigned tokens can be legitimate ("no motif" is data, not a gap).
7. **Encode exact assignments in tests too** (`assert.deepEqual(reps, [...])`)
   so any later edit that silently changes a group fails loudly.
8. **Record every decision in revision_notes** inside the output JSON, including
   rejected false positives — future audits need to know what was already
   checked and why it stayed rejected.

## Pitfalls

- **One vision pass is never enough.** In one audit, a contact-sheet pass said
  token A had a halo and B didn't; full-resolution zoom proved the exact reverse
  (the "halo" was a UFO light beam). Contradictions between passes are normal;
  the zoomed tiebreak is authoritative.
- **Classic false positives:** eyelid lines read as glasses; ordinary oval eyes
  read as X-eyes or cyclops; background glows read as halos. Classic misses:
  small worn accessories (star patches, bows, chokers) invisible at thumbnail
  size.
- **Vision models miscount grid cells** on long sheets (repeated labels, skipped
  IDs). Give the explicit ordered ID list when re-asking, and split into more
  sheets rather than trusting one big pass.
- **Respect prior user-confirmed decisions.** Revision notes may record that a
  token was explicitly excluded from a value after a previous full-res review.
  Do not silently reverse those on a new machine-read; flag the conflict to the
  user instead.
- **Scope checks before assigning:** confirm each candidate token's curation tier
  and duplicate-image status before adding it anywhere — sketch-tier duplicates
  and 1/1s outside the draft scope will break coverage assertions and belong in
  different categories.
- **Editing long JS arrays via scripted string replace** tends to leave trailing
  commas / dropped elements. Prefer the patch tool with exact context, and let
  the builder's own assertions catch what slips through.
- **Hand-typed ID lists for NEW categories are error-prone even with assertions.**
  When introducing a category covering ~100 tokens, expect several rounds of the
  coverage assertion catching: tokens duplicated across two values, wearers of
  one accessory wrongly also in a "visible" value, and out-of-scope IDs (sketch
  duplicates, 1/1s). Budget for it; the assertion doing its job is progress.
- **Eye-color traits need their own zoom pass — face crops ~470px and eye-region
  crops at 700px+.** Full-character thumbnails cannot resolve iris color; two
  passes at different zoom levels will disagree ("green eyes" vs "black eyes
  with green skin around them"). Ask whether the COLOR is in the iris itself or
  only in surrounding skin/eyelids/accessories, and which viewer side any
  asymmetric feature sits on.
- **Distinguish eyewear reflections from eye color.** Purple "eyes" may be
  purple sunglass lenses; blue "eyes" may be blue eyelids/eyeshadow over black
  pupils. Ask: is the color IN the eye, or ON something covering/around it?
- **A silhouette token has no eyes.** Check that eyes are visible AT ALL before
  assigning any Eye Style value; add an explicit "No Eyes / Silhouette" value
  rather than forcing a style onto a featureless silhouette.
- **User correction ("you got a lot of X wrong") after shipping a vision-built
  category means re-audit the WHOLE axis**, not just flagged tokens: sweep every
  token with per-token terse questions, tiebreak conflicts with single-token
  ultra-zooms, then rewrite the category's values from verified data.
- **"You haven't distinguished X well enough" means the value taxonomy is too
  coarse — split fused buckets into named values.** A 9-bucket Skin Color draft
  became 19 precise values after user pushback: Green / Mint Green / Olive Green,
  Blue vs Cyan, Pink vs Red-Maroon, White vs Gray, Gold-Yellow vs Peach, and one
  named value per pattern (Polka Dots, Rainbow Stripes, Pixel Pattern, Clown
  Rainbow, Striped) instead of a single "Multicolor / Patterned" junk drawer.
  Collectible-grade users expect shade-level precision.
- **Programmatic pixel sampling anchors but does not decide skin color.** Sample
  face-region pixels and quantize to /24 RGB buckets to find outliers cheaply
  (a "Green" token whose cheek samples read rgb(183,68,102) is mislabeled — that
  is background bleeding through), then confirm every outlier and every ambiguous
  token with a labeled thumbnail sheet + two-pass vision read (broad pass, then
  targeted second-opinion pass on just the disputed IDs). Backgrounds dominate
  naive crops; sample the head region and take the most common non-background
  cluster.
- **Shade calls need side-by-side comparison sheets**, not absolute judgments:
  render the whole family on one sheet and ask the model to rank lightest→darkest
  and name shades relative to each other. Single-token asks flip between passes
  ("white" vs "pale blue"); comparative framing stabilizes them.
- **Compute big-category membership from an exclusion set, not hand-typed lists.**
  For a value covering ~70 tokens (e.g. Normal Black eyes), list only the special
  tokens and derive the rest via filter — hand-typing 80 IDs guarantees missing/
  repeated errors across several rebuild rounds even with coverage assertions.
- **When a fused motif axis becomes its own category, MIGRATE, don't duplicate.**
  Headwear lived as loose Motif values (Baseball Cap, Afro, Bandana,
  Hair/Headpiece...) until the user asked for "traits for baseball caps, reverse
  cap, afro, etc." — the signal to promote it to an exclusive category with a
  None value. Delete the old motif values, and add negative assertions
  (`"Baseball Cap" in motif === false`) so they cannot silently return. Expect
  overlap dedups when one token has two head features (hair vs hat): pick the
  dominant item for the exclusive slot and record the runner-up in revision notes.
- **Feature-region zooms beat whole-character zooms for accessory calls.** For
  headwear, crop the top ~55% of each image before upscaling; full thumbnails
  misread berets as hair buns, propeller beanies as party hats, and fox ears as
  cat ears. Labels drawn in black boxes (not bare yellow text) survive vision
  reads far better on busy sheets.
- **`npm test` hides syntax errors behind a generic "test failed".** When a test
  file suddenly reports fail-1 with no assertion diff, run `node
  test/<file>.mjs` directly — scripted string-replaces can insert declarations
  outside callback scope (duplicate `const`) that only surface as clean
  SyntaxErrors that way.
- **Update computed catch-all exclusion sets in the same edit as the value list.**
  When a category has a derived value ("None" = everyone not in `wornSet`), a
  rewritten value list with a stale set produces nonsense coverage errors
  (`repeated=` ids that appear in both their real value and None). Grep for ALL
  copies of the set literal first — scripted replaces can leave duplicates.
- **Split cap-style traits BY COLOR into separate values** (Black Baseball Cap,
  Blue Baseball Cap, Black/Blue/Red Reverse Cap...). Users at collectible grade
  treat color variants as distinct traits, not one shape value.
- **Ear-worn items (headphones) are Motifs, never Headwear.** Headwear = on-top-
  of-head only; keep the boundary explicit or headphones drift in.
- **When the user rejects a trait NAME (not the assignment), stop re-guessing
  synonyms and ask them to name it.** Four vision passes flip-flopping on one
  token's label is a naming problem, not a perception problem.
- **deepEqual is order-sensitive.** Match the builder's literal ID order in test
  assertions or sort both sides before comparing.

## References

- `references/ecalm-trait-case-study.md` — concrete category definitions,
  verified assignments, and the contradiction log from a full 200-token
  collection audit.
- `references/ecalm-eye-color-audit.md` — verified per-token iris-color
  verdicts from the Eye Style correction audit (colored-iris table, resolved
  black-eye false positives, unresolved items at pause).
- `references/ecalm-skin-color-audit.md` — Skin Color re-audit: 9 coarse
  buckets → 19 shade-precise values, pixel-probe method, flip-flop log.
- `references/ecalm-headwear-audit.md` — Headwear promotion from Motif to
  exclusive 19-value category: per-token zoom verdicts, flip-flop log, and the
  builder/test migration mechanics.
