---
name: onchain-claim-reverse-engineering
description: Use to solve on-chain mint, claim, and puzzle gates.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [web3, nft, mint, puzzle, reverse-engineering, onchain]
    related_skills: [ethereum-data-pipelines]
---

# On-Chain Claim Reverse-Engineering

Use when the user points at a project (usually a website or X post) and asks "how do I mine/claim/get this?" — where "mine" means solving a gate to claim an on-chain reward (NFT, token, airdrop), not Proof-of-Work mining.

## Goal

Answer with the exact claim mechanics and — wherever possible — a fully solved, verified answer, so the user only has to supply a funded wallet and say go.

## Workflow

1. **Recon the surface.** Read the site's `<title>`/meta/body and its `robots.txt`/`sitemap`. Extract every `href`/`src` and embedded script to find the repo, docs, and contract addresses. The real spec is usually a GitHub README + `docs/` + an `AGENTS.md`, not the marketing page.

2. **Read the authoritative docs, not just the landing copy.** Clone the repo (`git clone --depth 1`) and read `README.md`, `docs/*.md`, `AGENTS.md` (if present — it is written FOR an agent and spells out the exact solve/claim steps), the package manifest, and any `miner`/`scripts`/`cli` entry point. The repo almost always ships a working claim tool; do not reimplement its steps yourself.

3. **Read live chain state — never trust a stale "how many left" number.** Use a provider read (ethers `JsonRpcProvider` is cleaner than raw curl; a batch provider avoids N round-trips). Key facts:
   - block number, `gasPrice` (to state real mint cost, usually fractions of a cent on L2/side chains)
   - `totalMinted`, and the set of already-claimed ids via the `Solved`/`Transfer`/`Minted` event logs (queryFilter over `fromBlock`..`latest`)
   - claimability per token: `ownerOf` reverting (or returning zero address) is the definitive "still claimable" test.
   - **Do not trust a `mintedInBand`/`frontier`/counter alone.** This session: `frontier()` read 7777 (max) while low-numbered angels were still unclaimed — the frontier was not the claimable frontier. Compute the claimable set from events + a genesis/reserved subtraction instead.

4. **Identify the gate type.** Common gates: Vigenère cipher, SHA-256 prefix hunt over a published wordlist, AES-CBC-sealed chained trials, acrostic+hash "construct" puzzles, book ciphers (ottendorf), grid/lattice constraint solving, "relic" = read colors off the token's own SVG art. Each maps to a short program, not a guess.

5. **Solve offline for free.** Solve each trial, chain the results (later trials are usually sealed and unsealed with the previous answer as an AES key), then construct the final answer EXACTLY as the docs specify (separator, casing, normalization, tokenId prefix). Verify against the published/seed hash **before any gas**.

6. **Confirm the hash encoding.** The seed/`answerHash` is ground truth. The on-chain form is usually `keccak256(abi.encode(uint256 tokenId, bytes finalSha256))`, where `finalSha256 = sha256(hex) of "<tokenId>|<answer1>|<answer2>|..."`. Re-derive this against a KNOWN solved single-trial token (e.g. a low angel you can solve trivially) to lock the format before trusting your multi-trial answer.

7. **Gate the actual claim.** Solving/reading is free and autonomous. The mint transaction spends gas and needs a funded wallet, so it requires approval. Ask for one funded throwaway wallet, or offer to create a fresh key and have the user fund it. Creating one locally is a single command: `uv run --quiet --with eth-account python3 -c "from eth_account import Account; a=Account.create(); print(a.address, a.key.hex())"`, then save the key to `~/.hermes/secrets/<name>_key` with `chmod 600` and re-derive the address from the file to prove the backup matches. Never invent an answer to spend gas on — a wrong submission is a wasted txn.

## Voucher-signed mints (server-issued)

Not all gates are puzzles. Many live "catch-to-mint" NFT games make the client speak a WebSocket protocol and mint via a server-signed voucher: the server sends `{contract, chainId, voucher:{to,tokenId,nonce,deadline}, sig, price}` and the wallet broadcasts a plain payable `mint(v, sig)` transaction. No offline solving — the work is reimplementing the WS client headlessly (see the `browser-game-automation` skill, `references/spawnhood-ws-mint.md` for a full worked example). Rules: verify `voucher.to` equals the broadcasting wallet, take `price` from the voucher/on-chain (`currentPrice()`, `tierPrice(i)`) never the UI, broadcast with `{value: price}`, and send the server a `mint_onchain`-style confirmation after the tx mines.

