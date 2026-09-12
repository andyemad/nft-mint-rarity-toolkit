# SeaDrop public-mint preflight — "mint these NOW" gate (WLAND worked example 2026-09-04)

Emad's urgent-mint requests ("Mint these on public 0x… in less than 3 minutes using the settings from the dunlap mint") target OpenSea **ERC721SeaDrop** contracts on Robinhood Chain. Public mints run through the SHARED SeaDrop stage singleton, NOT the NFT contract. Before queuing parallel wallet txs from any prior known-good config, run the preflight below — a drop that is sold out or whose stage is closed reverts every attempt and wastes gas.

## WLAND case (what actually happened)
- Request arrived ~17:31 UTC for WLAND / Wasteland (`0xeb5cbe68a0fb8a0fb3660f152e98329a5b465c9d`, ERC721SeaDrop, verified, 3333 supply).
- On-chain truth: `totalSupply() == maxSupply() == 3333` (FULLY MINTED); SeaDrop `getPublicDrop` stage had ended 17:30:00 UTC (window 17:30 → 20:10 UTC). Sold out minutes before the request.
- Explorer recent-tx list showed a swarm of repeated `status: error` txs from one caller (`0xc2a98ce3…`) firing selector `0x0da0ba32` — a selector that matches NO mintPublic/mintSeaDrop variant (computed against the full candidate list). Two tells: (a) failed swarm = closed/misconfigured/sold-out drop; (b) unknown selector = the spammers are burning gas on a phantom function, do not copy them — read the real ABI.
- Outcome: all three of Emad's wallets verified `balanceOf == 0`; nothing broadcast; zero ETH spent. Honest miss beats gas waste.

## Preflight checklist (run in order, then broadcast)
1. **Supply check first** — RPC `eth_call` `totalSupply()` (0x18160ddd) and `maxSupply()` (0xd5abeb01). If equal → sold out, STOP, report, offer floor-watch/secondary instead.
2. **Stage check** — `getPublicDrop(nftContract)` on the SeaDrop singleton decodes as ABI words: word0 = mintPrice (wei, 18dp), word1 = startTime, word2 = endTime, then maxPerWallet / feeBps / restrictFeeRecipients. Confirm `now` is inside [start, end].
3. **Selector check** — the canonical stage call on this chain is `mintPublic(address,address,address,uint256)` = **0x161ac21f** (nftContract, feeRecipient, minterIfPayer, quantity; value = price × qty). Compute keccak of the EXACT function signature from the verified SeaDrop ABI — never copy a selector you saw in the mempool/explorer without matching it to a real ABI entry.
4. **Known-good config reference** — the "Dunlap" settings live at `~/Projects/dunlaps-mint-report/data.json` (public-mint postmortem): SeaDrop singleton `0x00005ea00ac477b1030ce78506496e8c2de24bf5`, method mintPublic 0x161ac21f, walletCap 2, gas limit 180000, maxFeePerGas 0.5 gwei, maxPriorityFee 0, ~0.00414 ETH funding per wallet (2 qty @ 0.002 + buffer), one prepared tx per wallet fired in parallel at stage start. Reuse as the DEFAULT SeaDrop execution config on RH chain, but re-read the live stage every time — the WLAND stage closed at a different price/window than Dunlap's.
5. **Post-attempt verify** — `balanceOf(wallet)` per wallet (0x70a08231 + padded addr); report landed mints by tx, else state plainly nothing minted.

## RH RPC notes that matter here
- `rpc.mainnet.chain.robinhood.com` hard 403/429s bursts: always send `User-Agent: Mozilla/5.0`, retry with sleep backoff (2s+), and expect intermittent single-call success (a `totalSupply` read may land when the previous call 429'd). Space calls ~0.3-1s.
- Blockscout legacy proxy (`?module=proxy&action=eth_call`) returns 400 on RH — do not rely on it; use the RPC directly or the v2 API.
- `getPublicDrop` may come back cleanly even while other calls fail; decode defensively word-by-word.

## General rule
Any "mint NOW, we must hit" request against a SeaDrop public stage: read supply + stage FIRST (seconds, two eth_calls), then blast. If the drop is already sold out, the correct action is to spend nothing and say so — not to fire the queued config and report reverts.
