# Robinhood Chain (Arbitrum L2) gas + sweep — Kuantom 2026-09-01

## Symptom cluster
- `eth_estimateGas` for plain ETH transfer returned `0x5309` (21257) and `0x530c`, not 21000.
- Sending with `gas=21000` and correct `maxFee` failed 5 times: `intrinsic gas too low`.
- Sending legacy `gasPrice` at the quoted value failed: `max fee per gas less than block base fee: maxFeePerGas: 312720000 baseFee: 319668000`.
- Success required `gas = eth_estimateGas` (21257) and `maxFeePerGas = max(baseFee*1.2, 700_000_000)` with `maxPriorityFeePerGas=10_000_000`.

## Verified working path (sweep after NFT transfer)
- `est = eth_estimateGas({from, to, value: 0x1})` → `0x5309`
- `bal = eth_getBalance(bot)`; `base = eth_getBlockByNumber(latest).baseFeePerGas`
- `maxFee = max(int(base*1.2), 700_000_000)`; `gas = est` (21257), not 21000
- `send = bal - gas*maxFee` → broadcast type-2 tx succeeded: `0xc271c87e...f17dc7a` (gasUsed `0x5246`)
- Prior NFT `safeTransferFrom` needed `gas=71641*1.2` ≈ 85969, succeeded: `0xc10356be...38cde` (gasUsed `0x1144c`)

## Lesson
Hardcoded 21000 is an L1 assumption. On RH/Arbitrum, always estimate. Buffer maxFee above the live baseFee; the quoted `eth_gasPrice` can be stale by the time the tx lands.
