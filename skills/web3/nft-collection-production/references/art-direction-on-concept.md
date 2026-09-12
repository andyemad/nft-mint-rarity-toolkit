# STILL UP art direction — ON-CONCEPT **and** GENUINELY AESTHETIC (2026-08-20, rev 2)

The 2026-08-20 experimental sequence produced THREE art attempts plus Claude's
reference. The rev-1 note here said flat-vector "won" — that was wrong. the user's
actual verdict this session: the flat-vector trading-desk portraits were
rejected ("this sucks"), the ORIGINAL glitch/pixel sleepless-trader tokens had
more presence, and the true ask was "just something really aesthetic." The
lesson is about the QUALITY BAR, not which file happened to be produced.

## What the user actually wanted (corrected)

- When he says "see what you can come up with," he means **show a strong,
  genuinely AESTHETIC direction** — not re-skin the existing brand, not a
  lecture, not flat-vector cap-art. Do not anchor on re-drawing STILL UP; he may
  be asking for something else entirely. Confirm the SUBJECT before spending an
  hour (he'll pick flatly and you lose one cycle; better to put that as a
  10-second question).
- "It doesn't have to be 3d, just something really aesthetic." The bar is
  **PRESENCE**: texture, mood, light, grain, depth — the thing that makes art
  feel expensive and memeable. A clean-flat-cap is NOT it.
- He rated the **original pixel/datamosh sleepless-trader tokens as better than
  the flat-vector ones** — because they had texture and a vibe, not because they
  were pixel-perfect. Grain + datamosh + mood beat sterile flat fills.

## The honest capability ceiling