### Free / paid / capacity-gated mint interaction (RH Chain, worked: PayDirt Miners)

Not every gate is a puzzle or voucher. Some "free mint" games on Robinhood Chain expose a plain payable `rush(uint256 amount)`/mint fn — mintPrice reads 0 (free, gas only), yet a `rush(n)` can still **revert by design** when the collection is capacity-gated and full. Diagnose BEFORE broadcasting:

- **Always derive the 4-byte selector, never guess.** Wrong selector = `execution reverted` with empty `0x` data on eth_call, which fools you into thinking the mint is closed/paused. `from eth_utils import keccak,to_hex; to_hex(keccak(text='rush(uint256)'))[:10]` → `0x560e3e3f`. I guessed `b0059384` for `rush(uint256)`, got a false revert on the FIRST live txn, and only caught it by recomputing selectors. Also verify the event/getter selectors the same way — a wrong `rushOpen()`/`pendingMintCount()` selector also "reverts" and lies about state.
- **Capacity-gated Rush queue.** Read `totalMinted()`, `pendingMintCount()`, `nextRushRequestId()` and compare against the collection's `assayCapacity` (from the dapp's `deployment.json`). When `minted + pending == capacity`, the contract's own status is "fully committed" and every `rush()` reverts on purpose. This is not an error to retry — the sale is genuinely over.
- **`mintPrice() · qty` is the `value`, even when 0.** For a free mint this is 0 wei, but read `mintPrice()` anyway rather than assuming.
- **Gas price must clear the block base fee.** `eth_gasPrice` can return a value BELOW the latest block's `baseFeePerGas`, and `eth_sendRawTransaction` then rejects with `-32000: max fee per gas less than block base fee`. Fetch `eth_getBlockByNumber("latest", false)["baseFeePerGas"]` and set `gasPrice ≈ base × 1.3`. This bit me twice in one session.
- **Check `tokensOfOwner(addr)` (selector `0x8462151c`) before committing** — the wallet may already own tokens (here: 28/10 cap), which independently blocks further minting.

Worked end-to-end example (PayDirt Miners free mint on RH Chain, correct-selector probe → capacity-gate diagnosis → clean abort): see `references/robinhood-chain-mint-diag.md`.

### Shared free-drip mints (FABLINGS-style, RH Chain)

Some "free mint" contracts expose NO queue at all — they run ONE global shared line that opens periodically (FABLINGS: ~every 10s) and the first tx in the window claims it. Other wallets grab it within milliseconds, so:

- **A slow cron (~30s+) misses almost everything.** Run a fast daemon polling ~1.3s that simulate-tests then broadcasts the instant the sim is clean (worked numbers + script: `references/fablings-free-drip-mint.md`).
- **Simulate-then-broadcast wins some, loses most.** Observed ~5 wins / ~25 broadcasts (≈20%) against live bots. Every lost race mines as a **revert** — receipt status `0x0`, `logs: []`, ~28.8k gas ≈ $0.001 at 0.02 gwei. Budget **2–3× the theoretical mint gas** for race losses: a $0.10 budget funded only 5/10 mints. A wallet can run dry mid-batch; top up and resume rather than assuming the mint broke.
- **A mined tx is NOT a minted NFT.** Revert txs mine normally with status 0x0. Always re-read `freeMinted(wallet)`/`balanceOf(wallet)` (via `tokenOfOwnerByIndex` enumeration) after each broadcast before counting progress. Never trust the daemon's own "BROADCAST:" line alone.
- **Per-wallet cap exists** (FABLINGS: 10/wallet via `freeMinted(address)`). When the sim reverts with a cap-style error (`0x53353903` here) the wallet is done — use a fresh wallet, don't retry.
- **Sweeping minted tokens** to a collector wallet: enumerate `tokenOfOwnerByIndex` then `transferFrom` each; every transfer is also a gas tx (~$0.008 at 0.02 gwei), so include sweep gas in the budget.

