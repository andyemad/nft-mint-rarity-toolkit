# Wave 10 — a Windows minting app Contract Minter batch planner (extracted formulas + port status)

Source: decompiled `a Windows minting app.Infrastructure.ContractMinter/ContractMinterBatchPlanner.cs`
(393 lines, pure math). TS port: `lib/server/modules/contract-minter.ts`.
Ledger: `GATES-wave10.md`.

## STATUS (end of session 2026-08-23)
PORTED AND GREEN: 23/23 tests (`tests/modules-contract-minter.test.ts`), tsc clean.
Impl+tests written by PARENT after the dispatched leaf produced zero files in its
600s budget (spent it hand-verifying formula vectors). Process rule confirmed:
when the parent already holds full understanding from its own source study, write
the module in-parent — delegation only wins when the parent lacks the understanding
or work parallelizes across disjoint domains.
Integration (route + Batch panel mode) was in flight at session close.

## Constants — exported as DEFAULT_OVERHEADS / FALLBACK_CAPS
- Overheads: intrinsic 21000, coordinatorEntry 60000, perJob 15000, callReserve 20000,
  postCallReserve 120000, safetyReserve 50000, calldataGasPerByte 16,
  calldataFloorGasPerByte 40, envelopeBytes 512.
- Caps fallback: hardGasCap 15_000_000, planningGasBudget 13_500_000, maxTxBytes 131072.
- effectiveBudget = min(planningGasBudget, hardGasCap).

## Core formulas
```
grossUpEip150(g)          = g>0 ? g + (g-1)/63 : 0        (integer div)
computeMemoryExpansion(b) = b<=0 ? 0 : w=ceil(b/32); w*3 + w*w/512
padToWord(n)              = ceil(n/32)*32
walletJobTailLength(b)    = 192 + padToWord(b)
executeCallLen(inner)     = 100 + 224 + padToWord(inner)
outerRaw = intrinsic + bytes*16 + memExp + coordinatorEntry + consumptionSum
           + largestFloorExcess + margin(safetyReserve vs consumptionSum/10)
plannedOuterGas = max(outerRaw, eip7623Floor = intrinsic + bytes*40)
```
Accumulator phase uses per-job tails (132+32n+Σtails) and PER-JOB padded execute lengths;
final recompute uses WIRE bytes with memExp over padToWord(wireBytes) ONCE.

## Packing (greedy, order-preserving)
Dedupe by taskId ("Task appears more than once in the batch input.") → validate with
VERBATIM C# reasons ("Job wallet and target must be canonical non-zero Ethereum
addresses." zero-address rejected / "Job value cannot be negative." / "Job gas budget
must be greater than zero." / "Job calldata is not canonical 0x-prefixed hex.") →
greedy loop: one mint per wallet per outer tx; !fits → fitsAlone ? close partition :
exclude permanently with "Job cannot fit the gas/byte caps on its own (gas budget N,
byte cap M)."

## Wire form
uniform (identical calldata case-insens, same target/value/gasLimit) | templated
(differ ONLY at one 20-byte window where each job embeds its own wallet at the SAME
offset — scan job0 for its own address) → 292 + padToWord(inner) + 32 + count*32;
heterogeneous → 132 + count*32 + Σ tails.

## Test vectors locked
grossUpEip150(64)=65/(63)=63/(1)=1; memExp(1024)=98/(33)=6/(32)=3; tail(4)=224;
executeLen(4)=356; heterogeneous 1-job-4B wire = 388.

## Group key (for later live-execution wave)
ContractMinterGroupKey(ChainId, TaskGroupId, ScheduledFor?, SimulationMode,
BroadcastMode, ReadRpcUrl, BroadcastRouteFingerprint, FeeFingerprint); Contract Minter
is EXCLUDED from fast-path batching (MintSubmissionMode.ContractMinter).
