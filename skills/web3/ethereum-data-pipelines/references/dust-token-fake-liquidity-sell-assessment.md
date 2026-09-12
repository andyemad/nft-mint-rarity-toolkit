# Dust-token "sell this for me" assessment (fake-liquidity bait)

Worked example 2026-08-22: Emad pasted a raw private key asking to sell "~0.03 $SHCAP worth $192" with a dexscreener link claiming "1.88 weth liquidity". On-chain truth: dead Dec-2018 ERC-20 ("AshleighCoin"/SCHAP, supply 7,000), real Uniswap V2 pool created Oct 2023 with ~0.5 SCHAP + 0.1 ETH, **last swap ever Oct 26 2023**, current reserves ~5e-8 SCHAP / ~1.1e-7 WETH. Realizable value $0.00; the $192 and "1.88 weth" were fabricated by a price feed, not on-chain facts.

## Why this class exists

Dust scams airdrop worthless tokens to thousands of wallets, inflate displayed valuations, and bait holders into connecting real wallets to a "sell" site that drains them. Any "can you sell this token?" request must be settled ON-CHAIN before touching anything — the aggregator UI is not evidence.

## Verification recipe (all read-only eth_call/getLogs, minutes)

1. **Derive the address from the pasted key** (`eth_account.Account.from_key`) — the user often pastes the KEY, not the address. Check `balanceOf` and `eth_getBalance` on the DERIVED address, not any address they name.
2. **Token identity**: batch `name()` 0x06fdde03, `symbol()` 0x95d89b41, `decimals()` 0x313ce567, `totalSupply()` 0x18160ddd on the contract. Cross-check age/provenance via Ethplorer freekey (`api.ethplorer.io/getTokenInfo/<addr>?apiKey=freekey` returns creator + creation timestamp).
3. **Treat the dexscreener URL skeptically**: the path address may be the TOKEN CONTRACT, not a pair (this case was). Confirm what it is first — if `getReserves` 0x0902f1ac reverts but `name()` works, it's a token, not a pool.
4. **Dexscreener API nulls = strong red flag**: `/latest/dex/pairs/ethereum/<addr>`, `/tokens/<addr>`, and `/search?q=<addr>` all returning `"pairs":null` means no indexed liquid market exists, whatever the page claims.
5. **Find the REAL pools keylessly**:
   - Uniswap V2: `getPair(token,WETH)` 0xe6a43905 on factory 0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f
   - Sushiswap factory 0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac
   - Uniswap V3 `getPool(token,WETH,fee)` 0x1698ee82 on 0x1F98431c8aD98523631AE4a59f267346ea31F984 for fee tiers 500/3000/10000
   Then read `token0()` 0x0dfe1681 / `token1()` 0xd21220a7 and `getReserves()` 0x0902f1ac.
6. **Quote honestly**: constant-product with 997/1000 fee, or router `getAmountsOut` 0x38ed1739 (reverts here because the bag exceeded total pool reserves ~650,000× — itself the verdict).
7. **Is the pool DEAD?** Scan `Sync` logs (topic 0x1c831912) from pool creation forward in ≤9,990-block windows until several consecutive empty windows; also binary-search `eth_getCode` over blocks to date pool creation. Zero syncs since 2023 = no exit liquidity regardless of quoted "liquidity".

## Free Ethereum RPC reality (Aug 2026)

- **drpc.org worked** as the only fully functional free mainnet RPC of the set tried: llamarpc 521, publicnode silent-empty, ankr auth-required, 1rpc rate-limited, cloudflare-eth internal error. Free plan caps `eth_getLogs` ranges at 10,000 blocks ("ranges over 10000 blocks are not supported on free plan").
- Python urllib against drpc needs a browser-ish `User-Agent` header (403 otherwise); curl is fine.
- Encoding discipline: build calldata in Python (`sel + word.zfill(64)`), never hand-concatenate in shell — three separate shell attempts failed on odd-length/mangled hex before moving to a script.

## When the user pushes back with "these seem to be real sales" (verified 2026-08-22)

Emad followed the verdict by pasting three etherscan tx links of actual SCHAP sales (Jul 2025, Mar 2026, Jun 2026). They WERE real — and they confirmed the diagnosis rather than refuting it. Handle this pattern as:

1. **Decode each tx on-chain** (`eth_getTransactionByHash` + receipt logs): who sold how much for how much WETH, via which pool. Don't argue from priors — read them.
2. **Read the trajectory**: 0.1156 SHCAP → 0.0643 WETH (Jul 2025), 0.0013 → 0.0041 (Mar 2026), 0.00017 → 0.00057 (Jun 2026). Each sale got ~an order of magnitude less than the last: that's a pool being drained to zero, not a market. The last sellers got paid because liquidity still existed in front of them.
3. **Re-check pool state NOW** (V3 `slot0` 0x3850c7bd / `liquidity` 0x1a686502): in-range liquidity was **exactly 0**. A quote through Uniswap V3 QuoterV2 (0x61fFE014bA17989E743c5F6cB21bF9697530B21e, `quoteExactInputSingle` selector 0xc6a5026a, struct args) reverts with **`SPL`** = the pool's own "swap can't execute at any price in range" signal — quote that revert name in your reply, it's legible proof.
4. **Then run the aggregator sweep as the final gate** (user asked for exactly this): Li.Fi `/token?chain=1&token=<addr>` → Not Found (token not even indexed); KyberSwap routes → 404; ParaSwap price/v5 → Not Found; Odos unreachable from this network; 0x Permit2 quote API requires a key ("Unauthorized"); 1inch v5.2 requires a key. No aggregator has a route ⇒ no sellable path anywhere.

## Verdict delivery

Say plainly: the displayed USD value is fake, realizable value is ~$0, gas balance is 0 anyway, and the site's numbers are classic dust-scam bait — do NOT connect this key anywhere or approve anything. If a private key was pasted into chat, tell them to treat it as burned and never reuse it (even if the wallet currently holds nothing). Keep the first verdict SHORT — one screen: what the token is, why the number is fake, the dead-pool fact, don't-connect warning. Full re-lectures on pushback read as noise.
