# Unified completion planning for Mint Room

Use this when merging an older implementation plan with a newer agent handoff or delegating Mint Room work to a weaker coding model.

## Reconcile before planning

1. Read the current `HANDOFF.md` from the end backward; later dated sections supersede stale prompts and test counts.
2. Read the existing implementation plan, then inspect the live diff and rerun the baseline gates. Do not copy claimed counts into a new plan without verification.
3. Separate **already-fixed**, **still-open code**, **live-only blocked**, and **unrelated dirty work**. A handoff instruction is not proof of approval or completion.
4. Preserve unrelated dirty files with narrow patches. Never clean, reset, stash, or rewrite a dirty file wholesale.

## Preserve two execution models

Mint Room has two distinct paths:

- **Ordinary multi-wallet OSNM-Z:** runtime stage discovery, engine-managed fee policy, and optional post-mint forwarding. Preserve `RECIPIENT_ADDRESS=BOT_WALLET`, `FEE_AUTOMATIC=true`, key/address verification, and explicit selected wallets.
- **Opening-block public SeaDrop:** a separate prepared TypeScript path. Decode the public stage on-chain, persist a key-free immutable launch plan, sign only in memory, broadcast one logical transaction per selected wallet concurrently, and monitor receipts separately. Do not force these timing requirements into every legacy engine module.

## Funding is a preflight contract

- Never use historical ETH amounts as UI policy.
- Mirror the engine's current reserve formula in one tested server module using bigint.
- Preflight selected wallets, source-wallet capacity, stage cap, `totalSupply`/`maxSupply`, gas envelope, and RPC certainty before spawning a live engine.
- If any explicitly selected wallet is underfunded, block the reviewed set; do not silently shrink it.
- Underfunding is `blocked`, not generic `failed` and never a successful no-op.
- A live stage time window is not proof of remaining supply.

## Delegation packet for a weaker model

A self-contained plan should include:

- Correct absolute repo path and explicit wrong-path warning.
- Verified branch, dirty-tree inventory, baseline test/typecheck counts, and files that are off-limits.
- Existing invariants that must survive.
- TDD-sized tasks with exact files, payloads, formulas, commands, and expected outcomes.
- Side-effect boundaries: no commit/push, funds, live arm, broadcast, service restart, skill install, or Discord post.
- A gate ledger and a mandatory final handoff listing exact files, commands, counts, deviations, remaining blockers, and current `git status --short`.

## Discord/Hermes adapter pattern

Keep Hermes as transport and approval controller. Give it a deterministic loopback JSON CLI for safe commands (`status`, `inspect`, `preflight`, `rehearse`, `queue`, `run-status`, `cancel`, `review-live`). Stdout should be exactly one JSON object and must never contain keys, raw signed transactions, keyfile paths, or secrets. `review-live` returns exact bounded details with `approvalRequired: true` and stops; do not let a delegated implementation install the skill, restart Hermes, arm, or broadcast.

## Verification standard

- Focused tests after each task.
- Full typecheck, test, lint, build, and no-broadcast E2E at the end.
- Inject an RPC spy that fails if a real `eth_sendRawTransaction` occurs.
- Record actual outputs in the gate ledger.
- Do not call the system live-verified while funding, receipt handling, or post-mint forwarding remain untested on-chain.
