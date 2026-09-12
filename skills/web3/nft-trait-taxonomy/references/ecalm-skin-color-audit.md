# eCalm Skin Color audit — 2026-08-21 session

User: "you still haven't distinguished the skin colors well enough." Original
9-bucket draft (Green, Blue/Cyan, Pink/Red, Purple, Yellow/Orange/Gold,
Beige/Tan, White/Gray, Black/Dark, Multicolor/Patterned) was too coarse and had
misplacements.

## Final 19-value taxonomy (111 finished tokens, exclusive, exact coverage)

Green 38 · Mint Green [158,161,170,191] · Olive Green [166,172] ·
Blue [121,136,142,171] (incl. navy #136) · Cyan [90,97,104,111,120,177,182] ·
Pink [85,148] (#148 is magenta-pink, was buried in red) ·
Red/Maroon [52,92,128,155,164,188] · Purple [106,117,149,163,184,187]
(#117 deep magenta-purple — was "Pink/Red") · Gold/Yellow [93,173,193] ·
Peach/Orange [196] · Beige/Tan [141,146,151] ·
White [95,96,100,107,110,119,130,132,140,147,150,152,153,194,197,199] ·
Gray [77,98,109] · Black [27,79,80,84,103,118,169,174,181,186]
(#118 black skin w/ white swirls — was Multicolor) ·
Polka Dots [89] · Rainbow Stripes [101] · Pixel Pattern [105] ·
Clown Rainbow [143] · Striped Pattern [157,160].

## Method that worked

1. Dump current category from draft JSON; build labeled thumbnail sheets of
   questionable + full groups (~340px cells, yellow #id labels).
2. Programmatic pixel probe: resize to 300x300, sample head region grid
   (y 60–200, x 90–210), quantize RGB to /24 buckets, report top clusters.
   Caught background bleed (rgb(183,68,102) = pink BG reading as cheek).
3. Broad vision pass: terse `#id: skin` for every token on sheet.
4. Targeted second-opinion pass on ONLY disputed IDs with either/or questions.
5. Comparative ranking pass for shades within a family ("rank lightest→darkest:
   mint/pale/standard/muted/olive/dark") — absolute color asks flip between
   passes; relative framing is stable.
6. Rewrite values in builder, let assertExclusiveCoverage catch stragglers
   (#117, #172 surfaced as missing → single-pair zoom tiebreak settled them),
   update tests that referenced old value names ("Blue / Cyan" → "Blue").

## Flip-flop log (why two passes per call)

- #129: "standard green" then "pixelated bright green"; pixel probe showed
  same palette as #1 → Green.
- #172: "green" vs "olive/yellow-green" — pair-zoom vs classic green confirmed
  olive (chartreuse, scaly texture). Was previously Yellow/Orange bucket.
- #117: pink → patterned → purple across three passes; final: deep
  magenta-purple skin, spiky sun headpiece irrelevant to skin axis.
- #120: cyan → light blue → purple/lavender; landed Cyan (pale blue family).
- #109/#132/#153/#194/#197: navy-tint suspicion rejected twice — white skin,
  blue only in shading/lips.
