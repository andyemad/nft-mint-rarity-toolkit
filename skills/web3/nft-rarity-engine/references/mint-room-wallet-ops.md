# Mint Room wallet-ops fixes (2026-08-22 session)

Context: Emad hit "RPC HTTP 429" red errors on every wallet row + "Distributed to
0/13 wallets" in Mint Room /wallets. Both were the SAME transient cause, and the
fixes are now in the codebase.

## Diagnosis path that worked

1. Vision-analyze both screenshots first — got verbatim error text ("RPC HTTP 429"
   per balance cell) without asking Emad anything.
2. Re-test the suspected rate limit directly: 30 parallel `eth_getBalance` calls
   from python → all OK. Proves the 429 was transient, not a standing limit.
3. On-chain proof nothing was lost: OG nonce identical at `latest` and `pending`
   (no stuck txs), fresh wallets still held only dust. Distribute's per-send
   `eth_getTransactionCount` calls had 429'd → every send threw pre-broadcast.

## Fixes applied (in rh-mint-command-center)

- `lib/server/rpc.ts`: rpc() now retries 3x with backoff (600ms/1200ms) on
  429 / 5xx / timeout before throwing.
- `app/api/wallets/route.ts` distribute action: nonce fetched ONCE via
  eth_getTransactionCount(from,"pending") then incremented locally per send —
  13 sends = 1 RPC call instead of 13 (the burst that triggered throttling).
- Verify with `npm run check` (55 tests) + `launchctl kickstart -k gui/$(id -u)/com.patelai.rh-mint-room`, then curl `/api/wallets` and count error rows.

## THE REAL ROOT CAUSE (found later same day — do not trust the 429 story alone)

After the retry/backoff fix shipped, distribute STILL failed 13/13. Direct POST
to the route exposed the true error: ethers v6
`missing provider (operation="sendTransaction", code=UNSUPPORTED_OPERATION)`.
The signers were built as `new Wallet(readKey(...))` — key but NO provider — so
every send threw before broadcasting regardless of RPC health. The 429s had been
MASKING this all along; fixing the throttle alone changed nothing.

Fix: shared `const provider = new JsonRpcProvider(RPC_URL, {chainId:4663,
name:"robinhood"}, {staticNetwork:true})` at module scope in wallets/route.ts
(`RPC_URL` exported from rpc.ts), passed into BOTH the distribute signer and the
per-wallet consolidate signers. Verified live: distribute 0.00001 ETH × 13 =
confirmed 13/13 on-chain, balances visible in /api/wallets.

Lessons:
- **A "fixed" failure isn't fixed until you re-drive the actual operation** (here:
  POST the distribute endpoint and count confirmed hashes). Retrying under a
  different error is progress, not success.
- When every item in a batch fails with an IDENTICAL non-network error, suspect
  construction/wiring (missing provider, wrong chainId), not rate limits.
- Pre-existing red test unrelated to your change: tests/ui.test.tsx "offers a
  bounded queue..." expects label /maximum price per nft/i which exists nowhere —
  belongs to the other session's queue work. Don't chase it during wallet fixes.

## Consolidate post-mortem (later 8/22 — batching + exact-balance reverts)

Emad reported consolidate working in odd chunks: "a batch of 3, then failed,
then a batch of 5" instead of all at once. Two stacked causes:

1. **Serial receipt-waiting.** Old code waited ≤60s for each wallet's receipt
   inline before the next send → minutes of RPC polling per request → mid-loop
   rate-limit failures hit random chunks. Fix (in wallets/route.ts): broadcast
   ALL sweeps first collecting hashes, then ONE bounded receipt-poll phase at
   the end (~45s deadline, 3s interval, splice confirmed/failed as found).
2. **Exact-balance sweeps revert on fee movement.** Sending `balance − gasCost`
   is knife-edge: RH base fee rose between the balance read and broadcast, and
   ethers v6 defaulted to EIP-1559 envelopes whose overhead counts against
   funds. Error signature: `insufficient funds for gas * price + value: address
   ... have X want Y` where want−have ≈ small fee delta. Fix: legacy `type: 0`
   txs in sendFrom, pass the SAME gasPrice used in cost math into the sender
   (lockedGasPrice param), and subtract ≥2x gas headroom from sendable —
   leaving dust is fine and expected.

Verified end-to-end: after fixes, one consolidate run broadcast fabw_4/7/10
(pending through the poll window) and a follow-up balance read showed ZERO
wallets holding funds — everything swept to OG.

Also learned: another agent session was editing the same route.ts concurrently
and briefly reverted the provider fix — re-grep shared files before assuming a
fix is still present. And a kickstart'd service may take ~10s to listen on
:3000 again; curl api:000 right after restart means "still booting", retry
before diagnosing.

## Pitfalls

- Next.js route handlers doing serial sends: never fetch nonce/gasPrice per item
  inside the loop; batch once, increment locally.
- A transient RPC outage produces MULTIPLE seemingly-unrelated symptoms (balance
  errors AND failed distribution). Diagnose the shared dependency first — but keep
  digging if failures persist after the transient cause clears.
- ethers v6 signers REQUIRE a provider to broadcast; `new Wallet(key)` alone can
  sign offline only. Any server-side send path needs `new Wallet(key, provider)`.
- ethers v6 defaults to EIP-1559 tx envelopes; for exact-balance sweeps use
  legacy `type: 0` and lock the gasPrice so cost math and tx agree.
- `timeout` command does not exist on this Mac (no coreutils) — use the terminal
  tool's own timeout parameter instead.
- execute_code may be blocked for arbitrary python in cron profiles; write a
  scripts/*.py file and run it via terminal instead.
