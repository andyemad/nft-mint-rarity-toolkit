# ZARV sniper vs rh-mint-command-center — capability diff (audited 2026-08-21)

Source: X post @zarvxbt/status/2090772574028636231, 112s demo video (contact sheet),
live site zsniper.vercel.app, public repo zarvxbt/zarv-sniper @657c210 (MIT, viem-only,
zero tests). All claims below verified against actual source, not the README.

## What it has

1. **Wallet mint-stats + supply visibility** — `getMintStats(minter)` gives
   minterNumMinted / currentTotalSupply / maxSupply / maxTotalMintableByWallet; shows
   "X already minted, Y/Z after this" and a supply bar. This was our biggest gap.
2. **Seven-rule preflight** mirroring SeaDrop's `mintPublic` revert order: stage window,
   quantity, wallet cap, collection supply, fee-recipient set, recipient allowed
   (`getFeeRecipientIsAllowed`), exact payment. Reports ALL failures in one pass.
3. Discovery layer: live `SeaDropMint` event feed (20s), trending-by-recent-mints,
   gas display, watchlist with countdowns, shareable `?c=0x…` links.
4. Multi-wallet: AES-GCM/PBKDF2(310k) browser vault, parallel blast, per-wallet balances.

## Where its claims overstate the demo

- The extension does NOT call getMintStats — only the CLI does. Demo ≠ engine.
- Its scheduled fire reads the drop ONCE, then waits on a wall-clock time and sends the
  stale plan — no recheck of stage/price/supply at fire time. Queue dies with the tab.
- Fails OPEN when stats/fee-recipient checks are unverifiable (`passed: true`).
- Success = receipt status only; never verifies the expected NFT Transfer log.

## What rh-mint-command-center already did better

Persistent disk-backed queue surviving restarts, on-chain stage watching (not clock),
fresh simulation + revalidation before broadcast, atomic one-use execution claim,
exact total-exposure cap, receipt + NFT-delivery verification, pinned custom adapters,
same-origin loopback guard, real test suite + no-broadcast E2E against live contracts.

## Adopted into Mint Room (2026-08-21, all green)

- `lib/domain/seadrop-checks.ts` + `lib/server/seadrop-stats.ts`: seven-rule panel with
  tri-state ok/fail/**unknown** (unknown = contract doesn't expose data — NEVER fail-open;
  simulation still verifies before broadcast). Rendered in both future-queue and live views.
- Watchlist: `/api/watch`, `.runtime/watchlist.json` (max 24), live/upcoming state +
  price, click-to-load, 15s refresh.
- Deliberately NOT copied: browser key vault (weaker than server-side signer), manual gas
  inputs, wall-clock scheduling, uncontrolled multi-wallet blasting.
- Feed/trending left to mint-field-guide (don't duplicate intelligence layers).

## Lesson

When comparing against an X-marketed tool: clone the repo and read the code path that
actually runs in the DEMO'd surface before crediting features. Marketing READMEs describe
the CLI; the shipped extension may lack the headline safety feature.
