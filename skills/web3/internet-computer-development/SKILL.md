---
name: internet-computer-development
description: "Use when building or researching ICP blockchain apps."
---

# Internet Computer (ICP) Development

Research-verified 2026-08 against docs.internetcomputer.org (full knowledge bank with
source URLs: `references/icp-research-notes.md`). The platform moves fast — the official
docs explicitly warn agents not to rely on pre-training knowledge. Before writing ICP
code, re-verify against the docs `.md` endpoints and https://skills.internetcomputer.org
(DFINITY's authoritative agent-readable skills).

## Critical: the toolchain was renamed (most tutorials are stale)

- `dfx` → `icp-cli` (npm `@icp-sdk/icp-cli`); `dfx.json` (JSON) → `icp.yaml` (YAML).
  Nearly all third-party tutorials and many older official pages still say "dfx".
- Command map: `dfx start --background` → `icp network start -d`; `dfx deploy` →
  `icp deploy`; `dfx deploy --network ic` → `icp deploy -e ic`;
  `dfx canister call X m '(...)'` → `icp canister call X m '(...)'`;
  `dfx canister id X` → `icp canister status X --id-only`; `dfx identity get-principal`
  → `icp identity principal`. Full migration guide: cli.internetcomputer.org/1.1/migration/from-dfx
- Install: `npm install -g @icp-sdk/icp-cli @icp-sdk/ic-wasm ic-mops` (Node.js 22+).
  `icp network start -d` boots a pre-funded local replica — no wallet/cycles setup needed.

## Platform model (canister vs EVM — the mental shift)

- Canister = Wasm module + persistent state, replicated across a 13-node subnet.
  Upgradeable by controllers (dev principal, multisig wallet, or SNS DAO); empty
  controller list = immutable.
- Update calls: go through consensus, ~1–2s (often 2–4s in practice), cost cycles,
  may mutate state. Query calls: one node, ~200ms, free, but responses are NOT
  threshold-signed — use certified variables when reads must be verifiable.
- Users don't pay gas — canisters pay cycles (1T cycles = 1 XDR ≈ $1.37).
- Canisters serve HTTP (asset canister = frontend/CDN), call external APIs (HTTPS
  outcalls), sign on BTC/ETH/Solana natively (chain-key cryptography), run timers.
  No external database: "your app IS the database" (orthogonal persistence).

## Language choice (details in references)

- **Motoko** — official, purpose-built. `persistent actor` = all actor variables
  survive upgrades automatically (true orthogonal persistence; `transient var` for
  ephemeral state). Stdlib `core` (supersedes `base` — migration guide exists).
  Packages via mops.one. Best for dev speed, small/medium apps, agent-friendly.
- **Rust + ic-cdk** — `#[update]`/`#[query]`/`#[init]`/`#[pre_upgrade]` macros;
  persistence is explicit via `ic-stable-structures` (StableBTreeMap, StableCell,
  StableLog, MemoryManager). NEVER heap-serialize large state in `pre_upgrade`
  (fixed instruction limit → upgrade aborts, may need `skip_pre_upgrade`). Best for
  production-scale apps (OpenChat is Rust). No tokio/threads/env-vars/std-time —
  use ic-cdk timers, `ic_cdk::api::time()`, compile-time `env!()`, raw_rand.
- **TypeScript via Azle** — community CDK, Release Candidate, README disclaimer
  "has not yet undergone intense security review". Stable mode default; experimental
  mode = Node.js stdlib/HTTP servers (explicitly not secure/stable). Good for
  prototypes/TS teams; be cautious with production funds. `npx azle new hello_world`.

## Hello world (verified commands)

```bash
npm install -g @icp-sdk/icp-cli @icp-sdk/ic-wasm ic-mops
icp new hello-icp --subfolder hello-world --silent && cd hello-icp
icp network start -d
icp deploy
icp canister call backend greet '("World")'   # -> ("Hello, World!")
icp network stop
```

Motoko backend (`backend/src/main.mo`):
```motoko
persistent actor HelloWorld {
  var greeting : Text = "Hello, ";
  public func setGreeting(prefix : Text) : async () { greeting := prefix; };
  public query func greet(name : Text) : async Text { return greeting # name # "!"; };
};
```
Project layout: `icp.yaml` (lists canisters) + per-canister `canister.yaml` with a
versioned recipe (`@dfinity/motoko@v5`, `@dfinity/rust@v3.3`, `@dfinity/asset-canister`,
`@dfinity/prebuilt`) + `mops.toml` (compiler pin + source path). Commit `.icp/data/`
(mainnet canister ID mappings); ignore `.icp/cache/`. Frontend discovers backend IDs
via the `ic_env` cookie (`getCanisterEnv` from `@icp-sdk/core/agent`).

## Porting an existing REST app (verified 2026-08)

Real port done: FastAPI+SQLite backend + React/Vite frontend → single ICP project
(frontend asset canister + Rust backend canister serving the SAME `/api/*` JSON, zero
frontend API-layer changes). Key points:

- Seed the canister with `include_str!` on JSON exported from the old DB — no init
  calls, survives reinstall.
- Serve dynamic JSON as `http_request_update` and return `upgrade: Some(true)` from
  the `http_request` query — this bypasses response-certification entirely (query
  responses fail gateway verification with "Certification values not found").
- Branch on HTTP method, not query-vs-update entrypoint (all traffic goes through the
  update entrypoint once you use the upgrade trick).
- SQLite exports bools as 1/0 — a `bool` field with `unwrap_or_default()` silently
  empties the whole array; use a tolerant `deserialize_with` bool.
- Swapping a Motoko canister for Rust fails install ("wasm_memory_persistence: opt
  Keep") — `icp canister delete backend` then `icp deploy --yes`. Interface changes
  need `--yes` past the Candid compat check.
- GitHub release-asset 503 while api/raw work: seed the recipe cache manually from the
  release ZIP (`~/Library/Application Support/org.dfinity.icp-cli/pkg/recipes/...`).
- Faucet moved: https://faucet.internetcomputer.org/ (faucet.dfinity.org 301s there);
  needs a browser GitHub login — hand that step to the user.

Full recipe, code snippets, and error transcripts: `references/porting-rest-app-to-icp.md`.

## Toolchain & testing

- Candid (`.did`) = language-neutral IDL; Motoko generates it automatically, Rust via
  `candid-extractor` + `export_candid!()`. Safe interface upgrades follow Candid
  subtyping rules (`didc subtype old.did new.did` to verify).
- Agents: JS `@icp-sdk/core/agent` (successor to `@dfinity/agent`; docs js.icp.build),
  Rust `ic-agent`, community agents for Go/Java/Dart/.NET/Elixir/C.
- Testing pyramid: unit tests (`mops test` for Motoko; cargo test with dependency
  injection/mocks for Rust) → PocketIC (in-process deterministic replica; Rust
  `pocket-ic` crate, JS `@dfinity/pic`; the local network runs on it) → deployed
  tests on containerized networks. `canbench` for instruction-count regression
  benchmarks (perf regressions literally cost money — 40B instruction cap/update).

## Architecture patterns (official guidance)

Start with a SINGLE canister (recommended for most apps); split per-service when
hitting limits (2 MiB/message, 40B instructions, 4 GiB heap) or for separation of
concerns; canister-per-subnet for horizontal scale. Canister-per-user is
experimental and expensive — OpenChat is the only known full implementation.
Cross-canister updates are NOT atomic — idempotency patterns are mandatory for
anything financial. See references for the OpenChat canister map.

## Gotchas (real developer complaints; threads in references)

1. Inter-canister calls can block upgrades ("biggest problem on the IC").
2. No cross-canister atomicity / no atomic multi-canister upgrades.
3. `pre_upgrade` traps on big heap serialization → upgrade failure/data loss.
4. Subnet protocol upgrades take canisters down (503 no_healthy_nodes) — no zero-downtime.
5. Tooling churn: dfx→icp-cli rename, Motoko base→core breaking stdlib renames — pin versions.
6. Cycle top-up friction; freezing threshold stops messages when balance is low.
7. 2 MiB message-size limit; Wasm >2 MiB needs chunk store (icp-cli auto-handles).
8. Latency reality: queries ~200ms, updates 1–4s — not web2.
9. Motoko hiring pool is small; steep learning curve (DFINITY's own roadmap thread says so).
10. Azle not security-reviewed; most tutorials are dfx-era stale.

## Research path (reproducible)

- Docs as markdown: `curl https://docs.internetcomputer.org/<path>.md`; full index at
  `/llms.txt`; old `internetcomputer.org/docs/*` URLs 301 to homepage.
- Agent skills (current, authoritative): https://skills.internetcomputer.org/llms.txt
- OpenChat architecture (open source, canonical multi-canister design):
  raw.githubusercontent.com/open-chat-labs/open-chat/master/architecture/doc.md
- Community sentiment: forum.dfinity.org/search.json?q=... + hn.algolia.com (see the
  terminal-web-research skill for the curl patterns).

## Support files

- `references/icp-research-notes.md` — full knowledge bank: resource limits, cycle
  costs, storage model, language comparison, hello-world tree, OpenChat & Caffeine
  architectures, gotcha threads with names/dates, and all source URLs.
