# SeaDrop Multi-Wallet Public-Mint Sniper (Robinhood chain)

Verified 2026-08-18 building `~/Projects/rh-mint-bot/mintbot.py` (gen → fund → mint).
Reusable kit for hammering a PUBLIC SeaDrop mint with N wallets at T-0. Buy/relist
mechanics for Seaport are in `opensea-v2-orderbook-buy-relist.md`; this file is the
MINT side (contract -> SeaDrop singleton -> N signed txs).

## Architecture (why it beats a naive API mint)
Build `mintPublic()` calldata LOCALLY from on-chain reads so the only critical-path work
at T-0 is writing pre-signed bytes to a socket — no ~1s API round-trip. Pre-sign every
funded wallet's tx BEFORE the stage opens, spin-wait, then blast all signed txs at once
(fire-and-forget `eth_sendRawTransaction`). Same idea as morsyxbt/nft-public-mint,
rewritten clean in Python (eth-account + eth-abi + pycryptodome).

## Verified on-chain selectors + addresses (RH, chainId 4663 = 0x1237)
- SeaDrop singleton: `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5` — DEPLOYED on RH
  (eth_getCode length ~21KB). Do not assume mainnet addresses; this one is confirmed.
- `getPublicDrop(address)` = `0xbc6a629c` (eth_call on singleton, ABI word 0=mintPrice-ETH,
  1=start, 2=end, 3=maxPerWallet, 4=maxMintablePublic, 5=feeBps). All-zero = stage closed
  (correct, not an error).
- `mintPublic(address)` (single) = `0xa06cb719` — ONE param word (the NFT contract addr).
  `mintPublic(address,uint256)` (quantity) = `0x9f93f779`.
- Compute selectors from the sig string with keccak (not hardcode blindly).
- RPC: `https://rpc.mainnet.chain.robinhood.com`. urllib needs `User-Agent: Mozilla/5.0`
  (403 without it); curl is fine.

## Deterministic wallet factory (backup = keep one key)
Child keys from the funding key so regenerating N wallets always reproduces the same
addresses: `child = keccak(master_priv || i)` for i in 0..N-1. Store each keyfile
chmod 600. Regenerating N obviously REPLACES the state list — safe because deterministic.

## Funding (disburse ~3c to each)
~0.000018 ETH/wallet covers a normal mint price + RH gas (~0.02 gwei → fractions of a cent).
100 wallets ≈ 0.0018 ETH ≈ ~$3. Plain 21000-gas ETH transfers, nonce = getTxCount + i.

## Mint flow safety
1. **Dry-run is the default**; real actions need an explicit `--live` AND a wallet+contract
   that pass: chain-id probe (must equal 4663) + per-wallet affordability check
   (`balance >= price + gas buffer`; skip underfunded, don't partially fund).
2. **Public stages only.** Allowlist/FCFS `mintSigned()` needs per-wallet launchpad
   signatures — genuinely impossible locally. Don't promise it.
3. Broadcasting gotchas are IDENTICAL to the buy path (see opensea-v2-orderbook-buy-relist.md):
   - `to` must be EIP-55 checksummed or `eth_account` refuses to sign every tx.
   - `eth_sendRawTransaction` needs `"0x" + signed.raw_transaction.hex()` (no prefix = reject).
4. Proof-of-life before any real mint: one actual broadcast that returns a txid AND
   `eth_getTransactionReceipt` status=1 with the NFT transferred — not just eth_call ok.
5. Handle the `sys.stdout.getvalue()` trap — if a script accumulates output via a StringIO
   then flushes it to a FILE-backed stdout, that call raises; don't mix redirect targets.

## Free "drip" mints are NOT a slow-cron job (FABLINGS lesson, verified 2026-08-18)
Some collections gate free mints on a GLOBAL shared line (e.g. `mintInterval: 10` = one
free mint roughly every 10s across ALL wallets, capped per-wallet like `freePerWallet: 10`).
`mintFree()` takes 0 ETH value (genuinely free, only gas ~0.02 gwei ≈ $0.01) but the slot
is claimed within MILLISECONDS by other wallets. A 1-min cron that does one
simulate-then-broadcast per minute catches ~0% of slots; a continuous daemon polling
`eth_call` simulate every ~1.4s and broadcasting the instant the slot is open catches them
(verified: 2/10 → 4/10 in 15s once switched to fast polling). So:
- Slow cron = wrong tool for drip mints. Use a supervisor cron (every 1m) that keeps a fast
  ~1.4s background daemon alive, and have the cron relay the daemon's MINTED lines.
- Simulate-then-broadcast still loses races when another wallet takes the slot between the
  eth_call and the send (tx=None) — that's normal, not a bug; retry next slot.
- Never sanity-check a `--fire` daemon: use `--noop`/simulate for the test run. (I accidentally
  broadcast a real free mint during a `--fire` sanity check because the slot opened at that
  second — the check should have been noop.)
- The daemon must self-stop at the per-wallet cap (re-read `freeMinted(wallet)` and exit).

## UI / deployment security (Emad, 2026-08-18)
The user wants to "use this visually." Two deliverables split by SECURITY:
- **Static walkthrough / explainer** → deployable to Vercel PUBLIC (no keys, no backend).
- **Operational control panel that funds/mints** holds the REAL bot-wallet key and
  broadcasts ETH → **MUST stay local-only (127.0.0.1)**. Never deploy it public: anyone
  finding the URL could drain the wallet. Bind the local sever to 127.0.0.1 only.
Emad explicitly does NOT want localhost as the deliverable — deploy the SAFE static site to
Vercel and keep the money-moving UI local. Stop the local server after verifying the public
deploy (the user asked for that here).

## Local control server pattern (verified)
Single `server.py` (stdlib http.server) that imports the mintbot module and exposes
`/api/state`, `/api/gen`, `/api/fund`, `/api/mint`. Capture mintbot stdout per call
(`contextlib.redirect_stdout` into a StringIO) so the browser console shows real output.
Serve a static HTML UI from the same process. Poll state every 5s in the UI. Dry-run
default; a UI toggle flips `--live` for the rare explicit real action.
