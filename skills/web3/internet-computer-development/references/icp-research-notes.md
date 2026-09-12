# ICP Development — Research Knowledge Bank

Verified 2026-08-12 by fetching official docs as markdown (`<path>.md`), the OpenChat
architecture doc, GitHub repos, HN Algolia, and forum.dfinity.org search API. All claims
carry their source URL. The platform changes fast — re-verify before building.

## Sources

- Docs index (everything): https://docs.internetcomputer.org/llms.txt — every page also
  available as clean markdown at `https://docs.internetcomputer.org/<path>.md`.
- Quickstart: docs.internetcomputer.org/getting-started/quickstart.md
- Canisters concept: docs.internetcomputer.org/concepts/canisters.md
- Orthogonal persistence: docs.internetcomputer.org/concepts/orthogonal-persistence.md
- Cycles costs: docs.internetcomputer.org/references/cycle-costs.md
- Resource limits: docs.internetcomputer.org/references/resource-limits.md
- Candid: docs.internetcomputer.org/guides/canister-calls/candid.md
- Clients/agents: docs.internetcomputer.org/guides/canister-calls/calling-from-clients.md
- Testing: docs.internetcomputer.org/guides/testing/strategies.md, .../pocket-ic.md
- Languages: docs.internetcomputer.org/languages/index.md, .../motoko/index.md,
  .../rust/index.md, .../rust/stable-structures.md
- dfx→icp-cli migration: https://cli.internetcomputer.org/1.1/migration/from-dfx
  (raw: github.com/dfinity/icp-cli/docs/migration/from-dfx.md)
- Azle (TypeScript CDK): github.com/demergent-labs/azle (README carries the
  security-review disclaimer), book at demergent-labs.github.io/azle
- OpenChat architecture: github.com/open-chat-labs/open-chat/blob/master/architecture/doc.md
- Agent skills (authoritative, current): https://skills.internetcomputer.org/llms.txt
- Community: forum.dfinity.org/search.json?q=<query>; hn.algolia.com/api/v1/search

## Resource limits (hard numbers)

- Ingress payload / cross-subnet msg / replicated response: 2 MiB (same-subnet
  request: 10 MiB; query response: 3 MiB).
- Instructions per call: 40B per update/heartbeat/timer; 5B per query; 300B per
  install/upgrade; 7B per round per thread.
- Memory: heap 4 GiB (wasm32) / 6 GiB (wasm64); stable memory 500 GiB/canister;
  subnet total 2 TiB; 10 snapshots/canister.
- Wasm module: 100 MiB total / 10 MiB code section; classic `install_code` limit is
  2 MiB → chunk store (`upload_chunk` + `install_chunked_code`, 1 MiB chunks) for
  larger; icp-cli does this automatically.
- Execution: canister is single-threaded (one message at a time); 4 update threads
  per subnet; ~0.75–1.5 blocks/s; 2B Wasm instructions/thread/s target.

## Cycle costs (13-node subnet; 1T cycles = 1 XDR ≈ $1.37 USD)

