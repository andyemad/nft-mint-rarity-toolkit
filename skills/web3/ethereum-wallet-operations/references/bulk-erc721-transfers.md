# Bulk ERC-721 transfers

Verified read/preflight workflow on Robinhood Chain, 2026-08-30. Use this for any request to move many NFTs from a locally controlled EVM wallet.

## Safety and approval boundary

1. Treat the transfer as irreversible external action. Perform read-only discovery and simulation first.
2. Before approval, present one exact slate: source, recipient, chain ID, contract, deterministic token-ID list, count, maximum aggregate gas/native spend, and irreversibility.
3. Do not sign or broadcast before approval. After approval, consume it once, then execute exactly the listed transfers under the stated cap.
4. After broadcast, verify every receipt and read `ownerOf(tokenId)` for every token. Also verify source/recipient `balanceOf` deltas before reporting success.

## Collection and wallet discovery

- Derive the source address locally from the configured key with `Account.from_key(...)`; print only the address, never the key.
- When given an OpenSea collection URL, the server-rendered HTML may contain collection records with `chain.identifier`, `contractAddress`, `standard`, and slug even when higher-level web extraction is unavailable. Parse the record tied to the requested slug/name rather than accepting an arbitrary address found in the page.
- Confirm on-chain `name()`, `symbol()`, source `balanceOf`, recipient `balanceOf`, and chain ID.
- Check `eth_getCode(recipient, latest)`. `0x` means EOA; non-empty code means a contract and warrants extra receiver-risk review. Preserve the recipient address exactly as provided, then checksum it for local encoding.

## Recovering token IDs when ERC721Enumerable is absent

`balanceOf` can prove count while `tokenOfOwnerByIndex` reverts. Recover IDs from logs instead:

1. Compute `Transfer(address,address,uint256)` topic and ensure the JSON-RPC topic has a literal `0x` prefix. In current Web3.py, `Web3.keccak(...).hex()` may omit it; an unprefixed topic produces `invalid argument 0: hex string without 0x prefix`.
2. Left-pad the owner address to a 32-byte indexed topic.
3. Scan contract `Transfer` logs in provider-safe chunks (1,000 blocks is conservative), filtering `topic2 = owner` for inbound transfers.
4. Work backward from latest when acquisition was recent. Deduplicate candidate token IDs and call `ownerOf` on each.
5. Stop only when the number of candidates currently owned equals live `balanceOf(owner)`. This equality is the completeness check; incoming-log count alone is not enough because tokens may have left later.
6. If acquisition history is old, use a capable indexer/archive source or scan both inbound and outbound logs from deployment. Do not silently return a partial list.

For Robinhood Chain, probe the official RPC first. For bulk reads, `https://rpc-proxy.opensea.io/robinhood` was a working fallback when the official endpoint rate-limited. Re-probe endpoints each session rather than treating availability as permanent.

## Deterministic selection and preflight

- If the user specifies token IDs, preserve them exactly.
- If they specify only a quantity and no rarity/selection rule, use a deterministic rule such as the lowest currently owned token IDs, and disclose the exact list in the approval slate.
- For every selected ID, re-check `ownerOf(id) == source` and simulate `safeTransferFrom(source, recipient, id)` using `eth_estimateGas` from the source address.
- Require all simulations to pass. One failure blocks the whole batch until understood.
- Estimate a hard aggregate maximum: sum per-token gas estimates with a safety margin (for example 20%) and multiply by a bounded gas price (for example 1.5x the live quote). Ensure wallet native balance covers the cap.

## Broadcast discipline

- ERC-721 normally requires one transaction per token unless the specific collection exposes a verified batch-transfer method. Never assume one exists and never route assets through an unverified helper contract merely to reduce transaction count.
- Build the exact approved token list, assign sequential nonces from a freshly read pending nonce, and enforce per-transaction gas limits plus the approved aggregate fee ceiling.
- Broadcast sequentially or in a small controlled window. Record token ID, nonce, tx hash, and receipt status so interruption can resume without duplicating transfers.
- If any receipt fails, stop launching new transactions, reconcile confirmed ownership, and return to the user with the exact partial state.

## Concurrent nonce recovery and idempotent resume

