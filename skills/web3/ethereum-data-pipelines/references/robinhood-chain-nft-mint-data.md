# Robinhood Chain NFT/mint data sources

Validated 2026-08-13 while researching independent MintGo-equivalent coverage. Re-probe live values before relying on them operationally.

## Network and public infrastructure

Mainnet:

- Chain ID: `4663` (`0x1237`).
- Native currency: ETH, 18 decimals.
- Official HTTP RPC: `https://rpc.mainnet.chain.robinhood.com`.
- Additional HTTP RPCs directly verified with `eth_chainId`: `https://rpc.arrowrpc.com`, `https://robinhood-rpc.publicnode.com`, `https://robinhood.api.pocket.network`.
- Standard JSON-RPC WSS directly verified: `wss://robinhood-rpc.publicnode.com`, `wss://robinhood.rpc.blxrbdn.com`.
- Explorer: `https://robinhoodchain.blockscout.com`.

Testnet:

- Chain ID: `46630` (`0xb626`).
- Native currency: Sepolia ETH, 18 decimals.
- HTTP RPCs directly verified: `https://rpc.testnet.chain.robinhood.com` and the `/rpc` variant.
- Explorer: `https://explorer.testnet.chain.robinhood.com`.

Official docs: `https://docs.robinhood.com/chain/connecting/`. Robinhood Chain is an EVM-compatible Arbitrum L2. The docs recommend a provider archive endpoint for historical reads/indexing; do not assume the free official RPC offers unlimited archive history.

Official `wss://feed.mainnet.chain.robinhood.com` and testnet equivalent are Arbitrum sequencer feeds, not ordinary Ethereum JSON-RPC sockets: a probe yielded versioned sequencer envelopes with encoded L2 messages. Use a dedicated Arbitrum feed decoder rather than sending `eth_subscribe` as though these were normal RPC WSS endpoints.

## Blockscout API

Keyless v2 routes worked:

- `/api/v2/stats`
- `/api/v2/blocks?type=block`
- `/api/v2/addresses/{address}`
- `/api/v2/smart-contracts/{address}`
- `/api/v2/transactions/{hash}`

Base URL: `https://robinhoodchain.blockscout.com`. The legacy Etherscan proxy call `?module=proxy&action=eth_blockNumber` returned `Unknown module`; do not assume complete Etherscan compatibility.

**Cloudflare-Worker caveat (verified 2026-08-14):** every v2 route listed above
returns **429 from Cloudflare Worker egress** (datacenter-IP WAF/rate block; browser
UA + Referer do not help), while the same calls return 200 from a home IP/node. Use
Blockscout freely from your machine/scripts, but never from a CF Worker — fall back
to RPC `eth_call totalSupply()` + your own aggregate minters data (see
`opensea-v2-keyless-enrichment.md` for the full fallback stack).

## Canonical SeaDrop coverage

Verified active deployment:

`0x00005ea00ac477b1030ce78506496e8c2de24bf5`

Evidence: non-empty runtime bytecode, verified Blockscout source/ABI labeled SeaDrop, active configuration logs, and successful mint receipts containing `SeaDropMint`.

Public schedule event:

- Signature: `PublicDropUpdated(address,(uint80,uint48,uint48,uint16,uint16,bool))`
- Topic: `0x3e30d8e1f739ea4795c481b21c23f905e938b80339305f3508e43c558e5dead3`
- NFT contract: last 20 bytes of `topics[1]`.
- Six ABI words: `mintPrice`, `startTime`, `endTime`, `maxTotalMintableByWallet`, `feeBps`, `restrictFeeRecipients`.

A live 5,000-block mainnet query returned 23 `PublicDropUpdated` logs. Representative successful configuration transaction:

- Tx: `0x4a29d4f120507dd576ed721b221a076a994a871e9d9ed66b6bb108d2e0cf01b3`
- NFT: `0x06963c8acd0d3086f8a611edc99fb3fcc94afa75`
- Decoded values: `0.01 ETH`, start `1786641631`, end `1786728031`, max/wallet `20`, fee `1000 bps`, restricted recipients `true`.
- Explorer: `https://robinhoodchain.blockscout.com/tx/0x4a29d4f120507dd576ed721b221a076a994a871e9d9ed66b6bb108d2e0cf01b3`.

