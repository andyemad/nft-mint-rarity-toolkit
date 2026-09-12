# Fresh ERC-20 Launch Forensics ("a token connected to <person>")

Verified 2026-09-11 on PRTSCN, an unverified ERC-20 on **Ink** (Kraken L2,
chain 0xdef1 = 57073), surfaced by a third-party tweet claiming an on-chain
connection to a known founder. Deliverable was: is the connection real, is the
market live, what is it worth, what is the actionable venue.

Sibling references: `dev-wallet-connection-forensics.md` (operator-wallet
intersection tests, Ink endpoints), `nft-fud-scam-claim-verification.md`
(accreditation/FUD claims), `nft-holder-profiling.md`.

## 0. Inputs and endpoints

- Ink RPC: `https://rpc-gel.inkonchain.com` (chainId `0xdef1`). `rpc.inkonchain.com`
  and `ink.llamarpc.com` returned empty — keep the `gel` host as primary.
- Ink Blockscout v2 (keyless): `https://explorer.inkonchain.com/api/v2/`
  - `addresses/{addr}` → `name`, `is_contract`, `is_verified`, `creator_address_hash`,
    `creation_transaction_hash`, `coin_balance`, `public_tags`, `is_scam`,
    `token` (embedded ERC-20 summary incl. `holders_count`, `total_supply`)
  - `addresses/{addr}/transactions`, `/internal-transactions`, `/token-transfers`
    (add `?type=ERC-20`), `/token-balances`
  - `tokens/{addr}`, `tokens/{addr}/holders` (paginate `next_page_params`),
    `tokens/{addr}/transfers`, **`tokens/{addr}/counters`** → `{token_holders_count,
    transfers_count}` (cheap "is anything happening" probe)
- Method-ID naming: `https://www.4byte.directory/api/v1/signatures/?hex_signature=0x<sel>`
- `ens_domain_name` comes back ON transfers/`address` rows (`cruelhand.eth`) — free
  identity when the operator uses a name.

Fetch these from **Python `urllib` inside `execute_code`, not `curl | python3`** —
that pipe shape trips the HIGH pipe-to-interpreter security scan and blocks the turn.

## 1. Name the unknown contract from its OWN observed methods

An unverified token has no ABI, but its method IDs are public. Two steps:

1. Pull every tx/transfer row touching the address and collect distinct `method` values.
2. Resolve each 4-byte selector at 4byte.directory.

PRTSCN result: `0x8a8c523c` = `enableTrading()` and `0x4022b75e` =
`airdropTokens(address,address[],uint256[])`. That single lookup turned "unverified
blob" into "launch token with a trading gate and a push-airdrop function" and framed
the whole audit. `0x095ea7b3` approve / `0xf305d719` addLiquidityETH are the
recognizable neighbours that tell you it is a launch sequence.

## 2. Attribute the batch airdrop by grouping transfers

When the token dashboard shows ~1,200 transfers and 1,200+ holders, do not assume a
contract did it. Fetch the full transfer list (`tokens/{addr}/transfers`, paginated)
and group:

```python
collections.Counter((t["from"]["hash"], t.get("method")) for t in items)
```

PRTSCN: **1,260 of 1,263 transfers came from ONE wallet, method `0x4022b75e`
(airdropTokens)** — i.e. the founder personally pushed the airdrop to holders, not a
distributor contract. Plus 2 mints (from 0x0) and 1 addLiquidity. That grouping is
the evidence for "the founder is doing real on-chain work for holders," which is a
genuinely different claim from "a token appeared."

## 3. Confirm the "connected to X" claim

Do not accept or reject on vibes — check the four hard links:

- **Creator link**: `creator_address_hash` of the TOKEN vs of the NFT/project
  contract. PRTSCN's NFT contract `0x3ea71c6a…e448` was created by `cruelhand.eth`
  (`0x7171E64E…7866`, bio "shipping at @inkfndhq") — verified source, so the person
  link is airtight.
- **Flow link**: who holds what. 60% of supply (266.4M) went straight to
  `cruelhand.eth`, who then ran the airdrop; the token owner() and the deployer are
  the OTHER wallet. Different roles, same project.
