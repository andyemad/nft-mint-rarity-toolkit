---
name: nft-trait-curation
description: Use when auditing or approving NFT metadata trait drafts.
---

# NFT trait curation — vision-assisted trait audits

Class workflow for assigning human-quality trait metadata (background, skin, lips,
motifs, clothing) to a fixed token set whose images are cached locally. Proven on
ecalm-icp-metadata (see `references/ecalm-icp-metadata.md`); generalizes to any
collection with `<catalog>.json` + local image paths.

## Workflow (two-pass vision audit)

1. **Read the existing draft first.** Load the trait JSON + its generator script +
   its test file BEFORE looking at any image. Prior revisions encode user-confirmed
   decisions (in revision_notes AND test assertions) — those outrank what you see.
   A test like `assert Cosmic Glow does not include 118` means a previous full-res
   audit already settled that token; do not silently reverse it.
2. **Coverage check before auditing.** Compute per-category expected vs assigned
   sets in Python. Exclusive categories must partition their scope exactly once;
   non-exclusive ones (Motif) may repeat tokens. Report the gap list — that list IS
   the audit workload.
3. **Pass 1 — contact-sheet sweep.** Render all gap tokens into labeled grid PNGs
   (~300px cells, 5-9 per sheet, yellow `#id` labels via PIL) and ask vision_analyze
   for motif presence against the EXACT value list with its exact definitions.
4. **Pass 2 — full-resolution verification.** For every claimed feature, re-render
   just the claimants larger (~420px+) with the claim in the label (`#118 glasses?`)
   and ask CONFIRM/REJECT per feature. Then run one more sweep over the tokens the
   first pass called "clean" — pass 1 misses worn accessories and small props.
5. **Apply only confirmed assignments** to the generator script, bump the revision
   notes with every add AND every rejection (rejections prevent future sessions
   from re-flagging the same false positive).
6. **Update tests to encode the new truth**, rebuild, run builder + full test suite
   + verify script, then confirm the review HTML page serves 200.

## Pitfalls

- **Pepe-style eyelids fake out glasses detection.** A heavy-lidded eye line is NOT
  glasses; require visible frames or tinted lenses. Expect false positives here.
- **Vision models hallucinate plausible motifs on stylized art** (cybernetic eyes,
  glitch treatments, printed-vs-worn stars). Every single assignment needs the
  high-res confirm pass — never bulk-apply pass-1 output.
- **"No motif found" can be correct data.** Plain characters with no recurring
  feature legitimately have no Motif entry; don't force-fit one to reach 100%
  coverage. Document the count as "legitimately motif-free".
- **When editing long array lists in the generator, replacing adjacent blocks can
  silently drop neighboring lines.** After every patch, diff-check that unrelated
  values (e.g. Skeleton, Wings) still exist, and let the test suite catch omissions.
- **Tests pinning exact arrays are the safety net.** When assignments change
  legitimately, update the pinned test values in the same change and add a new
  named test for the audit wave — never weaken assertions to make them pass.
- Keep source attributes untouched: draft traits stay `draft_review` and out of the
  normalized catalog until the user approves; approval is the merge step.
