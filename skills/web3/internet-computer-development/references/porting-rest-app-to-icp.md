# Porting an existing REST app (FastAPI + React) to ICP — verified recipe 2026-08

Verified end-to-end locally (frontend asset canister + Rust backend canister serving the
real ALM tracker: 47 dealers, 10,742 vehicles, 48k events, 4 leads).

## Architecture that worked

- **Frontend**: existing React/Vite app becomes an asset canister. Swap the scaffold's
  `src/` for the real app; keep deps at versions the app was built with (scaffold ships
  React 19, older apps may need React 18 — peer-conflict resolution, do NOT use
  `--force`, just pin the app's original versions).
- **Backend**: Rust canister implementing `http_request` / `http_request_update` that
  serves the SAME JSON the SPA already calls (`/api/dealers`, `/api/stats`, ...).
  This means ZERO frontend API-layer changes — only `VITE_API_URL` changes at build
  time (`VITE_API_URL="http://backend.local.localhost:8000/api" npm run build`).
- **Data**: export the existing SQLite/Postgres to JSON, `include_str!` the seed files
  into the Rust binary (compiled in, no init calls, survives reinstall).
- Backend canister.yaml: `recipe: { type: "@dfinity/rust@v3.4.0", configuration: { shrink: true, candid: backend.did, metadata: [...] } }`.

## THE certification trick (biggest gotcha)

Dynamic JSON from a canister query fails the gateway's response verification
("backend_response_verification / Certification values not found") because query
responses need a certified hash tree. Building one is real work. The standard
escape hatch:

```rust
#[ic_cdk::query]
fn http_request(_req: HttpRequest) -> HttpResponse {
    HttpResponse { status_code: 200, headers: vec![], body: vec![], streaming_strategy: None, upgrade: Some(true) }
}
#[ic_cdk::update]
fn http_request_update(req: HttpRequest) -> HttpResponse { handle(&req) }
```

Returning `upgrade: Some(true)` makes the gateway re-send as an update call, which is
always trusted. Cost: every request goes through consensus (~1–2s) — fine for a
refresh-driven app, wrong for latency-sensitive APIs.

## Gotchas that cost real debugging time

1. **SQLite exports bools as ints (1/0)**. `serde_json::from_str::<Vec<T>>(...).unwrap_or_default()`
   fails the ENTIRE array silently on a bool mismatch → you get empty lists with no
   error. Add a tolerant bool deserializer:
   ```rust
   fn de_bool<'de, D: serde::Deserializer<'de>>(d: D) -> Result<bool, D::Error> {
       match serde_json::Value::deserialize(d)? {
           serde_json::Value::Bool(b) => Ok(b),
           serde_json::Value::Number(n) => Ok(n.as_i64().map(|i| i != 0).unwrap_or(false)),
           serde_json::Value::String(s) => Ok(s == "1" || s.eq_ignore_ascii_case("true")),
           _ => Ok(false),
       }
   }
   // field: #[serde(default, deserialize_with = "de_bool")]
   ```
2. **If all traffic goes through the update entrypoint, `is_update` is ALWAYS true.**
   Don't branch on query-vs-update entrypoint; branch on HTTP method
   (`is_write = method == "POST" || "PUT" || "DELETE"`) or every GET to write-able
   routes (leads/watchlist/scrape) returns the empty write response.
3. **Reinstall fails with "wasm_memory_persistence: opt Keep requires enhanced
   orthogonal persistence"** when swapping a Motoko canister (installed with
   orthogonal persistence) for Rust. Fix: `icp canister delete backend` (no --yes flag
   on delete) then `icp deploy --yes`.
4. **Candid compatibility check blocks changing the interface**: "Method greet is only
   in the expected type" — pass `--yes` to bypass.
5. **icp-cli needs Rust >= 1.8x / Cargo lock v4**: old rustc (1.77) fails; `rustup
   update stable && rustup target add wasm32-unknown-unknown`.
6. **HTTP type mismatch with ic-cdk**: ic-cdk 0.13 does NOT have
   `management_canister::http_request::HttpResponse` for serving — define your own
   `HttpRequest`/`HttpResponse` with candid derive (method, url, headers, body:
   Vec<u8>, certificate_version; status_code u16, headers, body, streaming_strategy,
   upgrade Option<bool>). `#[serde(skip)]` on a CandidType-only struct errors —
   remove it.
7. **GitHub release-asset 503 while api/raw work**: `icp deploy` downloads recipe
   templates from github.com release assets which can 503 while api.github.com /
   raw.githubusercontent.com work fine. Workaround: fetch the release ZIP from the
   same releases/download path (the .zip asset worked when recipe.hbs 503'd), unzip,
   and seed the cache: `~/Library/Application Support/org.dfinity.icp-cli/pkg/recipes/motoko/v5.1.0/recipe.hbs`.
   Verify: `icp deploy` gets past "Building canisters:" instead of failing to resolve
   the handlebars template.
8. **Local HTTP URLs**: frontend at `http://frontend.local.localhost:8000/`, backend at
   `http://backend.local.localhost:8000/` (certified domain — needs the upgrade trick),
   raw domain `http://<canister-id>.raw.localhost:8000/` bypasses verification for
   quick curls. Get the ID: `icp canister status backend` (Canister Id line).

## Seed data shapes (export pattern)

```python
import sqlite3, json
db = sqlite3.connect('alm.db'); db.row_factory = sqlite3.Row
open('dealers.json','w').write(json.dumps([dict(r) for r in db.execute('SELECT * FROM dealers')]))
```
Watch: bools come out as ints, timestamps as "YYYY-MM-DD HH:MM:SS.ffffff" strings,
NULLs as null (Option<T> in Rust handles those fine).

## Mainnet + cycles

- Faucet: https://faucet.internetcomputer.org/ (the old faucet.dfinity.org 301s there).
  Requires browser + GitHub login — the one step an agent should hand to the user.
- `icp identity new default --storage plaintext` (or keyring) creates an identity;
  the faucet credits the principal's account; then `icp deploy -e ic`.
- Local network is free/pre-funded; mainnet needs cycles top-up before deploy.

## Minimal frontend vite.config.ts (asset canister)

```ts
export default defineConfig(({ command }) => {
  if (command !== "serve") return { plugins: [react()], base: "./" };
  return { plugins: [react()], server: { port: 5173, proxy: { "/api": { target: process.env.VITE_API_URL || "http://localhost:8000", changeOrigin: true } } } };
});
```