Also index SeaDrop ABI events `SeaDropMint`, `SignedMintValidationParamsUpdated`, `TokenGatedDropStageUpdated`, `AllowListUpdated`, `AllowedFeeRecipientUpdated`, `CreatorPayoutAddressUpdated`, `PayerUpdated`, and `DropURIUpdated`. PublicDrop alone cannot reconstruct every signed-presale detail.

## Live mint detection and validation

Filter standard `Transfer` logs with:

- `topic[0] = 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`
- `topic[1] = 0x` + 64 zeroes (`from == address(0)`).

Require exactly four topics for ERC-721. In a live 20-block sample, the broad filter returned 30 logs: 24 four-topic ERC-721 mints and 6 three-topic ERC-20 issuances. Add separate ERC-1155 `TransferSingle`/`TransferBatch` handling if parity requires it.

Representative validated mint:

- Tx: `0x4e90fa304d950e9944ffe93405497ba16bccd4afb826503429b3c841c95fc447`
- NFT: `0x4ec2e266cc4c349adff0ec923d8e44a9b2c08e34`
- Recipient: `0x9aafaaa231f66c8fed09af5124c8c211daefbf20`
- Token IDs: 706 and 707.
- Receipt status: `0x1`.
- Receipt included both zero-address ERC-721 Transfers and a `SeaDropMint` emitted by canonical SeaDrop.
- Explorer: `https://robinhoodchain.blockscout.com/tx/0x4e90fa304d950e9944ffe93405497ba16bccd4afb826503429b3c841c95fc447`.

Validation sequence: confirm receipt success; correlate Transfer and factory events in the same receipt; compute payment from transaction value plus native/ERC-20 receipt flows; persist `(blockHash, transactionHash, logIndex)`; and handle removed/reorged logs. Backfill finalized ranges over HTTP even when WSS is connected.

## Marketplace and enrichment

OpenSea supports chain slug `robinhood`:

`https://opensea.io/contract/robinhood/{contract}`

The contract route redirects to a collection page. Public page hydration can expose name, slug, image, project/social URLs, supply, floor/statistics, and SeaDrop stages. OpenSea REST v2 is keyless **for the robinhood chain** (`/api/v2/chain/robinhood/contract/{addr}` + `/api/v2/collections/{slug}` return name/image/slug with no key); only the ETH contract endpoint is key-gated, and v1 is permanently removed (410). OpenSea has NO stats/events coverage for RH (404) — market volume/sales for RH must be derived on-chain from marketplace events. See `references/opensea-v2-keyless-enrichment.md` for the verified endpoint matrix, the instant agent-key flow, and the cache-first enrichment pipeline. Public-page GraphQL hydration remains a best-effort fallback only for Ethereum identity.

MintGo's live Robinhood status reported OpenSea market data, standard HTTP/WSS failover, and a relayed OpenSea stream. Treat MintGo endpoints as private audit evidence, not a supported dependency. During the same probe, its SeaDrop radar showed on-chain configurations enriched with OpenSea signed/public stages, while market/trending snapshots carried OpenSea identities, images, floors, and sales/volume fields.

No Robinhood coverage was independently established for Magic Eden, Reservoir, Rarible, or other marketplaces in this pass. Keep them labeled unverified until directly probed.

## Production source hierarchy

1. HTTP/WSS RPC for canonical blocks, receipts, logs, calls, and balances.
2. Canonical SeaDrop events for public configuration and verified route attribution.
3. Blockscout for ABI/source, deployment provenance, labels, and decoded transaction fallback.
4. OpenSea public pages or keyed API for market identity and signed-stage enrichment.
5. Heuristics only for descriptive scoring; never promote inferred payment, factory identity, or marketplace state to on-chain fact.
