# eCalm eye-color audit — verified findings (2026-08-21, in progress)

Follow-up to the trait case study: the user rejected the first Eye Style pass
("you got a lot of the eye colors wrong"). Full re-audit of all 99 visible-eye
finished tokens. Verified verdicts so far (ultra-zoom adjudicated):

## Colored irises (NOT black — must leave "Normal Dot")

| Token | Verified iris color | Notes |
|---|---|---|
| 80  | Neon green, glowing | Black skin w/ green outlines; green IS the eye |
| 95  | Red | One giant central eye + ~8 small red satellite eyes; cyclops-style |
| 100 | Black with red reticle rings inside | NOT red eyes — red targeting circles inside black pupils |
| 103 | White spirals on dark | Spiral patterns IN the irises |
| 105 | Rainbow concentric rings | pink/green/yellow/white ring stacks both eyes |
| 107 | Medium blue iris | white sclera visible |
| 117 | Yellow/gold iris with green pupil | oversized cartoon eyes |
| 122 | Multicolor equalizer-bars pattern in one/both eyes | purple/pink/cyan vertical bars |
| 130 | Purple/mauve iris | white ghost frog |
| 140 | Blue oval eyes + anaglyph red/cyan 3D-glasses outlines | |
| 141 | Brown iris | tan frog |
| 147 | Left (viewer) eye red mechanical/targeting; right black | cybernetic |
| 153 | Big light blue-white glossy ovals with dark pupils | oversized |
| 160 | BOTH eyes blue iris | purple-skinned polka-dot frog |
| 170 | Exactly one cyan/blue eye, other black | heterochromia |
| 172 | Left green iris, right blue iris w/ sclera | |
| 173 | Dark red/maroon iris (golden Pepe) | NOT amber/gold |
| 182 | Dark-blue iris with lighter blue ring | light blue frog |
| 184 | Red irises containing black spiral swirls | also Frown expression |

## Resolved as genuinely black/normal

98 (jagged white shapes are star/sparkle highlights, NOT X marks — X-eye claim
was wrong at every zoom level), 106 (purple = sunglasses lenses, eyes dark
behind), 111 (black eyes with BLUE EYELIDS/eyeshadow above), 155, 164 (black
irises, white sclera), 101 (rainbow only in face stripes, not iris),
157 (purple only in striped skin around eyes), 186 (solid silhouette, NO eyes
at all → needs explicit "No Eyes" value), 196/197/198/200 (196 normal;
197/198/200 have notable white sclera — candidate for a Sclera value).

## Unresolved at pause (user said pause mid-audit)

- Large-sclera-vs-normal calls for: 104, 108, 136, 161, 162, plus re-checks of
  119, 154, 174, 195 flagged in the final sweep.
- Whether to add a separate "White Sclera" value vs fold into existing values.

## Lessons encoded

See SKILL.md pitfalls: iris-color-vs-surroundings question, eyewear-reflection
disambiguation, silhouette check, whole-axis re-audit on user correction.