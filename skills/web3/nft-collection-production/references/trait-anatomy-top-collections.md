# Trait-system architecture: what the bits and parts look like in top collections

Emad's framing (2026-08-22), which corrects how style study should be framed:
"it's more about the traits and variants and how these all come together with
those so you can learn from the bits and parts not the whole." When profiling
a reference collection, the deliverable is TRAIT ANATOMY — slot structure,
variant-pool shapes, weighting, cross-layer coherence — not an art critique of
whole tokens. Whole-token vision analysis still helps, but the trait
distribution data is the primary study object.

All numbers below are measured from live on-chain metadata (150-token random
samples per collection, 2026-08-22) via `scripts/trait_sampler.py`, NOT from
marketing pages or guesses.

## 1. Slot architecture

| Collection | Slots | Shape |
|---|---|---|
| Shadow Wolves | Face, Hat, Shirt, Tier | Exactly 4 fixed slots on every token |
| HOWLERZ | Background, Type, Eyes, Hat, Outfit, Accessory, Back Bling | 3–7 slots, VARIABLE presence |
| Pudgy Penguins | Background, Skin, Body, Face, Head | Exactly 5 fixed slots |

- Fixed slots = clean rarity math, uniform metadata.
- Variable presence is itself a rarity lever: a token that simply HAS no hat,
  or has Back Bling when most don't, gains rarity without any new art.
- Every collection has exactly one foundational slot that does the heavy
  lifting (see §2).

## 2. The Tier/Type slot (the biggest single lesson)

One "base body" slot overrides everything and carries the rarity CLASS system:

- Shadow Wolves `Tier` (9 variants): Shadow 1 21% / Shadow 2 19% / Primal 2 17%
  / Primal 1 13% / Sinister 1 9% / Sinister 2 8% / Chaos 1 8% / Chaos 2 4% /
  Scholar 1%. Two-axis naming (mood-class × generation number) doubles as
  rarity branding.
- HOWLERZ `Type` (19 variants): 13 Standard colors ≈60–75% combined
  (Green 13 / Blue 13 / Yellow 12 / White 11 / Red 10 / Black 8 /
  Monochrome 5 / Chroma 1) + special bodies Robot 7% / Bone 6% / Ghost 4% /
  Fire 4% / Shock 3% / Puffer 1-3 ~1% each / Matrix 1% / Chalk 1% / Ice 1%.

Design rule for our own sets: give one slot a wide common base (~60-75%) plus
a long tail of structural specials down to ~1%. Common tokens stay collectible
because the class system is legible; grails live in this slot.

## 3. Variant-pool shapes (the long tail)

Measured pool sizes and top-item share:

- Shadow Wolves Hat: 58 variants, top item (Broken) only 5%, then a massive
  ~30-item tail at ≤1% each (Tesla, Fishbowl, Davy Jones, Blood Moon,
  Flame Head…). Shirt: 68 variants, same pyramid.
- Shadow Wolves Face: 28 variants, flatter distribution (top ~7%, floor ~1%)
  because faces are the personality engine.
- HOWLERZ Eyes: 27 variants (Troll 9% → Zoinked/Wavy/Flames 1%). Outfit: 31
  variants (Tactical Vest 9% → Dirt Shirt 1%). Accessory: only 5 variants but
  concentrated (Earring 36% / Triple 28% / Bone Nose Ring 16% / Nose Ring 12%
  / Bone Earring 8%).
- HOWLERZ Background: 21 variants — flat colors (Mustard 9% … Purple/Blood 1%)
  plus pattern families Wavy/Dots/Stripes/Rainbow at 2-7%.
- Pudgy Penguins: much tighter pools (~15–20 variants/slot, e.g. Background
  ~12 colors, Head hats ~20).

The recurring shape: roughly 60% of tokens wear the top few commons, ~25%
mid-tier, ~15% spread across a deep near-1/N grail tail. Pool SIZE varies by
slot role: identity slots (Eyes/Face/Tier) get many variants with flatter
curves; accessory slots get either huge tails (hats/shirts) or tiny
concentrated pools (earrings).

## 4. Cross-layer coherence (named sets)

Named sets recur ACROSS slots and read as intentional outfits:
- Shadow Wolves: Jester Pink hat + Jester Pink shirt; Astro + Astro;
  Blood Moon + Blood Moon; Cat Costume + Cat Costume; Celestial Blue/Pink
  hat + Celestial shirt; Masquerade both layers; Boss both layers.
- HOWLERZ pairs special Types with themed accessories/outfits.

Matching set = bonus rarity feel with zero extra code: just draw the same
motif on two slots and (optionally) note it in metadata naming so rarity tools
and humans can spot it.

## 5. Background as free rarity depth

HOWLERZ's 21 backgrounds show backgrounds are the cheapest axis: flat colors
for commons, pattern families (Wavy/Dots/Stripes/Rainbow sunburst) as mid-tier,
near-1% colors as grails — no character art touched. Shadow Wolves instead
keeps bg constant per tier family; Pudgy uses plain color-only backgrounds.
Patterned-background families are the underused trick worth stealing.

## 6. Checklist when designing our own trait system

1. Pick slot count 4–6; decide fixed vs variable presence (variable adds a
   free rarity lever).
2. Design ONE Type/Tier slot: ~13 commons (60-75%) + 6+ structural specials
   down to ~1%.
3. Identity slot (eyes/face): 20–28 variants, flattest curve, carries mood.
4. Wardrobe/hat: 50–70 variants if going for Shadow-Wolves-style depth, with
   a deliberate ≥25-item 1% tail of grails.
5. Small accessory pool (≤6 variants) is fine — concentration reads as
   signature, not laziness.
6. Backgrounds: add 3–5 pattern variants beyond solid colors.
7. Cross-slot named sets: pick 4–6 motifs that appear on 2+ slots.
8. Verify total combos >> supply AND sample-render the actual joint
   distribution (some combos must be genuinely rare, not theoretically rare).
