# Contract-stack discovery: find every contract behind an NFT project

Verified end-to-end 2026-08-25 on CacheFlow (Robinhood chain). Use when given
only an OpenSea collection URL (or slug) — or an X post from the project — and
asked to find "the contracts".

## Recipe

1. **Keyless collection metadata**:
   `curl -s https://api.opensea.io/api/v2/collections/<slug>` → gives
   `contracts[]` (address + chain), `owner` (project EOA), `editors`,
   `required_zone`, royalty recipients/fees, `total_supply`,
   `created_date`, `pricing_currencies`. NOTE: other v2 endpoints (`/nfts`,
   `/stats`) DO require an API key — only `/collections/<slug>` is keyless
   (re-verified 8/25; don't waste calls rediscovering this).

2. **Verify deployment + read ownership on-chain**:
   - `eth_getCode` — deployed if length > 2.
   - `eth_call` selector `0x8da5cb5b` (`owner()`) — most ownable NFT
     contracts answer it. CacheFlow's returned the project EOA directly,
     matching OpenSea's `owner` field (two independent confirmations).

3. **Walk the owner EOA's history on Blockscout**
   (`https://robinhoodchain.blockscout.com/api/v2`; needs a browser
   User-Agent or it returns an EMPTY body with HTTP 200 — check bytes):
   - `/addresses/<EOA>/transactions` — shows `created_contract` hashes (the
     deployer's OTHER contracts) plus setup methods. `multiConfigure`,
     `setTransferValidator`, `setBaseURI`, `setMaxSupply` = SeaDrop-style
     stack; `mintSigned` to a separate minter address identifies the mint
     contract.
   - `/addresses/<EOA>/internal-transactions` — royalty/payout flow (from
     zero address = WETH unwraps/sale proceeds).
   - `/addresses/<EOA>/token-transfers` — which ERC20 sales settle in.
     CacheFlow settles in **WETH**, not native ETH.

4. **Classify each found contract**: `eth_getCode` size + probe common
   selectors — `0x06fdde03` name(), `0x95d89b41` symbol(), `0x18160ddd`
   totalSupply(). A ~21KB contract receiving `mintSigned` = minter; a small
   non-standard contract deployed in the SAME SECOND as the NFT = custom
   project logic (CacheFlow: its mining contract, 5KB, no standard interface).
   Contracts in OpenSea metadata that show 0 code on this chain (e.g. the
   OpenSea fee recipient `0x0000a26b…a719`) are just not deployed per-chain —
   don't treat as an error.

## Reading X posts about a project (no-auth)

`https://api.fxtwitter.com/<handle>/status/<ID>` → `.tweet.text`. Worked for
CacheFlow's roadmap tweet ("testing on testnet… now checking all smart
contracts live on mainnet") — which told us the live mainnet deployment IS
the final stack; nothing remained on testnet to find. When the user asks to
"find these contracts on testnet", read the post first: it may say they've
already moved to mainnet.

## State checks (reveal tracking)

- Pre-reveal detection: `eth_call` `tokenURI(1)` =
  `0xc87b56dd0000000000000000000000000000000000000000000000000000000000000001`.
  The returned string decodes UTF-8 with a stray leading pad byte
  ("Bipfs://…" — B is offset padding); strip to the real `ipfs://`.
- Fetch metadata JSON via `https://ipfs.io/ipfs/<cid>`. The pinata gateway
  served an HTML page for this CID while ipfs.io returned clean JSON —
  gateway reliability is per-CID, try more than one.
- `"Prereveal <name>"` metadata title = still unrevealed.

## Robinhood RPC notes (current)

- `https://rpc.arrowrpc.com` now returns Cloudflare `error code: 1033` from
  curl (it worked before); `https://rpc.mainnet.chain.robinhood.com` answers
  fine. Probe both at session start; prefer whichever answers NOW. Don't
  hardcode either.
