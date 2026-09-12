# Decaying-price NFT mints

A block-decaying mint charges a price that falls after each reset and snaps back to the start price after a successful mint.

## Exact integer economics

```solidity
elapsed = block.number - lastResetBlock;
decayed = decayPerBlock * elapsed;
price = decayed >= startPrice - floorPrice
    ? floorPrice
    : startPrice - decayed;
```

For Crypto Cougars:

- start: `0.1 ether`
- floor: `0.0001 ether`
- decay: `0.003 ether` per block
- supply: 10,000
- every successful mint sets `lastResetBlock = block.number`

### Boundary calculation: use ceil, not truncated division

`(0.1 - 0.0001) / 0.003 = 33.3` blocks. Solidity integer arithmetic does not make the floor appear at block 33:

- delta 32: `0.0040 ETH`
- delta 33: `0.0010 ETH`
- delta 34: raw subtraction would cross the floor, so clamp to `0.0001 ETH`

`blocksToFloor()` must use ceiling division:

```solidity
(remaining + decayPerBlock - 1) / decayPerBlock
```

Never describe this tuning as “33 blocks to floor.” It is 33 full decays plus a partial final interval; the first floor block is delta 34. Encode both boundary assertions in contract tests and in a separate exact-wei proof script.

## Production-grade local contract shape

The verified local milestone is `~/Projects/decay-mint/`.

Use OpenZeppelin ERC-721 rather than a mechanism-only token stub:

- `ERC721` for ownership, approvals, transfers, safe minting, ERC-165, and metadata behavior.
- `Ownable2Step` for safer administration.
- `ReentrancyGuard` on mint/refund and withdrawal paths.
- Checks-effects-interactions: validate price/supply, allocate token and seed, reset price state, then `_safeMint`, then refund.
- Custom errors for sold out, underpayment, invalid price config, failed refund, and failed withdrawal.
- Explicit events for mint price/seed, reset, price changes, and withdrawal.
- Refund all overpayment; if the receiver rejects the refund, revert the whole mint atomically.
- Keep test-only supply mutation in an inherited harness. Production exposes only an internal hook, not a public bypass.

Deterministic trait seeds such as `keccak256(collectionSeed, tokenId)` are reproducible and easy to audit, but predictable. State this honestly; do not call them secure randomness. Rough rarity rules (for example, `seed % 10 == 0`) need deterministic tests and should not be sold as guaranteed exact counts unless the complete 10,000-token distribution is enumerated.

Owner price tuning is useful during a local milestone but is a production centralization risk. Before any approved launch, decide whether to freeze it, timelock it, or remove it. This is separate from contract correctness.

## Minimum acceptance matrix

Write RED tests before replacing the prototype, then require:

1. Exact start price and one-block decay.
2. Delta 33 = `0.001 ETH`; delta 34 = floor.
3. Floor clamp remains stable after additional blocks.
4. Successful mint resets the clock.
5. Underpayment reverts; overpayment is refunded and not retained.
6. Supply cannot exceed 10,000.
7. Invalid price configuration and non-owner configuration revert.
8. Owner-only withdrawal succeeds and sends the full balance.
9. ERC-721 transfer, approval, safe receiver, and interface behavior.
10. Nonexistent metadata reverts; minted metadata decodes to valid JSON and on-chain SVG.
11. Seed/traits are reproducible.
12. Reentering receiver cannot mint twice.
13. Rejecting ERC-721 receiver and rejecting refund receiver revert atomically.
14. Frontend source fails closed outside localhost and rejects every chain except 31337.

Run compile, focused/full tests, formatter, linter, exact integer proof, dependency audit, bytecode-size check, a real browser E2E, and independent spec/security reviews. Fix findings, then rerun the complete gate. A static source assertion is not browser evidence.

## Real localhost browser E2E without downloading Chromium

Use `playwright-core` with an installed Brave/Chrome executable:

1. Spawn `node_modules/.bin/hardhat node`; wait for TCP 8545.
2. Run a deployment script that refuses every chain ID except 31337 and writes the local address/ABI into frontend config.
3. Serve only on `127.0.0.1`; wait for the HTTP port.
4. Launch installed Brave/Chrome headlessly by `executablePath`.
5. Navigate to the page and wait for an explicit “local contract connected” state.
6. Click mint using an unlocked Hardhat test account.
7. Assert supply `0 → 1`, a live price, decoded token name/traits, an SVG data URI, and zero `pageerror` events.
8. Save a full-page screenshot and inspect it visually for clipping, overlap, blank art, and stale state.
9. Close browser and terminate both child services in `finally`; verify ports are closed.

When connection times out, include the DOM status, browser console, and page errors in the thrown error. This exposed a durable integration pitfall: ethers v6's `ethers.min.js` distribution is ESM and fails in a classic `<script>` with `Unexpected token 'export'`; use `ethers.umd.min.js` for a classic global `ethers`, or use an explicit `type="module"` import.

Do not retain, display, or document Hardhat's default private keys. They are local fixtures, not user credentials.

## Current verified artifact

As of 2026-08-20, the project contains:

- `contracts/DecayedMint.sol`: OpenZeppelin ERC-721 with on-chain SVG/JSON metadata.
- `test/CryptoCougars.test.js`: contract/security acceptance suite.
- `test/frontend.test.js`: localhost/chain/config static safety checks.
- `scripts/deploy-local.js`: chain-31337-only deployment/config writer.
- `scripts/e2e-local.js`: fresh-node headless-browser mint proof and cleanup.
- `price_proof.js`: exact BigInt boundary/reset proof.
- `demo.html` + `frontend/app.js`: polished local chain-backed mint interface.
- `ARCHITECTURE.md` and `README.md`: safety boundary, risks, and runbook.

The complete `npm run check` gate passed with 17 tests, formatter/linter, exact proof, browser mint, and zero production dependency vulnerabilities. The screenshot is at `artifacts/e2e/crypto-cougars-local.png`.

## Safety boundary

Local deploys and Hardhat transactions are verification fixtures. Never deploy to a real-money chain or enable live ETH minting until the separate distribution/demand gate passes and Emad explicitly approves the external consequence. No review preference should become a blocker: if the user waives a named reviewer, continue with direct tests and independent quality/spec verification rather than stopping implementation.