- **Fund link**: the deployer EOA's inbound funding tx (see §4).
- **Interface link**: does the ERC-20 name/symbol match the collection (PRTSCN/PRTSCN),
  and does supply divide cleanly by the collection size (444,000,000 = 4,440 × 100,000)?

Then answer the tweet's own premise **separately** from its conclusion. Here the
premise ("isn't even live for trading yet") was wrong — `enableTrading()` had fired at
22:00:49, 12 minutes after deploy — while the observed conclusion (no functioning
market) was right for a different reason (nobody ever traded it).

## 4. Rug surface: deployer history, LP custody, funder template

1. **Deployer tx list, oldest page.** A launch burner shows a handful of txs:
   fund → deploy → approve → addLiquidityETH → enableTrading → airdrops. PRTSCN's
   deployer had **8 lifetime txs** and was funded with 0.5845 ETH **4 minutes** before
   deploy.
2. **Where the LP lives — the decisive check.** Find the pair, then read the PAIR's
   own holder list:
   `tokens/{pair}/holders` → if 100% of UNI-V2 sits in the deployer EOA (PRTSCN:
   9,423.375 LP, unlocked, unburned), the operator can pull the entire pool at any
   moment. That is a rug flag regardless of how good the story is. Burned (0x0) or a
   timelock contract are the benign readings.
3. **Funder's prior launches.** Walk the funder's token-transfers/transactions: the
   PRTSCN funder had **pulled liquidity from a different token ("Otomate" OTO, 550M
   supply) 25 minutes earlier**, then redeployed the same 0.5-ETH pattern. Same
   deploy → seed → airdrop → leave-LP-unlocked sequence = a repeatable launch
   template, not a one-off.
4. Pool shape: V2 pair via router `getPair`/reserves (`getReserves` 0x0902f1ac →
   uint112 ×2 + uint32 ts). Remember native is wrapped — Ink token0 was
   `0x4200…0006` (WETH), so "reserve0 = 0.5" is 0.5 WETH, not native ETH.

## 5. Prove "no market" the right way (and the trap)

**Do not report zero volume from a failed log query.** On this session the
`eth_getLogs` chunks over the pair all returned HTTP 400 (range/params rejection) and
a careless read printed "TOTAL swaps: 0" — a conclusion built on zero successful
queries. Negative evidence must come from a successful read:

- `addresses/{pair}/transactions` → **0 items** (no swaps, no adds, nothing).
- `addresses/{pair}/token-transfers` → only the two `addLiquidityETH` rows
  (the 0.5 WETH in, 177.6M tokens in).
- `tokens/{token}/counters` + the newest transfer timestamp → last movement was
  minutes after launch, days ago.

Together those three are a real proof of a dormant pool. If a log range fails,
fail over (smaller range, other provider) or use the explorer lists — never convert
failure into a zero.

## 6. Value it honestly, then name the actionable venue

- Pool price = `reserve_wrapped / reserve_token`; PRTSCN = $0.0000074, TVL $2,610,
  FDV ≈ $3.3k vs an NFT market cap of ~$880k (4,440 × $198 floor).
- Airdrop value = per-NFT allocation × pool price. Per-NFT allocation is derivable
  from holder data: `token_balance ÷ NFT balance` per address (PRTSCN ≈ **62,506
  tokens/NFT**, ≈ $0.46; one holder showing 4× = tier-weighted distribution, so
  sanity-check two or three addresses before generalising a flat ratio).
- **Then say where the thesis actually trades.** With a $2.6k pool, no DEX listing,
  no UI and a chain the user's stack does not cover, the token is not a venue — the
  NFT floor is. Emad's framing: state the tradeable instrument, not the narrative.
- Note the airdrop snapshot problem: a one-shot push to holders on day one means
  later buyers receive nothing; compare NFT-holder count vs token-holder count
  (1,940 vs 1,261 here) to flag who is excluded and whether a future claim is plausible.

## Output shape that landed

Tweet premise verified/contradicted up front → the confirmed person-link with the
address that proves it → supply/flow split → red flags (unverified, unlocked LP,
burner deployer, funder template) → what the NFT/token is worth at the only real
price → bottom line: real founder link, zero utility announced, zero market, and the
instrument that would actually express the thesis. Then offer a watcher (floor/volume,
new swap, founder announcement) rather than assuming a buy.
