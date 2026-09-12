# ClawCrabs (Robinhood chain) burn-to-mint recon — 2026-08-25

Session-specific detail for the Pons V2 "burn token to mint" pattern. The
direct-contract detector in Mint Room (`direct-detect.ts`) does NOT fit this
class: it looks for a plain `mint()` on the collection contract and fails when
minting is a multi-step flow through a separate claim/curve contract.

## Collection facts

- Tweet CA 0x80c8571aaa74e5a940492e81e941bf6667b4ecd8 = the $CLAW ERC-20
  (Pons V2 launch token), NOT the NFT. Site clawcrabs.xyz lists all four
  addresses in its bundle (`CLAIM_ADDRESS`, `CLAW_ADDRESS`, `NFT_ADDRESS`,
  `USDG` constants).
- NFT: 0xB60d6089C3601ea13B4E8E9B20922FAce5Eb5997 (ERC-721, 1,111 supply).
- Claim: 0x61A502D2138F6e073a22EA445E0393170fc83659 — verified source
  `src/ClawcrabsClaim.sol` on Robinhood Blockscout.
- Curve: 0xbd3154d00ca64b01952091210dbdd23cca54bd13 — UNVERIFIED bytecode;
  identified by selector dump + openchain.xyz signature lookup.
- Factory: 0x7eD598BcEf8bd9Edd8C97A195C6d13f40801EC7e = `PonsV2LaunchFactory`
  (verified). `getLaunchedToken(token)` returns a struct whose word 1 is the
  curve address — this is how to find the curve for any Pons launch.

## Burn-to-mint flow (two transactions, by design)

1. Buy quote-token amount from the bonding curve:
   `buy(uint256 amountIn, uint256 minOut, address recipient)` — NATIVE-quote
   curve (`isNativeQuote()==true`, pairToken=0), so send `msg.value ==
   amountIn`. A reverted eth_call returns custom error
   `NativeValueMismatch(uint256 sent, uint256 required)` — useful as a free
   price probe: revert data echoes the exact required native value.
   Cost observed: 0.001 RH ETH bought ~311k CLAW (300k needed per claim).
2. `approve(CLAIM, amount)` on the ERC-20.
3. `claim()` on the claim contract — burns the tokens, writes a Commit
   anchored to current block. Custom errors: NotWiredAsMinter,
   CommitPending, SoldOut, PriceNotSet, TransferShortfall.
4. Wait REVEAL_DELAY_BLOCKS=1 (~11.5s/block measured; site says ~23s wait),
   then call `reveal()` within MAX_REVEAL_BLOCKS=240 or `recommit()` (free,
   permissionless; revealFor/recommitFor also permissionless).

Useful views on claim: `claimPrice()`, `claimOpen()`, `claimed()`,
`openCommits()`, `claimState(address)`, `supplyState()`.
Anti-snipe: `_pinnedSeed` precomputes the Fisher-Yates seed so reveal timing/
contract cannot reroll rarity — do not try to snipe rare mints via reveal
timing; it is pinned at commit time.

## Recon workflow that worked (generalize to any new RH-chain drop)

1. Extract tweet text via fxtwitter/vxtwitter mirrors → get CA + chain.
2. Inspect the CA with Mint Room `/api/direct-mint?inspect=1&contract=…`
   (GET, loopback only). If it returns an ERC-20 totalSupply (~1e26 range),
   it's the fungible token, not the NFT.
3. Scrape the project site HTML for `0x[a-fA-F0-9]{40}` addresses; map roles
   via blockscout `/api/v2/tokens/{addr}` (type ERC-20 vs ERC-721) and
   `/api/v2/smart-contracts/{addr}` for verified sources.
4. For unverified contracts: pull `eth_getCode`, regex selectors
   `63([0-9a-f]{8})1461`, resolve names via
   `api.openchain.xyz/signature-database/v1/lookup?function=0x<sel>`.
5. Read state with eth_call against `https://rpc.mainnet.chain.robinhood.com`
   using keccak selectors from `eth_utils` (bunker-snipe venv has eth-utils).
   Plain urllib gets 403 unless a browser User-Agent header is set.
   `rpc.robinhoodchain.com` fails TLS SNI — use the mainnet.chain.robinhood.com host.

## Gotchas

- Blockscout smart-contract API intermittently returns plain
  `"Internal server error"` / empty JSON — retry; second fetch often works.
- The claim `_burn` tries `burn(uint256)` on the token first, falls back to
  transfer-to-DEAD; either way tokens are destroyed, not collected.
- Direct-mint inspect times out slowly (>60s) on contracts without standard
  ABI — use short curl timeouts and don't block the session on it.