Flat-vector PIL drawing fundamentally caps at "clean and colorful" — it cannot
reach "cinematic/rich" (volume, lighting, depth-of-field, readable film grain).
That is exactly why Claude's 3D mechs read as higher quality. If the user asks for
"really aesthetic" and medium is open, the real routes are:
- **A real renderer** (Three.js/WebGL procedural, Claude's league) — the only
  way to actually hit "expensive-looking." Bigger build (hours), best yield for
  mint demand.
- **Painterly 2D with real texture** (scanned-etching / charcoal / oil-brush,
  paper grain) — the texture *becomes* the aesthetic; flat vector can't do it
  but PIL with brushes/noise can. Cheaper than 3D.
- State the fork honestly and stop rather than burning a third iteration on the
  same flat target. the user values being told "flat caps at this level" over a
  third flat attempt.

## What still holds from rev 1 (verified true)

- On-concept + expressive + memeable beats technically-polished-but-generic:
  Claude's abstract 3D mechs were self-consistent but generic/off-concept for a
  themed collection. That half of the rule is still valid.
- **But on-concept is necessary, not sufficient.** On-brand subject + flat
  sterile execution = still rejected. the user wants BOTH on-concept AND real
  aesthetic quality.

## PIL gotchas specific to this session's "aesthetic" attempt (new-art/night.py)

1. **Vignette via `im.paste(dark_rgba, (0,0), mask)` BLACKS OUT the lit region.**
   `paste` copies the source image's RGB channels (black) scaled by mask alpha —
   it REPLACES pixels, it does not alpha-blend. This silently made 3 near-black
   renders before diagnosis. To darken edges use `alpha_composite`, OR compute a
   mask that is 0 at centre and >0 only at edges:
   ```python
   vig = Image.new("L",(W,H),0); vd=ImageDraw.Draw(vig)
   vd.ellipse([-W*.25,-H*.25,W*1.25,H*1.25], fill=255)
   vig = vig.filter(ImageFilter.GaussianBlur(120))
   vig = vig.point(lambda v: int((255-v)*0.30))   # 0 centre, ~30 edges
   im.paste(Image.new("RGBA",(W,H),(0,0,0,255)), (0,0), vig)
   ```
   (mask is the ONLY thing that should be non-flat here; do not pass a dark RGBA
   as the paste source expecting a fade.)
2. **Diagonal gradient bands must span the FULL canvas diagonal**, or most of the
   frame stays black. A `±400` perpendicular offset leaves most rows untouched.
   Use `span = hypot(w,h)*1.2` and sweep a thick line from `-span` to `+span`
   along the perpendicular.
3. **Exposure gets crushed by too-dark palettes + heavy vignette + dense grain.**
   A near-black bg1 (e.g. `#05070d`) plus an aggressive vignette plus full-frame
   dark grain = functionally invisible portraits (vision reports "pure black /
   no subject"). Start with LIFTED gradients of LIGHT (bg1 mid-tone → bg2
   saturated), luminous skin, and subtle light grain. Check a single token's
   pixel histogram (Counter over samples) BEFORE batch-rendering — the contact
   sheet only amplifies the exposure problem.
4. `Image.alpha_composite(im, (x, y))` takes ONE dest tuple, not two args
   (`Source must be a list or tuple` otherwise) — applies to every overlay,
   including ones placed via arithmetic like `(W//2+280, H-280)` (watch that the
   sed/rename of `, x, y)` → `, (x, y))` catches expression forms too).
5. Named-key entry values (`a1`/`a2`, not `accent1`/`accent2`) after a palette
   redesign; convert hex→RGB once after skin pick:
   `p = {k: hex2rgb(v) for k,v in PAL[skin].items()}; p["ink"]=hex2rgb(INK)` and
   never re-run hex2rgb on an already-converted tuple.
6. Deterministic per-token `random.Random(seed*2654435761 & 0xFFFFFFFF)` so the
   same seed always gives the same PNG + traits (metadata can't drift from render).

## Cash Dogs experiment: technically coherent, aesthetically rejected

The Cash Dogs reference was correctly identified as neon-on-black cartoon art,
but the hand-coded corgi implementation did **not** approach its illustration
quality. the user's verdict was explicit: "absolutely terrible," "MS Paint slop."
He noted that even movement toward Adam Bomb Squad's polished designer-toy /
streetwear illustration quality would have been acceptable.

What the experiment proved:

- A black background, bloom, crisp silhouette rim, and cute subject can create
  contrast and thumbnail readability. They cannot create illustration craft.
- Vision checks saying "cohesive," "consistent," or "viable PFP" only proved
  that the generator had no obvious structural breakage. They did not prove
  that the art was good. Do not translate defect-free into aesthetically
  successful.
- Iterating anatomy, props, hats, glows, and palettes after the base character
  already reads as primitive geometry wastes time. The rendering method is the
  bottleneck.
- Adam Bomb Squad-level direction requires deliberate line weight, shape
  design, volume, surface finish, graphic confidence, and integrated traits.
  Use a real illustration/image model or a human-made master character, then
  derive overlays. Do not try to approximate that bar with Pillow primitives.
- Never say "this is the one," "it landed," or "collection-ready" before the user
  approves the benchmark. His aesthetic verdict outranks auxiliary vision.

The neon/bloom code below is retained only as a prototype/debugging reference
for low-cost glow effects—not as a recommended route to premium collectible
art.

**Prototype neon-bloom technique (`new-art/corgi.py`):**
```python
def glow_bloom(img, color, radius=26):
    glow = Image.new("RGBA", img.size, (0,0,0,0))
    a = img.getchannel("A")
    tint = Image.new("RGBA", img.size, color+(255,))
    tint.putalpha(a)
    tint = tint.filter(ImageFilter.GaussianBlur(radius))
    glow.alpha_composite(tint, (0,0))
    return glow
```

Anatomy debugging remains valid for prototypes: overlapping head/body shapes,
connected limbs/tail, and coherent z-order prevent floating parts. That is a
minimum correctness check, not an aesthetic achievement.

## Researching a live collection before designing

When the user says "something like this [URL]", do NOT design from memory — pull
the actual collection page. Useful keyless endpoints (OpenSea API v2, no key):
- Collection stats/logo/banner: `api.opensea.io/api/v2/collection/<slug>` (this
  one works without a key; gives name, supply, floor, volume, owner_count,
  image_url, banner_image_url).
- **`/nfts` and `/listings/all` require an API key** (`Missing an API Key`) —
  so for item-level art/traits use the browser page screenshot path instead:
  `open -a Safari <url>` then `computer_use` capture (vision mode) to read the
  style, grid, and any traits column.
- Collection media (seadn.io) is often **AVIF** — convert to PNG before
  `vision_analyze`: `python3 -c "from PIL import Image; Image.open(i).convert('RGB').save(o+'.png')"`.

## Files (failed prototypes retained for diagnosis)
- `~/Projects/mint-page/new-art/corgi.py` and
  `new-art/output/corgi-1-16.png` are rejected prototypes. Keep them only as
  evidence of the hand-coded-primitive quality ceiling; do not present or
  extend them as the collection direction.