Bot wallets may have other daemons broadcasting at the same time. A `nonce too low` response is not proof that the intended transfer failed: the RPC may have accepted and mined the signed transaction before returning the error, or another process may have consumed that nonce.

- Before every send, read the pending nonce again rather than relying on a nonce captured at batch start.
- On `nonce too low`, wait briefly and read `ownerOf(tokenId)` before retrying. If the recipient already owns it, do not resend.
- Recover the transaction by querying the exact `Transfer` log with contract + source topic + recipient topic + token-ID topic, then read its transaction and receipt to reconstruct hash, nonce, gas, and fee.
- If ownership did not change, fetch the new pending nonce and retry the same token with bounded attempts.
- Persist a manifest after every broadcast and receipt. Resume by reconciling on-chain ownership first; treat already-confirmed IDs as complete.
- Enforce the approval ceiling cumulatively: prior confirmed fees plus the worst-case gas cap for all remaining transfers must stay under the original maximum.

This recovery pattern was verified during a 40-token Robinhood Chain transfer: the 16th send returned `nonce too low`, but `ownerOf` and the exact Transfer log proved it had confirmed. The remaining 24 transfers then resumed idempotently and all 40 verified at the recipient.

## ERC721-C / transfer-security-registry collections break operator batch routes

Verified 2026-09-09 on HoodPepes (RH 4663): some collections are ERC721-C and deploy a
**transfer security registry** that rejects ANY transfer where the immediate caller is not the
owner. This silently kills every operator/helper/conduit batch route — including the
documented OpenSea TransferHelper + conduit path — with `StrictAuthorizedTransferSecurityRegistry__UnauthorizedTransfer()`
(inner selector `0x1de5204e`) EVEN when the operator approval is successfully simulated.

Detect before choosing a route:
- Call `getTransferValidator()` on the collection. If it returns
  `0xA000027A9B2802E1ddf7000061001e5c005A0000` (StrictAuthorizedTransferSecurityRegistry)
  or similar, the owner-direct restriction applies.
- Decode the revert selector with `firecrawl` / OpenChain signature lookup
  (`https://api.openchain.xyz/signature-database/v1/lookup?function=0x1de5204e&filter=true`).
  `CreatorTokenTransferValidator` errors and `1de5204e` are the tell.

Working fallback:
- The OWNER wallet calling `transferFrom(source, recipient, id)` directly PASSES the registry
  (caller == from bypasses it). Simulate each with `eth_call` from the source address — all
  must return `0x`. No approval step is needed (owner needs no operator grant) and nothing to
  revoke afterwards, so the cost is genuinely just the transfer gas.
- There is NO batch on such collections when they also lack `multicall`/`batchTransferFrom`
  selectors — the hard floor is one transfer per token (one Rabby confirmation each). This is
  a registry constraint, not a signer limitation; do not lose time re-proving it. If the owner
  wants fewer confirmations, the only alternative is selling via OpenSea (SignedZone Seaport
  order), which carries listing fees — it is not a free batch-gift path.
- Size the real cost honestly: `perTxGas * count * boundedGasPrice`. For HoodPepes that was
  ~53.5k gas/tx, ~0.0005 ETH for 50 total.

## Pitfall: hex-encode token IDs when building calldata by hand

When constructing `transferFrom`/`safeTransferFrom` calldata manually (not via a library),
encode the decimal token ID as its HEX value padded to 32 bytes. Right-padding the literal
decimal string (e.g. `str(id).rjust(64,'0')` for id 625) produces `0x...0625` which decodes
as token 1573 (0x625), NOT 625 (0x271) — silently transferring the wrong token. Always build
calldata with a decode-verify step: re-decode `transferFrom(source, recipient, id)` and assert
the decoded id equals the intended string. Same trap applies to `eth_call` ownerOf probes.

## Final verification

A successful RPC submission is not completion. For every approved token:

- receipt exists and `status == 1`;
- `ownerOf(tokenId)` equals the exact recipient;
- source and recipient balances changed by the number of confirmed transfers;
- total fees did not exceed the approved cap.

Report the confirmed count and transaction hashes (or a saved manifest path for large batches), plus any failures or tokens not moved.