## Pitfalls

- **A "construct" puzzle with a stated hash prefix can have MANY valid phrases.** Brute-forcing a 7-7-7-7 acrostic wordlist phrase against a 6-hex-digit prefix yielded 9 matches; only ONE passed the full seeded final-answer hash. Always run every prefix-matching candidate through the full final-answer hash; do not stop at the first prefix hit.
- **Vigenère keys are best recovered by known-plaintext on repeated ciphertext words.** Find a 3-letter ciphertext word that repeats (e.g. `tdc` → `and`, `dgu` → `one`), derive key letters from position mod keylen, and verify the whole plaintext reads as coherent English. A "perfect-looking" decryption can still be the wrong key if the final hash doesn't match — trust the hash.
- **Spaces/normalization are byte-exact.** Answers are compared byte-for-byte; trailing spaces, capitalization, smart quotes, NFC vs NFD all break the hash.
- **`fromBlock`/`toBlock` on event queries.** Use the deploy block from the repo's `deploy.json`/README to avoid missing early events or rate-limiting a full-chain scan.
- **Event TOPICS are 32-byte full hashes; function SELECTORS are 4-byte (first 8 hex chars).** Never feed a truncated hash into an `eth_getLogs` topic filter. A helper written as `keccak(s)[:8]` is correct for eth_call selectors but produces a 4-byte `0xddf252ad` for `Transfer(address,address,uint256)` — `eth_getLogs` then fails with `-32602: invalid argument 0: hex has invalid length 4 ... expected 32 for topic` and (worse) some RH-rpc variants return an empty `result: []` instead of an error, so a full-history scan silently reports **zero** transfers even though the wallet demonstrably holds tokens. Use `keccak(s)` (full 64 hex chars) for topics; keep `[:8]` only for call data selectors. If a `Transfer`-scan returns 0 but receipts show `0xddf252ad…` logs, suspect this before anything else.
- **A quiet way to trap on this:** `eth_getTransactionReceipt` on a known mint reveals the real topic (`0xddf252ad1be2c89b…`) — compare your filter against it to confirm length/case before trusting a scan result.
- **Raw curl JSON-RPC can 403** (bot-blocked) where a provider client with a normal UA succeeds; prefer ethers over hand-rolled curl for anything beyond a single `eth_blockNumber`/`eth_gasPrice` probe.
- **RH chain RPC rejects legacy ETH transfers at gas=21000** with "intrinsic gas too low" — the official RPC (`rpc.mainnet.chain.robinhood.com`) wants a higher floor for plain value transfers. Use gas=60000+. (Two failed sends before the bump; contract calls with 300k gas are unaffected.)

Worked end-to-end example (puzzle mint on Robinhood Chain, Vigenère + construct trials, solved offline): see `references/inference-angels-recipe.md`.

## Raffle refunds and allocation claims

A frontend saying “did not enter” is not authoritative. First verify the original receipt, sender, value, entry events, and live `entriesOf(sender)`-style getter. Then query the allocation endpoint for that exact sender, verify its Merkle proof against the live root, and simulate the exact claim. A zero-NFT allocation can still contain a full refund. Use one bounded approval for the zero-value claim transaction, then require receipt status 1, claimed/refunded getter confirmation, NFT count, wallet balance delta, and exact gas accounting.

Worked refund-only claim workflow: `references/refund-allocation-claims.md`.

## Verification

- [ ] Claimable set derived from events + genesis subtraction, not a counter.
- [ ] Original entry/deposit receipt and exact sender checked before accepting frontend eligibility text.
- [ ] Allocation/refund proof independently matches the live on-chain root.
- [ ] Exact claim passes `eth_call` and `eth_estimateGas` immediately before signing.
- [ ] Final answer construction matches the docs byte-for-byte.
- [ ] Final hash verified against the seeded/on-chain hash on a known-good single-trial token AND the target token.
- [ ] Real mint/claim cost stated (gasPrice × estimated gas), not "free".
- [ ] Claim transaction (spends gas) is gated on a funded wallet + approval.
- [ ] Success is verified from receipt status, contract claimed state, and balance/token delta—not a broadcast hash.
