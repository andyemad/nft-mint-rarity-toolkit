# Session detail: THE POOL reveal + buy-path verification (2026-08-22)

## Collection
- FROGHOOD: THE POOL (slug `thepool`), RH chain, CA 0xfeed66d6c045d6e0c33d38b04df44ed3e42d4bed.
- 1777 supply, sold out pre-reveal, 368 owners, floor ~0.00055 ETH at check time.
- Pre-reveal tokenURI (all tokens): ipfs://bafkreihtgi5fmc4bh4guaw2cq765c75nwiznx4mfpz5vfwogttsm2gzrem
  → metadata: name "FROGHOOD: THE POOL - Unrevealed", description ends "A frog is hidden inside!"
- 48 live listings pre-reveal; cheapest real total ~0.00178 ETH.

## Buy-path proof sequence (reusable evidence pattern)
1. POST /api/v2/listings/fulfillment_data with listing hash + fulfiller=bot wallet
   → returns tx template (to = Seaport 1.6, value, input_data).
2. input_data shape decides path: `parameters` = basic order;
   `advancedOrder` = advanced. Encoder in buy.py handles both.
3. fulfillBasicOrder_efficient_6GL6yc selector is literally 0x00000000 (Yul quirk,
   verified via keccak). calldata_suffix field from API is misleading — compute the
   selector from the function signature string instead.
4. eth_estimateGas on encoded calldata from bot wallet → gas 144718 = clean sim.
5. Negative control: garbage calldata to same contract → "execution reverted".
   This two-sided test is what proves the encoder AND the RPC honesty.

## Bunker 49/49 revert post-mortem conclusion
Encoding was never the root cause. Dead orders (filled/cancelled) or value
mismatch are the leading suspects. When a fill reverts: re-fetch the listing
first; only then question encoding.

## Watcher cron
- Job dc1708b798e3 "thepool-reveal-watch", */2 * * * *, deliver origin (#ops).
- Script: ~/Projects/rh-mint-command-center/scripts/thepool_reveal_watch.py
  (silent empty stdout while pre-reveal; sweeps+rank+top10 alert on flip).
- Interpreter quirk: must run with PYTHONPATH= (empty) and
  ~/.hermes/secrets/../bunker-snipe/.venv/bin/python3 because the user-level
  ~/Library/Python/3.9 site-packages shadows venv packages otherwise.

## Approval-gate friction note
A bare "yes" approves exactly one slate. If the tooling consumes the approval
before the underlying action lands (cron.create needed a second bound slate),
re-present verbatim once — never re-confirm after an action actually succeeded.