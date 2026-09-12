---
name: nft-exit-discipline
description: Use when the user trades or sells NFTs, or decides on an exit.
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [nft, trading, exit, momentum, break-even]
---

# NFT Exit Discipline

Sourced from repeated sessions: the user trades NFT momentum, prefers liquid /
high-volume markets, and exits fast. His recurring leak is exiting at or below
break-even during the volume window instead of at a profit target.

## Hard rules (state these plainly, no lecture)

1. NEVER list a paid mint below break-even.
   - Break-even = mint price ÷ 0.89 (covers ~10% royalty + ~1% fee).
   - Also factor in any gas / cross-chain transfer costs to compute real cost.
2. Prefer liquid / high-volume markets. Avoid illiquid holds — the user hates
   being stuck holding NFTs that don't move.
3. Exit fast, at a profit target, not at break-even "just to be safe." The
   volume window is when to take the profit.
4. Before any exit, state the current price, the break-even (with royalty/fee
   math), and the profit target. Verdict frame: net $ vs time/risk, not hype.

## When to apply

- the user says he's trading, selling, listing, "exiting," or asks about a mint.
- Any NFT / mint decision where price or break-even is on the table.

## Copy / framing

- Do NOT hype-then-deflate. Give honest up-front numbers (race, cost, risk).
- Keep it to 2–4 lines of the actual math and the call. No lecture, no hand-holding.
- This is his call — give the number and the recommendation, he decides.

## Verification

- Any exit recommendation states: current price, break-even after fee math,
  profit target, and liquid-vs-illiquid note.
