---
name: seadrop-rapid-mint
description: Fire SeaDrop public mints fast with a fresh funded wallet.
---

# SeaDrop Rapid Mint (Dunlap config)

Fire OpenSea **ERC721SeaDrop** public mints on Robinhood Chain (4663) within seconds of a stage opening, using one **fresh wallet per mint event**. Built from the Dunlap postmortem (`~/Projects/dunlaps-mint-report/data.json`) — that report's numbers are the ground truth for what works.

## Tooling
- Script: `scripts/seadrop_fire.py` (this skill's dir). Run with the bunker-snipe venv: `~/Projects/bunker-snipe/.venv/bin/python scripts/seadrop_fire.py ...` (has eth_account). No web3 needed.
- Key files: raw-hex private keys in `~/.hermes/secrets/` chmod 600 (ethereum-wallet-operations convention).
- RPC `https://rpc.mainnet.chain.robinhood.com` rate-limits: script retries w/ backoff; if still 429, wait ~20s and retry. Blockscout v2 API (`https://robinhoodchain.blockscout.com/api/v2/...`) is Cloudflare-walled to raw curl — route through firecrawl or use the RPC eth_call instead.

## Ground truth (Dunlap / RH SeaDrop)
- SeaDrop singleton: `0x00005ea00ac477b1030ce78506496e8c2de24bf5` (same for Dunlap 0xe801b3... and Wasteland/WLAND 0xeb5cbe... — if a drop fails against it, pass the per-collection SeaDrop explicitly as last arg).
- Mint fn: `mintPublic(address nftContract, address feeRecipient, address minterIfNotPayer, uint256 quantity)` — selector `0x161ac21f`.
- feeRecipient MUST be an address from `getAllowedFeeRecipients(nftContract)` when `restrictFeeRecipients` is true (WLAND was restricted). Script picks the first allowed automatically.
- Gas: limit **180000**, maxFeePerGas **0.5 gwei**, maxPriorityFee **0**. Base fee on RH is ~0.07 gwei; 120k gas is enough for qty 2, 180k is the safe number.
- One prepared tx per wallet, sent in parallel at stage start.

## Workflow
1. **Recon first, always.** `... seadrop_fire.py recon <collectionCA> [seadropCA]` prints totalSupply/maxSupply, mint price, cap/wallet, window, feeBps, allowed fee recipients, and `open: true/false`. **Never fire blind** — value+gas on a closed/sold-out drop just reverts. If `soldOut` or outside window, say so and stop.
2. **Fresh wallet + fund ask.** `... seadrop_fire.py wallet <collectionCA> [N]` — generates N new wallets, prints each **address + exact fund amount** (price*qty + gas buffer + margin), saves keys chmod 600 + `~/.hermes/secrets/seadrop_last.json`. **Stop and hand the address(es) + fund amount to Emad.** Do not proceed until he confirms funding.
3. **Confirm funding.** `... seadrop_fire.py check-funded <collectionCA> --wallets a,b` polls balances; only proceeds when every wallet has enough.
4. **Fire.** `... seadrop_fire.py fire <collectionCA> <keyfile> [qty] [seadropCA]` — eth_call dry-run first (refuses if it would revert), then broadcasts. Qty defaults to cap; never exceed cap/wallet (use more wallets instead).
5. **Verify.** Script prints receipt status + `balanceOf`; also spot-check `0x161ac21f` txs from the wallet on the explorer.

## Rules / pitfalls
- **Recon before broadcast is mandatory** — WLAND (0xeb5cbe68a0fb8a0fb3660f152e98329a5b465c9d) was sold out (totalSupply==maxSupply==3333) and bots were still firing into the closed stage, burning gas on reverts.
- Fresh wallet each time = cap-per-wallet headroom + clean provenance. Emad funds it; we never reuse his main wallets for mints unless he says so.
- Quantity per wallet is capped by the drop (`capPerWallet`); for larger goals spawn more wallets and fund each.
- The drop window comes from `getPublicDrop` (startTime/endTime are unix). Mint attempts outside the window revert.
- If the sale hasn't started yet and timing is tight, prep the calldata + signed tx per wallet BEFORE the window opens (nonce/gas are safe to set then), then broadcast the moment startTime passes.
- RPC 429 on broadcast: do not double-send. Poll `eth_getTransactionReceipt`; only rebroadcast if no receipt after ~30s AND nonce unchanged.
- Never git-commit/clean these key dirs.

## Verification
A mint is only done when: tx receipt status 0x1 AND `balanceOf(wallet)` increased by qty AND token id(s) show on the explorer/OpenSea. Report tx hash + wallet + count. If receipt is 0x0, pull the revert reason from the tx trace before retrying anything.
