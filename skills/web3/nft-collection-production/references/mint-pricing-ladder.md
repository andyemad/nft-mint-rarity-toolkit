# Mint pricing: sizing a free-start + climbing-price ladder to hit a revenue target

Reusable when Emad asks "how many NFTs / start free then increase price" to
reach a guaranteed gross (he usually wants ≥1 ETH). Real session 2026-08-19:
he iterated 24 → 1000 → 4444 supply, free start, cheap entry, and this math
settled the curve.

## The trap: a ZERO-base ladder can't hit a big target

`revenue = Σ (base + i·step)` over `paid` mints. If `base = 0`, revenue comes
only from `step`, i.e. ~`step·paid²/2`, so the average price is only **half the
top price**, and to reach 1+ ETH the top climbs absurdly high — nobody pays
that, the mint dies.

**Fix: free wave FIRST, then the paid ladder starts at a real base (not zero).**
A free wave of `free` tokens creates the live feed / "it's a steal" feel, then
the paid ladder from a nonzero base carries the revenue. This is what "start
free then go up in price" actually means done correctly.

## The formula to run

```python
USD = 2500                      # rough ETH/USD for readability (adjust)
def run(n, free, base, step):   # n=supply, free=free-wave size, base ETH, step ETH/mint
    paid = n - free
    rev  = sum(base + i*step for i in range(paid))
    first, last = base, base + (paid-1)*step
    print(f"{n} sply, {free} free | start=${base*USD:.4f} last=${last*USD:.2f} "
          f"avg=${rev/paid*USD:.3f} | rev={rev:.4f} ETH (~${rev*USD:.0f})")
```

Interpret USD "half a penny" = `0.005 / USD` ETH.

## Verified working combos (from session)

- **4444 supply, 44 free, start $0.005, step ~0.1¢ → top ~$4.40, avg ~$2.20,
  rev ~3.9 ETH** (~$9,700). This is Emad's final locked shape.
- For reference, at 4444 supply even conservative prices clear 1 ETH easily —
  the scale does the work; cheap entry is affordable once supply ≥ ~1000.

## Emad's stated preferences on mint shape

- Supply in the **thousands** (he explicitly rejected 24/50 — "people are not
  going to mint if price is so high"; wants cheap, high-volume feel).
- **Start FREE** (small wave — he corrected 444 → **44** free: small starter
  feed that reads as a steal, not a giveaway).
- **Paid entry very cheap** — he pushed down to **half a penny ($0.005)**
  start. Cheap entry = maximum FOMO, "basically free and it's climbing".
- Climb by **cents-scale steps**, land the top in the few-dollars range
  (people won't pay $10+).
- "Guaranteed ≥X" holds **only if the whole supply sells** — the climbing
  price + free feed is the lever that leans on sellout, but the room problem
  is real and separate.

## Pitfall: don't re-lecture the room problem while sizing

Emad already knows distribution is the ceiling. When he says "make it work /
shut up and make people FOMO", give him the locked numbers and BUILD — do not
re-explain why no-buyer-room caps the revenue every time he tweaks a number.
State the caveat once ("guaranteed only if all N sell"), then ship the curve.
