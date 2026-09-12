# Worker ingestion wiring + parallel-subagent verification (established 2026-08-13)

The WRITE side of the live pipeline (raw logs → canonical facts) and the rules for running
parallel coding subagents on this repo. The READ side (routes ← D1 read repo) is documented
separately in `references/d1-read-wiring.md`.

## Worker decoder wiring (raw logs → canonical mint facts)
`persistent-worker.ts` runs each raw log through the decoder pipeline before committing:
`mint-decode` (ERC-721 `Transfer` from zero address / ERC-1155 `TransferSingle`/`TransferBatch`)
→ `mint-classify` (three-way `MintClassification = "paid" | "free" | "airdrop"`, added in
`mint-classify.ts`) → `mint-group` (transaction grouping). Facts then commit via
`D1CanonicalRepository.commitBlock`.

Integration test: `persistent-worker.mint.integration.test.ts` feeds raw log fixtures through
the worker and asserts canonical facts carry correct token IDs, amounts, classification, and
grouping.

## Parallel-subagent verification
This repo is driven by parallel `delegate_task` pushes. Rules that keep it safe:
- **Never trust the self-report summary** — verify on disk: run the full gate yourself
  (`npx vitest run` + `npx eslint src` + `npx tsc --noEmit` + `npm run build`) and confirm the
  expected files actually changed.
- **`status=timeout` ≠ failed.** A child that times out at the 600s wall may have COMPLETED its
  edits. `tail` its live transcript (`~/.hermes/cache/delegation/live/<delegation_id>/task-N.log`)
  and check `git status` before re-dispatching.
- **Every subagent must be told**: (1) NEVER `git commit`/`add`/`clean`/`checkout` — the working
  tree is intentionally uncommitted; (2) strict DISJOINT file ownership (name the exact files it
  owns and the files that are read-only) so parallel children never edit the same shared file
  (`types.ts`, `d1-repository.ts`).
- Partition parallel children by domain (e.g. `src/lib/monitor/` vs `src/lib/indexer/` vs the
  route files) — disjoint ownership is what lets three concurrent agents land without conflict.
