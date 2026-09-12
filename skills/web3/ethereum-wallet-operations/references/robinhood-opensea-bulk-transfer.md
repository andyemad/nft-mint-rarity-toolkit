# Robinhood Chain OpenSea bulk-transfer route

Read-only verified 2026-09-09 on chain 4663 (0x1237). Recheck live before use.

- RPC https://rpc-proxy.opensea.io/robinhood requires User-Agent: Mozilla/5.0 in curl. Same host /ethereum works for reference bytecode. Some other RPCs return 403/1015.
- TransferHelper: 0x0000000000c2d145a2526bd8c716263bfebe1a72. RH runtime 3884 bytes exactly equals Ethereum same-address runtime, verified source https://etherscan.io/address/0x0000000000c2d145a2526bd8c716263bfebe1a72#code.
- RH OpenSea conduit: 0x963f00d3ff000064ffcba824b800c0000000c300. Runtime 3190 bytes exactly equals Ethereum OLD conduit 0x1e0049783f008a0085193e00003d00cd54003c71, verified source https://etherscan.io/address/0x1e0049783f008a0085193e00003d00cd54003c71#code. Old conduit itself is NOT deployed on RH at this check.
- Key: 0x<REDACTED-PRIVATE-KEY>.
- Controller: 0x00000000f9490004c11cef243f5400493c00ad63, runtime 8820 bytes exactly matches Ethereum same address.
- SDK primary provenance https://github.com/ProjectOpenSea/opensea-sdk/blob/main/src/utils/chain.ts getDefaultConduit maps Robinhood to key/address 2; src/constants.ts defines exact values and helper. src/sdk/assets.ts implements bulkTransfer.
- Verify controller getConduit(bytes32) => correct conduit, exists=true; getChannelStatus(address conduit,address helper) => true. Both passed.
- Empty bulkTransfer simulation passed returning 0x32389b71 padded; this DOES NOT prove selected-token execution.
- ABI signature bulkTransfer(((uint8,address,uint256,uint256)[],address,bool)[],bytes32). Use one outer tuple for a common recipient, with items (2, NFT contract, token ID, 1); validateERC721Receiver=true; key above. Value zero. User signs via Rabby ordinary eth_sendTransaction; no wallet_sendCalls or key export needed.
- Approval spender is CONDUIT, NOT helper. Collection setApprovalForAll(conduit,true) may be needed. Review collection-wide authority, simulate actual selected tokens, approve explicitly, execute exact batch, then revoke if desired. 50 per-token approve calls are narrower but lose efficiency.
- Rabby develop source snapshot inspected: no wallet_sendCalls/wallet_getCapabilities implementations found across TS/TSX/JSON, SendNFT/index.tsx sends one safeTransferFrom via eth_sendTransaction. EIP7702 revoke chain support (HOOD present) is NOT evidence of EIP5792 batch send. Installed-version capabilities remain untested.
- nft.multisender.app assets/index-BTu3tEtw.js maps only nine chains, not RH. Its contract 0x63d831f320efe936287672220bd7821252a4cd32 returned no code on RH. ERC20 multisenders advertised for RH are not NFT support evidence.

This is a verified deployed contract route, not verified OpenSea UI control availability or approval to send. No writes/signatures occurred in discovery.
