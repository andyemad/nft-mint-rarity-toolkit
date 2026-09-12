# FOMO mint page — the pressure-trigger stack (STILL UP case, 2026-08-19)

Emad explicitly wants a mint page engineered to exploit the degenerate FOMO
impulse: "people are degenerate and will FOMO if you make it good enough."
The honest-gate caveat lives in SKILL.md — but once he says build, this is
the pattern that makes a page sell itself, even on a small supply. Reference:
`~/Projects/still-up-mint/index.html` (the FOMO rebuild).

## The six pressure triggers (all on one page)

1. **LIVE MINT FEED (social proof)** — random-ish wallet hex addresses visibly
   minting every ~2s (`0x3af…92d minted #002`). Strangers grabbing tokens while
   you watch = "am I missing it?" Feeds scroll, newest on top, cap ~9 rows.
2. **PRICE CLIMBS WITH EVERY MINT (scarcity + regret)** — bonding-curve ladder
   in JS: `price(n) = start + step*(n-1)`. Next token costs more than the last,
   painted live. Not fake urgency: the math itself punishes waiting.
3. **SUPPLY BAR DRAINING** — 0→24 fill bar in real time plus "X/24 MINTED"
   text. A hard, visible deadline.
4. **COUNTDOWN CLOCK** — 24h (or shorter) ticking down in HRS/MIN/SEC. Timer +
   drain = decide now.
5. **GROWING JACKPOT** — gold, climbing every tick; `pool += price * share`
   per mint, one winner at sellout. Greed + the "could be me" draw.
6. **SOLD-OUT REVEAL** — the moment supply hits max it snaps to "SOLD OUT —
   REVEAL SOON", clock zeros, button disabled. Finality is the FOMO capstone:
   buy before it's gone, not after.

## The psychology chain it rides
social proof → scarcity → urgency → jackpot greed → fear of missing out.
Remove every reason to wait; give a reason to act NOW. Works on this crowd
because it's not an argument, it's a pressure field.

## Wire it as a scaffold first
Build the page self-playing (setInterval spawning simulated mints at a realistic
cadence, e.g. 85% chance per 2.6s) so Emad can SEE it work before any contract
deploy. When deployed, the fake feed rows/price/jackpot swap to real reads via
`eth_newHeads` / `getLogs` — the JS writes to the same DOM ids either way.
Serve locally with `python3 -m http.server <port>` for review (localhost only,
nothing public, nothing on-chain); `open http://127.0.0.1:<port>/`.

## Interactive MINT CURVE EXPLORER (teach Emad how the curve works)

When Emad says some variant of \"help me visualize how the mint price goes up\",
don't just let the auto-play feed run — add a **drag-to-mint slider** he can
move to FEEL the ladder. This landed well 2026-08-19. It's a plain `<input
type=range min=0 max=SUPPLY>` plus a readout row, all driven by one recompute
function bound to the slider's `input` event:

- **MINTED SO FAR** — slider position.
- **PRICE OF NEXT MINT** = `base + paidCount*step` (what the next buyer pays).
- **LAST MINT PAID** = price of the mint at the current position (FREE while
  inside the free wave).
- **REVENUE COLLECTED** = `Σ(base+i·step) for i in 1..paidCount`.
- A hint line that labels which zone the thumb is in (free → cheap early →
  mid-run climbing → FOMO peak → sold out), e.g. \"within the 44 FREE mints —
  no revenue yet\" vs \"🔥 late run — price near top\". The zone labels make the
  mechanic obvious at a glance.
- Redraw the curve SVG **only up to the slider position** so dragging animates
  the line climbing — that one drag IS the understanding (early cheap → late
  expensive → the spread drives FOMO).

Teach with a specific drag sequence: 44 (still FREE) → 45 ($0.005, revenue
begins) → 500 (~$0.18) → 2500 (~$1) → 4444 ($4.40, ~3.9 ETH). Reference:
`~/Projects/still-up-mint/index.html` (explorer block + `exPaint()`).

**Pitfall (real): the auto-play feed and the explorer draw the SAME curve SVG
and fight.** The page's live `paint()` rewrites `#curveLine` every spawn while
the explorer's `exPaint()` also rewrites it on drag. Symptoms: dragging works,
then a feed tick jumps the curve back out from under your thumb. Fixes: have
`exPaint` write to a SEPARATE overlay/polyline, OR pause the auto-feed while
the slider has been touched (a `usedExplorer` flag that stops the feed's paint
calls). Either way, the explorer should win once interacted with.

## ANTI-FAKE-MECHANISM RULE (hard, learned 2026-08-19)
Never advertise a mechanic the contract does not implement. The first STILL UP
page promised a 1-in-24 ALPHA ticket, a live jackpot pool, and a 0.0039 bonding
curve — the agent-gated contract did NONE of them. Claude had to strip them
("honest copy") because shipping an advertised-but-implementable-nowhere prize
is how you accidentally run a rug and burn the brand. Either:
- build the mechanic INTO the contract with real on-chain logic + tests, or
- edit the page to say only what the contract actually does.
A flashy page is fine; a lying page is a reputation fatality. If you reverse a
page to honest copy (jackpot/curve/alpha removed), say so plainly — you are
removing a lie, not a feature.
