# Opening-Block SeaDrop Mint Forensics

Use this reference when reconstructing a fast SeaDrop mint and converting the evidence into a Windows minting app/the control room settings.

## Evidence workflow

1. Resolve the exact chain and collection contract from the marketplace API, then verify with RPC bytecode and ERC-721 reads.
2. Read SeaDrop configuration directly:
   - `getPublicDrop(address)` for price, start/end, wallet cap, fee bps, and fee-recipient restriction.
   - `getAllowedFeeRecipients(address)` for the accepted recipient.
   - collection `totalSupply()` and `maxSupply()`.
3. Scan collection `Transfer` logs whose `from` topic is zero. Group mint logs by transaction hash to recover quantity per transaction.
4. Fetch transactions and receipts. Keep these fields separate:
   - transaction gas limit;
   - receipt gas used;
   - block base fee;
   - transaction max fee and max priority fee;
   - receipt effective gas price;
   - `gasUsed × effectiveGasPrice` actually paid;
   - transaction value paid for NFTs.
5. Group by call target, selector, and quantity. Resolve selectors with OpenChain or verified ABI. SeaDrop public mint is normally `mintPublic(address,address,address,uint256)`; signed/API stages use a different selector and must not be mixed into public-mint gas statistics.
6. Find the first public-mint block and fetch the entire block with full transactions. Filter all calls to the SeaDrop target and public selector, then fetch every receipt. Count successes, reverts, quantities, transaction indices, and duplicate attempts per sender.
7. Decode representative calldata to verify collection, fee recipient, payer/minter field, and quantity.
8. Inspect failed receipts. Low gas used with a normal gas limit indicates an early contract revert (sold out, cap, duplicate), not out-of-gas.

## Turning evidence into settings

- Set gas limit from observed successful gas used plus explicit headroom, not from a winner's arbitrary gas limit.
- Never copy `maxFeePerGas` as if it were paid. Compare effective gas price and transaction ordering across low- and high-cap winners.
- If low and high priority offers all pay the same base fee and appear throughout the block, do not claim a gas-premium advantage.
- Prefer one transaction per wallet at the on-chain cap. Incrementing-nonce spam can spend gas after a wallet has already succeeded.
- Rehearse and resolve calldata before opening. At T+0, avoid blocking marketplace lookups, gas estimation, or sequential receipt waits.
- Broadcast selected wallets in parallel; monitor receipts separately.
- Permit only bounded same-nonce replacements that preserve target, calldata, value, and spend ceiling.
- Funding per wallet = mint value + `gasLimit × maxFeePerGas` + a small explicit reserve.
- Pin stage price, cap, target, calldata, fee recipient, time window, wallet set, and maximum all-in spend. Any material change invalidates rehearsal.

## DUNLAPS worked facts (Robinhood Chain, 2026-08-28)

- Collection `0xe801b3399193ad1af4e0bbcad72a45c2ff819a8f`.
- SeaDrop `0x00005ea00ac477b1030ce78506496e8c2de24bf5`.
- Public selector `0x161ac21f`; price 0.002 ETH; cap 2; value 0.004 ETH.
- Opening block 48,638,433 contained 175 public attempts: 169 successes and 6 reverts; 333 NFTs minted through normal public calls.
- Quantity-two gas used was typically 120,206; successful maximum 125,862; lowest winning gas limit 140,000.
- Opening base/effective fee was 0.068658 gwei even when winners offered max-fee caps up to 5 gwei.
- Evidence-based reusable profile: gas limit 180,000; max fee 0.5 gwei; priority 0; one transaction per wallet; parallel opening-time broadcast; spam off.

Public archive: https://dunlaps-mint-report.vercel.app

## Verification checklist

- Primary-source RPC receipts back every gas claim.
- Public, signed, allowlist, account-abstraction, and owner/batch mints are separated.
- At least one early success, late success, and failure are decoded.
- Site/report contains no keys, local paths, private wallet identifiers, or session metadata.
- Desktop and 390px mobile QA pass before external deployment approval.
