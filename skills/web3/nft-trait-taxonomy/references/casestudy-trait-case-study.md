# the case-study collection Suites trait audit — case study (2026-08-21)

Concrete instance of the workflow in SKILL.md. Collection: 200 tokens on
Ethereum (0x7deea…5b0e), 191 Basic + 9 user-confirmed 1/1s; 111 "Finished
Character" Basics eligible for character-level traits; 80 pencil-sketch tokens
excluded from most categories.

## Final category structure

Exclusive (one value per applicable token):
- **Artwork** (all Basic): Pencil Sketch 80 / Finished Character 111.
- **Background** (finished): 44 values, mostly exact-recurring families
  (CGraffiti, Spotlight Clouds, Gradient Drips...) plus individually named
  unique backgrounds.
- **Skin Color** (finished): 9 values. Green dominant (42).
- **Lip Color** (finished): 12 values incl. "No Standard Lips".
- **Eye Style** (finished minus sunglasses wearers): Normal Dot 83 /
  Oversized Cartoon 5 (#117,143,153,192,194) / White Sclera 4 (#79,107,155,164) /
  Spiral-Swirl 3 (#103,105,184) / X Eye #98 / Cyclops #95 / Cybernetic #147 /
  Glowing Red #199. Sunglasses wearers get "Hidden by Eyewear" and are excluded
  from other eye-style values.
- **Expression**: Smile 99 / Frown 5 (#109,111,162,184,192) / Smirk 4
  (#27,159,188,195) / Open Shout 2 (#128,196) / No Mouth #199.
- **Sunglasses** (12 wearers only): Red 4 · Purple 2 · Pink 2 · Orange, Blue,
  Green, Black 1 each.

Non-exclusive motifs: Flames, Golden, Cosmic Glow, Alien/UFO, Hair/Headpiece,
Afro, Baseball Cap, Backward Cap, Bandana, Glasses (18), Devil Horns, Smoke,
Woman-Eyelashes, Floral Accessory, Chain Necklace, Spiked Choker, Companion,
Paint Drip, Halo, Glitch/Pixel, Headphones, Caution Tape, Star Patches, Bow,
Mustache, Clown, Wizard Hat, Cat Ears, Ghost Body, Wedding Attire, Skeleton,
Wings, Bubbles. ~16 finished tokens legitimately carry no motif.

Clothing (7 repeated outfit templates, exclusive among themselves): Floral
Outfit, Sweater Vest, Blazer, Ribbed Turtleneck, White Ruffle Top, Black V-Neck,
Blue Overalls.

## Contradiction log (zoomed tiebreak wins)

| Token | Contact-sheet claim | High-res verdict |
|---|---|---|
| 95 | "flat mouth cyclops with wings+halo" then later "two eyes, no halo" | ONE giant central eye + ~8 small red eyes, black halo ring, white wings, NO mouth |
| 195 | "halo above head" | No halo — UFO with light beam top-left; two normal eyes; smug smile → Smirk + Alien/UFO only |
| 98 | pass1 "X eye", pass2 "normal" | X eye confirmed at zoom (left eye drawn as X) |
| 146/147/191 | cybernetic eye bounced between tokens | Only #147 has the red targeting eye + spiked choker |
| 127,140,154 | glasses flagged by low-res pass | REJECTED — eyelid lines, not glasses |

## Decision rules that worked (put verbatim into vision prompts)

- "Glasses = visible frames or tinted lenses over the eyes; a plain eyelid line
  is NOT glasses."
- Mouth taxonomy: smile = upward-curved closed/open grin; smirk = asymmetric
  one-sided raised corner; frown = downward-curved sad; shout = wide open
  laughing or O-shaped; flat = straight line or absent.
- Eye taxonomy: normal = plain black dot pupils, no visible white; white-sclera =
  visible white around pupil; oversized-cartoon = eyes dominate face, often
  colored iris; spiral = swirl pupil; X-eye = eye drawn as X; cyclops = exactly
  one central eye; cybernetic = mechanical/targeting implant; glowing-red = red
  glowing circles without pupils.

## Implementation notes

- Builder: `scripts/build-basic-traits.mjs` writes `data/analysis/
  basic-visual-traits.draft.json` (status draft_review) with revision_notes for
  every accepted AND rejected decision.
- Assertions in builder: assertExclusiveCoverage for every exclusive category;
  Hidden-by-Eyewear set must equal the sunglasses-wearer set exactly.
- Tests (`test/basic-traits.test.mjs`) pin exact representative arrays so edits
  fail loudly; test the Hidden group separately from covered tokens (counting it
  against itself is a test bug, not a data bug).
- Scope guards that caught real mistakes: token 138 is a sketch-tier duplicate of
  21 (not eligible for character traits); token 145 is a 1/1 outside Basic scope.
  Check tier + duplicate status before adding any ID to a new category.
