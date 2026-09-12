# Per-collection sniper params (v3, designed 8/25)

Extends the global-params model in `reveal-sniper-controller-integration.md`.
the user's ask: each collection gets its OWN parameters, edited through a clean
per-collection GUI in the control room instead of one shared caps file.

## Layering design (the part worth copying)
Two-tier params with different scopes:

- **Wallet-level safety stays GLOBAL** (`~/.hermes/rarity/snipe_params.json`):
  daily_cap_eth, reserve_eth, poll_secs, and global max_buys. Never per-col —
  two simultaneous reveals must never be able to double-spend past these.
- **Per-collection knobs** (`~/.hermes/rarity/<name>/params.json`, created on
  first save): max_buys (per collection), max_per_buy_eth, top_ranks,
  floor_mult. These are the knobs that genuinely differ per collection.
- **Resolution order**: per-col value → global value → DEFAULT, clamped by the
  same PARAM_BOUNDS either way. No per-col file = exactly previous behavior
  (backwards compatible by construction).

Daemon enforcement checks BOTH ceilings: col_buys >= col max_buys (counted from
state buys where `b["collection"]==col.name`) AND wallet totals vs global caps.

## the control room surface
- `sniper-params.ts`: PER_COL_DEFAULTS/PER_COL_BOUNDS mirror clay_sniper.py
  PARAM_BOUNDS; `COL_PARAMS_FILE(name)`; readColParams/readAllColParams reuse
  clampAll. Existing global exports untouched (status route depends on them).
- `/api/sniper/params` GET → `{global, collections: Record<name, params>}`;
  POST → `{scope: "global"|"<name>", params}`; unknown name ⇒ 404 validated
  against readSnipedCollections(). Loopback guard unchanged on both.
- Page: one card per sniped collection (4 fields + own Save) plus a clearly
  labeled "wallet-level caps (all collections)" card. Reuse the draft-string
  input pattern religiously (the `0.015→15` keystroke pitfall).

## Probe pattern for daemon param changes (no broadcast, no restart needed)
clay_sniper.py is safe to importlib-load (`main()` guarded): use
`.venv/bin/python` + `importlib.util.spec_from_file_location`, then call
`load_params("testcollection")` against a temp per-col file to prove resolution +
clamp. **Cleanup is safety-critical**: a leftover test `params.json` IS a live
override on the armed daemon — delete it in the same breath, verified by ls.

## Fan-out pattern used (worked well)
Parallel delegate_task pair: (1) daemon agent owns clay_sniper.py edits + probe,
(2) repo agent owns sniper-params/route/page/tests + `npm run check` gate.
Parent alone does deploy (build + kickstart) and the daemon restart — keeps the
armed process out of subagent hands. Gates ledger + spec live in the repo:
`.hermes/plans/per-collection-sniper-params.md`, `GATES-percol-sniper.md`.

Status at writing: both implementers dispatched, deploy + armed-daemon restart
(code change ⇒ restart required, unlike params-only edits) still pending.