- Queries: free. Canister creation: ~500B cycles (~$0.68).
- Update message: 5M base + 1B per 1B instructions (~$0.0014/B-instr).
- Storage: 127,000 cycles/GiB/s ≈ $0.45/GiB/month (≈ $5.4/GiB/yr; HN claim "100GB ≈
  $500/yr" matches).
- Xnet call 260k cycles + 1k/byte; ingress 1.2M + 2k/byte. 34-node fiduciary subnets
  cost ×2.6.

## Storage model

- Heap = Wasm linear memory: fast, wiped on upgrade in Rust; auto-preserved in Motoko
  `persistent actor`.
- Stable memory = separate address space via system API: survives upgrades, up to
  500 GiB, slower (system calls per access).
- Motoko: true orthogonal persistence — `persistent actor` variables persist
  automatically; `transient var` resets on upgrade; runtime (Stellarator engine)
  manages heap↔stable mapping; `core` stdlib data structures are upgrade-safe.
- Rust: explicit — `ic-stable-structures` (StableBTreeMap/StableCell/StableLog/
  MemoryManager). DANGEROUS pattern (official docs): heap-serialize in pre_upgrade →
  fixed instruction limit → trap on large data → upgrade fails; recovery needs
  `skip_pre_upgrade` with possible data loss.
- Atomicity: per-message — trap rolls back the message. BUT if you made an outgoing
  inter-canister call mid-message and trap later, state reverts to right after that
  call was dispatched (classic bug source).
- No cross-canister atomicity. Official idempotency guide:
  docs.internetcomputer.org/guides/canister-calls/idempotency.md

## Language comparison

| | Motoko | Rust (ic-cdk) | TypeScript (Azle) |
|---|---|---|---|
| Status | Official (DFINITY) | Official (DFINITY) | Community, Release Candidate |
| Persistence | Automatic (persistent actor) | Manual (stable structures) | Manual |
| Upgrade safety | Compiler-verified stable types | Your responsibility | Your responsibility |
| Stdlib | `core` (mops.one) — supersedes `base` | crates.io | npm (subset works in wasm) |
| Best for | Dev speed, small/medium, agents | Production, complex logic | Prototypes, TS teams |
| Risks | Small hiring pool, breaking stdlib renames | Upgrade-safe storage learning curve | Not security-reviewed |

Motoko notes: syntax = ML-family hybrid by Andreas Rossberg (WebAssembly designer);
`?T` options, `#tag` variants, `switch` pattern matching, `:=` assignment; async/await
for inter-canister calls; compiler at github.com/caffeinelabs/motoko (Caffeine Labs
maintains it, plus mops, VS Code extension, vessel). Mops pins compiler in mops.toml:
`[toolchain] moc = "1.9.0"`.

Rust notes: `#[query]`/`#[update]`/`#[init]`/`#[pre_upgrade]`/`#[post_upgrade]`/
`#[heartbeat]`/`#[inspect_message]`; `ic_cdk::export_candid!()`; must set
`crate-type = ["cdylib"]`; no tokio (use CDK executor + `ic_cdk::futures::spawn`);
no std::time/env vars/threads; `getrandom` needs a custom shim; wasm-bindgen crates
don't work.

## Toolchain

- icp-cli: `icp new` (templates via --subfolder hello-world/rust/motoko + --define
  backend_type=rust), `icp network start -d` (local PocketIC replica, pre-funded),
  `icp deploy`, `icp canister call/status/list`, `icp identity new/principal/export`,
  `icp project show` (expanded recipe view). Environments: `icp deploy -e ic` = mainnet.
- Recipes: versioned build templates `@dfinity/motoko@v5`, `@dfinity/rust@v3.3`,
  `@dfinity/asset-canister`, `@dfinity/prebuilt` (github.com/dfinity/icp-cli-recipes).
- ic-wasm: binary shrinker (shrink + gzip + chunk store for >2 MiB).
- Candid: `.did` files; TS bindings via `@icp-sdk/bindgen` (Vite plugin available);
  Rust via ic-cdk-bindgen or candid-extractor; `didc` CLI (check/encode/decode/subtype).
- Agents: `@icp-sdk/core/agent` (browser+Node; was `@dfinity/agent`), `ic-agent` (Rust),
  community: agent-go, ic4j-agent (Java), agent_dart, ICP.NET, icp_agent (Elixir), agent-c.
- Testing: mops test (Motoko, mo:test pkg); cargo test with trait-based DI mocks;
  PocketIC (pocket-ic crate / @dfinity/pic / Python) — deterministic in-process
  replica with time travel; Docker containerized test networks via icp.yaml; canbench
  (instruction/heap/stable-memory benchmarks vs committed baselines).
- ICP Ninja (icp.ninja): browser IDE, 5 MB / 2 canisters, deploys live 20 min.

## Hello world file tree (from `icp new` + `icp deploy`)

```
hello-icp/
├── icp.yaml              # canisters: [backend, frontend]
├── mops.toml             # [toolchain] moc; [canisters] backend = "src/main.mo"
├── .icp/                 # cache/ (gitignore) + data/ (commit: mainnet IDs)
├── backend/
│   ├── canister.yaml     # recipe @dfinity/motoko@v5.0.0
│   └── src/main.mo
└── frontend/
    ├── canister.yaml     # recipe @dfinity/asset-canister (React+Vite)
    └── app/              # src/, dist/, package.json, vite.config.ts
```
Frontend gets backend ID at runtime via `ic_env` cookie: `getCanisterEnv()` from
`@icp-sdk/core/agent/canister-env`; icp-cli injects `PUBLIC_CANISTER_ID:<name>` env
vars into every canister at deploy. Mainnet Candid UI:
`https://a4gq6-oaaaa-aaaab-qaa4q-cai.icp.net/?id=<canister-id>`

## OpenChat architecture (canonical multi-canister design, Rust)

Repo: open-chat-labs/open-chat (architecture/doc.md). ~100 canisters:
- Canister-per-user: user canister holds direct chats, group references, auth
  principal, acts as token wallet (hotkey to NNS/SNS neurons).
- Canister-per-group: members, roles, text messages (attachments via OpenStorage);
  member limit 100k; index canisters create/top-up/upgrade in batches (dev or SNS only).
- user_index / group_index: global registries (principal→userId, usernames, CAPTCHA
  on register); maintain pools of pre-created user canisters for fast signup.
- OpenStorage: index + dynamic bucket canisters, content-addressed, ref-counted
  blobs, per-user byte allowances (0.1 GB free w/ SMS verify, pay to 1 GB).
- notifications canister, online-users aggregator, cycles dispenser (c2c_request_cycles;
  burns ICP→cycles when low; SNS proposal tops up), assets canister.
- Client APIs: Candid. Internal canister-to-canister APIs: MessagePack (evolution).
- Every canister exposes public /metrics and /logs endpoints (memory, cycles balance,
  wasm version, git commit).
- Off-chain leftovers (AWS): SMS relay + web-push relay — planned to move on-chain
  via HTTPS outcalls. Custom domain via forked boundary-node service worker.

## Caffeine / Caffeine Labs

- caffeine.ai: "Create brilliant apps and websites through chat" — AI agent platform
  that writes and deploys production apps as canisters on ICP; DFINITY-launched
  Oct 2025 (VentureBeat; ~$200M+ backing per HN).
- Caffeine Labs (github.com/caffeinelabs) now maintains the whole Motoko toolchain:
  motoko compiler, vscode-motoko, mops, motoko-core, vessel, motoko-base, skills.
- Forum report (2025-08): alpha rewrites the entire app for a one-line change —
  early-stage UX caveat.

## Gotchas — real developer complaints (thread names + dates, forum.dfinity.org)

- "The biggest problem with the IC - InterCanister Calls" (2022-03): inter-canister
  calls render upgrades impossible in many cases.
- "ICP Uptime Guarantees" (2025-10): constant subnet upgrades take canisters down,
  multiple times/day, 503 no_healthy_nodes.
- "Feature suggestion: upgrading several canisters" (2024-07): no atomic multi-canister
  upgrade; cross-canister transactions aren't atomic ("The Token Problem", 2021).
- "Watch out for foot guns with canister upgrades" (2021-11) + "If pre_upgrade fails,
  revert to earlier snapshot" (2022-12): upgrade hooks are the #1 failure surface.
- "Motoko Base Library Changes" (2025-01, 79 posts): base→core breaking renames;
  DFINITY goal: reduce learning curve + improve AI codegen. "Motoko 2024 Roadmap"
  (2024-06): "steep learning curve when entering the Motoko ecosystem" (their words).
- "OPINION: stop inventing new esoteric protocols/tooling" (2024-07): adoption barrier
  from non-standard tooling; "I need to hire a developer to build on ICP" (2025-04):
  Motoko devs "in limited supply amongst the general dev population".
- "How can top-up be this broken and unstable?!" (2022-10): cycles top-up eats ICP;
  "How to add more cycles" (2021-06): cycles friction. Freezing threshold stops
  canisters when balance low.
- "How to run internet identity locally without docker?" (2023-01): local II setup pain.
- "SNS canister upgrade executed, but the canister wasn't upgraded" (2025-07): silent
  rollback on SNS-managed upgrades; "Repeated downtime on front end and backend
  canister" (2022-07): protocol upgrades are NOT zero-downtime, by design.
- "Caffeine AI buttons wont function" (2025-08): alpha rewrites whole app per change.
- HN (2020-08, RcouF1uZ4gsC on the Motoko launch): orthogonal persistence is "the
  Godzilla of all leaky abstractions" — skepticism quote.
- "Rust canister, Storage is limited to about 300MB, why" (2022-03): memory-limit
  confusion; "What happens when a canister hits the memory heap limit?" (2022-05).
- "All You Dev's Are Toast - ChatGPT knows Motoko" (2022-12): early LLMs couldn't
  write Motoko — hence DFINITY's agent-skills push (skills.internetcomputer.org).

## Latency reality

- Queries ~200ms (single node); updates 1–2s per concepts docs, 2–4s per agents doc
  ("~200ms" vs "~2–4 seconds" table in calling-from-clients.md). Plan for 1–4s on
  state changes; chat apps use optimistic UI + caching.
