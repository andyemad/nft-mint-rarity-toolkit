# Contracts

Solidity sources for the drop mechanics described in
`skills/web3/nft-collection-production/`.

## `DecayedMint.sol`: reset-on-mint decaying price

An ERC-721 that starts at a high price, decays toward a floor every block, and
**resets to the start price on every mint**. Early minters pay more; the decay
rewards whoever mints next; the reset means the price never sits at the floor
while the drop is alive.

```solidity
uint256 public constant MAX_SUPPLY   = 10_000;
uint256 public startPrice            = 0.1 ether;
uint256 public floorPrice            = 0.0001 ether;
uint256 public decayPerBlock         = 0.003 ether;   // 33 blocks to floor
uint256 public lastResetBlock;
```

Accompanying mechanics in the source: `setPrices` and `withdraw` (owner),
refunds (overpayment), deterministic trait seeds, custom errors
(`SoldOut`, `InsufficientPayment`, `InvalidPriceConfiguration`, `RefundFailed`).

**Disclaimer that matters:** the trait seeds are deterministic and predictable,
not secure randomness. Do not use this contract to promise a fair or
unguessable raffle.

Build against OpenZeppelin v5 (`ERC721`, `Ownable2Step`, `ReentrancyGuard`,
`Base64`, `Strings`). `compile_check_sol.py` is a lightweight source check for
imports and obvious structural problems before you reach for Foundry/Hardhat:

```bash
python3 compile_check_sol.py DecayedMint.sol
```

## Before you deploy anything

- Compile cleanly and run the mechanism tests, not just the compile.
- Prove the price curve arithmetically (the companion project in the skills ships
  a `price_proof.js` that replays the curve block by block).
- **Never deploy a real-money mint before the distribution/demand gate passes.**
  The lifecycle documented in `nft-collection-production` is distribution first,
  deploy second. A contract has never sold a collection.
- Sanity-check royalty and metadata-replacement authority before mint day: who
  can change the base URI after sale, and does the marketplace respect it?
