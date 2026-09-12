# Mint-Site Variants Beyond the Plain Free Mint

Verified 2026-08-18 on two Robinhood-chain mints the user asked about: **PayDirt Miners**
(play.theminers.cash — a 2-step game mint) and **stARThood** (starthood.art/mint — a
ritual + US-person-declaration gated free mint). Use this alongside
`free-mint-site-reverse-engineering.md` when the user shares a mint link that is NOT a
plain SeaDrop/public mint. Not every "free mint" is a one-call `mintFree()`.

## Variant A — Runtime-fetched deployment config + 2-step game mint (PayDirt Miners)
PayDirt Miners (contract `0x5DedE08aB27b56214c9FF0932D907F52A3a97627`, token "MINER49",
chain 4663/Robinhood) does NOT ship its config in `config.js`. It fetches
**`deployment.json` at runtime** from the site root (bundle does `fetch("./deployment.json")`).
Pull it first — it is the single source of truth:
```
chainId 4663  rpcUrl https://rpc.mainnet.chain.robinhood.com
miners 0x5DedE08aB27b56214c9FF0932D907F52A3a97627   (the NFT contract)
payDirt ...   punchClock ...   loans ...   gold/silver/oil ...   treasury ...
rushOpen true   randomMint true   mintPrice 0   mintPriceFrozen true
assayCapacity 4949
```
Mint is **2-step** (a block-delayed random draw, not an immediate token):
1. `rush(uint256 amount)` — payable, `value = mintPrice * amount`. With `mintPrice()==0`
   on-chain (=0), this is **genuinely free, gas only**. `rushOpen` must be true.
2. Then a separate **`finalize`** transaction ("finalizing the oldest Rush draw") —
   a random token per mined count is assigned after a block delay. Don't promise a token
   lands instantly; there is a second confirm step.
Other getters (`totalSupply`, `maxSupply`, `randomMint`, `rushOpen`) REVERTED via
`eth_call` even though the contract clearly works (name/symbol/mintPrice returned fine). A
reverting read getter is NOT proof the contract is broken or the mint is closed — probe a
spread of selectors and trust the ones that return (mintPrice, name, symbol) plus the
shipped deployment.json before concluding anything.

### PITFALL — "0.45 USDG" in the OpenSea title is the FLOOR, not the mint price
The collection page title was "PayDirt Miners 0.45 USDG - Collection | OpenSea". That
number is the current **resale floor** (OpenSea appends it to the title), NOT the mint cost.
Confirmed by `mintPrice()` reading 0 on-chain (free) while `/stats` floor is 0.45 USDG.
When the user reads the mint price off the OpenSea title, verify actual price via the
contract's `mintPrice()`/`publicDrop` — the title floors and mint prices are different
things.

### PITFALL — RH RPC blocks Python urllib even with UA in some toolsets
This session `eth_call` worked via `curl -X POST` with `Origin: https://play.theminers.cash`
+ `Referer` + the modern Chrome UA, while a plain `urllib` POST 403'd. For RH RPC, always
include browser-like `Origin`/`Referer` AND `User-Agent` (the `ethereum-data-pipelines`
pitfall covers the UA; the Origin/Referer matters too — copy them from the mint site you
are probing). Use curl for one-off probes; a Python client must replicate all three headers.

## Variant B — Ritual + US-person-declaration gated mint (stARThood)
stARThood (starthood.art/mint, same Robinhood chain family) is "free" but gated behind a
5-step **ritual**: (1) sign a gasless "passport" message with an explicit **ACCESS
DECLARATION — "I confirm I am not a U.S. Person, I am not accessing from the United
States…"**, (2) math+memory human test, (3) button maze, (4) X-ceremony (follow/like/
repost + reply **tagging two friends** + submit receipt links + X handle), (5) server issues
a 10-minute authorization, then mint (2 per wallet).

### Flag these to the user BEFORE agreeing to mint — three distinct gates
1. **Legal/geoblock.** The passport is a signed declaration that the minter is not a US
   person and not accessing from the US. For an Emad-in-Georgia user that assertion is
   FALSE. Do not script around it or fabricate it — state plainly this is a signed legal
   attestation to bypass a geoblock and let him decide; do not build the bypass.
2. **Social/consent.** The X-ceremony posts to his account and tags two unconsented real
   people. That's an external consequence (public post + tagging others); flag it, don't
   just execute it.
3. **Mechanics.** Needs an EIP-6963 browser wallet (Rabby/MetaMask/Coinbase) to sign +
   mint, plus chain gas. The gasless passport signature "cannot move funds" but the mint
   tx itself pays gas.
Net: a 2048-supply ritual free mint is, realistically, zero hype / not a flip-grade liquid
asset. Read the floor/volume before encouraging a claim.

### stARThood architecture notes (if you ever need the details)
- Site loads `../app.js` (+ `ethers.min.js`); the mint is server-authorized via a signer
  API + "private PHP database" (the "SIGNER API NOT CONFIGURED — preview mode" banner).
- Revert/success flow: commit `rush`, then `finalize` — same 2-step family as PayDirt.

## Diagnostic recap that worked (PayDirt)
OpenSea title "PayDirt Miners 0.45 USDG" → opensea v2 `/collections/{slug}` (+`/stats`)
keyless (chain robinhood, supply 3163, owner `0xfFaC31…`, 1% OpenSea fee) → t.co links in
the X profile resolved to play.theminers.cash → `deployment.json` (chain 4663, miners
addr, mintPrice 0, rushOpen true, randomMint true) → app.bundle.js → `rush` payable +
`finalize` → title "0.45 USDG" is floor not price. Bot wallet bal 0.030 RHC = enough gas
for a free 2-step mint. Verdict: free game-mint, gas-only, not a liquid flip.
