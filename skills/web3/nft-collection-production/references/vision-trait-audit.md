# Vision-assisted trait audit of an existing collection

Workflow for building or correcting a trait taxonomy over already-minted art
(eCalm Suites mirror, 2026-08-21). Also applies when Emad asks to "sort out
the metadata traits" of any collection with local images.

## The multi-pass pipeline (validated end-to-end)

1. **Survey pass** — contact sheets of ALL tokens (~220px cells, 12/sheet,
   PIL grid with yellow `#id` labels). Ask vision for per-token feature lists.
   Purpose: candidate generation only. Do NOT write results into the builder
   from this pass.
2. **Verification pass** — every flagged candidate re-checked at 400–500px
   face-cropped resolution (crop center 70–80% width, top ~60% height). Ask
   CONFIRM/REJECT per claimed feature with explicit rules ("eyelid line is
   NOT glasses").
3. **Tiebreak pass** — any feature where two passes disagree gets an
   ULTRA-ZOOM single-token or small-group crop (700–900px, feature-region
   crop like center 50–55% × upper 35–40%) and a pointed question naming the
   exact conflict.

## Hard rules learned from real failures

- **Vision disagrees WITH ITSELF across passes.** Same image read differently
  in different sheets (#98's "X eye" was jagged star glints; #95/#195
  halo/wings/cyclops flipped three times). Any conflict = mandatory tiebreak;
  never average or pick the first answer.
- **Low-res classification poisons data.** The user caught wholesale eye-color
  errors that came from judging eyes at sheet scale. Fine features (eye color,
  lens tint vs eyelid makeup, symbol-in-eye) need ≥400px on the FACE, often
  ≥700px on the eye region alone.
- **Re-audit the existing draft too, not just gaps.** Real errors found in
  previously "user-confirmed" data: Halo assigned to a token whose light was
  actually a UFO beam (#195); true halo token was unassigned (#95).
- **Anchor the model to grid positions.** With many cells it skips/mislabels
  (answered "#183 twice"). Restate the exact row-major order and demand the
  list in that order; ask it to enumerate labels seen if confused.
- **"No feature found" can be correct.** After full audit, tokens legitimately
  have no motif (~15% here). Empty assignment ≠ incomplete audit — record it
  as a finding, don't force-fit a trait.

## Encoding results without hand-typed ID errors

Hand-typing long token-ID arrays into a builder produced duplicates, missing
IDs, and out-of-scope IDs (a sketch duplicate and a 1/1 leaked into Basic-only
lists) on the FIRST try. Instead:

- Compute membership: define the special/exception set explicitly, then derive
  the default group by filter (`finished.filter(id => !special.has(id))`).
- Keep exhaustive coverage assertions ON (`every token exactly once`, expected
  set equality). They caught every error above in seconds — treat assertion
  failures as the normal edit loop, not accidents.
- When tests encode exact expected arrays, update them in the same change;
  a stale test array is a future false alarm.
- One shared constant (e.g. sunglassesWearers) feeding both the Sunglasses
  category and the Eye Style "Hidden by Eyewear" value prevents drift.

## Builder-editing loop gotchas (Node .mjs)

- Regex-replacing a `value("Smile", ...)` line can eat the trailing comma of
  the previous entry → SyntaxError. Re-run the build after EVERY scripted
  patch and read the actual error line before the next patch.
- `Set` args need real Sets (`new Set([...ids].filter(...))`) if the assert
  helper calls `.has()`; spread before `.filter()`.
- Python string-patching JS: match including surrounding punctuation, then
  verify by running, not by eyeball.
