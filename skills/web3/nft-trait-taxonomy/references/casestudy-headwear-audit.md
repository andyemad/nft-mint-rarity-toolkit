# the case-study collection Headwear audit (2026-08-21, v2 after the user's review)

Promoted headwear out of Motif into its own EXCLUSIVE category. v1 (19 values
incl. None) was corrected in bulk by the user; v2 final taxonomy below (23 values).
Every assignment verified with head-region zooms (crop top ~55–62% of image,
upscale, labels drawn in BLACK BOXES — bare yellow text drifted on busy sheets).

## Final assignments (v2, user-corrected)

| Value | Tokens |
|---|---|
| None | 72 tokens |
| Black Baseball Cap | 88 |
| Blue Baseball Cap | 94, 142 |
| Black Reverse Cap | 27, 149 |
| Blue Reverse Cap | 111, 104, 144 |
| Red Reverse Cap | 123, 165 |
| Propeller Beanie | 139 |
| Beret | 112 |
| Bandana | 113 |
| Wizard Hat | 198 |
| Bridal Veil | 85, 96 |
| Bow | 121, 128, 178 |
| Flower(s) in Hair | 151, 179 |
| Afro | 99, 106 |
| Long Flowing Hair | 114, 132, 153 |
| Curly / Bangs | 162 |
| Buns / Pigtails | 135 |
| Clown Wig | 143 |
| Cat Ears | 200 |
| Fox / Animal Ears | 146 |
| Alien Antennae | 167 |
| Devil Horns | 52, 97, 124, 131, 155 |
| Sun Ray Spikes | 117 |

## User corrections vs the model's v1 read (ALL of these were model errors)

- #144 and #104 wear reverse caps — vision passes called both "none"/"antennae".
- #149 is a baseball cap backward, NOT a beanie.
- Caps must be split BY COLOR as separate trait values (Black/Blue forward,
  Black/Blue/Red reverse) — collectible-grade users want color-level values.
- #122: headphones are ear-wear → Motif, never Headwear.
- #167 gets "Alien Antennae"; #195 has NO antennae (its alien is a UFO scene
  motif). The "alien" is antenna-shaped protrusions on the frog itself.
- #117 is NOT devil horns — renamed "Sun Ray Spikes" at the user's instruction when
  he rejected the name; spikes radiate sun-ray style from the head.
- #114 = long flowing hair (unique hair value kept separate from buns/bangs).

## Flip-flop log (model reads that kept flipping)

- #117: "crown" / "devil horns" / "dark spiky hair" / "sun-ray spikes" across
  four passes. Lesson: when no name satisfies the user, ask THEM to name it
  instead of re-guessing.
- #112: "bun", "white flower", "white fluffy hair", "white beret" — final beret
  (Eiffel Tower bg corroborates).
- #139: "white beret w/ bird", "party hat", "clown hair" — final propeller
  beanie (propeller visible only at zoom).
- #123: cap color flipped red/white/blue; final blue hair + red reverse cap.
- #132: bandana / beanie / white hair / blue hair — final Long Flowing Hair.
- #149: bangs / black beanie / purple cap / black backward cap — user verdict wins.
- #165: "nothing" / "red beanie" / "red backward cap" — final Red Reverse Cap.
- #104: plain blue frog / dark-blue backward cap / antennae — final Blue Reverse Cap.

## Builder/test mechanics that bit

- **Stale companion set bug:** `headwearWorn` (the exclusion set feeding the
  computed "None" value) was left with v1 membership after rewriting the value
  list — coverage assertion reported nonsense `repeated=` ids (tokens present in
  BOTH their real value AND None). Whenever a category has a computed catch-all
  value, update the exclusion set IN THE SAME EDIT and grep for every copy of
  the set literal first (`grep -n "<setName> = new Set"` — this file had TWO
  copies after a scripted replace; dedupe before debugging assertions).
- Removing values from Motif while adding Headwear required updating every test
  asserting `motif["Baseball Cap"]` etc.; assert `"X" in motif === false` for
  each migrated value so they cannot silently return.
- A scripted string-replace inserted `const headwear` outside callback scope →
  duplicate-declaration SyntaxError. Run `node test/file.mjs` directly;
  `npm test` hides syntax errors behind generic fail.
- deepEqual is order-sensitive: `[111, 104, 144]` fails against `[104, 111, 144]`.
  Match the builder's literal order or sort before comparing.
- Exclusive-category dedup order used: flowers beat veil/bangs for 151/179;
  hair beats cap for 123 (cap recorded here for provenance).
