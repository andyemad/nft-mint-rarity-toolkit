# Ethereum NFT Contract + Supply Audit

Use this workflow when asked for actual max supply, minted/unclaimed/reserved allocations, creator controls, mint mechanics, metadata/royalties, holder concentration, and price-relevant contract risks. It was validated on a custom ERC-721 whose `totalSupply` was absent and whose allocation lived in SSTORE2 bytecode.

## Evidence hierarchy

1. Verified Solidity and ABI from explorer/RouteScan `contract&action=getsourcecode`.
2. Direct `eth_call` at a stated cutoff block for live configuration.
3. From-zero `Transfer` logs and custom mint events for minted supply and allocation.
4. SSTORE2/runtime bytecode for frozen trait tables and ID pools.
5. Full `Transfer` history for current holders.
6. Explorer transaction history for owner setup calls and calldata.
7. Marketplace API/page only for external fees, floor/listings, and indexer cross-checks.

Always state the block/time cutoff and separate contract facts from economic inference.

## Hard-cap analysis

Do not equate `MAX_ID` with collection supply automatically. Determine:

- valid token-ID range, including special ID 0;
- whether every ID is live or some are retired in a trait table;
- every mint path (`claim`, public sale, reserve/owner mint, site token, airdrop);
- whether burns exist;
- whether the owner can reclassify unminted IDs among allocations;
- whether an upgrade/proxy could add mint paths.

A contract with IDs `0..9999` can have 10,000 ERC-721s even when only 9,999 are artwork tokens. Report both numbers.

## SSTORE2 allocation reconstruction

SSTORE2 pointers usually reference contracts whose runtime bytecode is `0x00 || data`. For each pointer:

1. `eth_getCode(pointer, cutoffBlock)`.
2. Remove the leading STOP byte (`0x00`).
3. Decode according to source layout (for example, seven-byte trait rows or big-endian uint16 IDs).
4. Validate length, uniqueness, ID bounds, and any retired marker.
5. Compare the decoded count with public state such as `poolTotal`.

For trait tables, count live rows rather than assuming every possible ID exists. For pool tables, verify unique IDs and intersection with reserve IDs.

## Reserve reconstruction

A reserve mapping may have no event. Decode successful setup-call calldata:

- identify every `reserveOwner(uint256[])`-style call from deployment onward;
- ABI-decode each dynamic array and deduplicate IDs;
- decode subsequent owner-mint calls to establish initial recipients;
- compare reserve IDs with the immutable pool and current owners.

Treat source comments like “never sold” as non-binding unless transfer logic enforces them. After owner mint, ordinary ERC-721 transfers usually make reserve inventory liquid.

Also distinguish **reserve designated so far** from **immutable reserve cap**. If the owner can mark additional non-pool IDs reserved, disclose that remaining claim inventory can be redirected into owner inventory.

## Mint accounting

Use custom events as ground truth for allocation mechanics:

- `Claimed` = signed/free claims;
- `Assigned` = random pool tokens actually minted;
- `Picked` = paid chosen IDs;
- owner-mint and special-token events = reserved/special supply;
- `DrawSkipped` / `AssignmentUnfilled` = paid obligations that may not have minted.

Outer account-history APIs can omit contract-forwarded calls. If successful outer mint calls account for fewer tokens than `Assigned` events, do not label the difference unpaid. Reconcile it using:

- assignment-request and assigned-event counts;
- exact-payment invariants in source (`msg.value == count * price`);
- internal/state-change traces when available.

Report direct outer-call value as an observed lower bound and contract-implied gross separately when necessary.

## Holder reconstruction

Scan all ERC-721 `Transfer` logs from deployment through the cutoff:

- require exactly four topics;
- from zero = mint;
- to zero = burn;
- otherwise set `owner[tokenId] = to`.

Compute holders, top 1/10/25 concentration, balance buckets, and single-token-holder share. Profile top addresses as EOA/contract and separate known reserve recipients from external whales. Marketplace/explorer holder counts are cross-checks and can lag by one or more addresses.

Useful risk views:

- top holders including team/reserve;
- largest external holder;
- top external holders after excluding known reserve recipients;
- free overhang as both `% final supply` and `% current minted supply`.

## Creator-control checklist

Check live values and mutability for:

- owner and pending owner; EOA versus multisig/contract;
- proxy/upgradeability;
- sale/claim open flags and price;
- claim and sale signers;
- renderer/site/base URI;
- reserve designation and owner mint;
- marketplace pointer;
- print/reveal/metadata state setters;
- ownership transfer/renounce.

A locked current renderer does **not** make collection metadata immutable if the NFT contract owner can replace the renderer. Explicitly test both module lock state and parent-contract replacement authority.

## Royalties and transfers

For royalties:

1. Call `supportsInterface(0x2a55205a)` for ERC-2981.
2. Inspect ABI/source for `royaltyInfo` or custom settlement restrictions.
3. Check marketplace fee configuration separately.
4. Distinguish platform fees from creator royalties and contract-enforced from optional marketplace royalties.

For transfers, inspect custom hooks and approval overrides. Report pause, blacklist, operator filter, soulbound behavior, taxes, forced marketplace, burn, or lack thereof. Note `_mint` versus `_safeMint` only as a contract-recipient compatibility risk, not a general transfer restriction.

## Price-risk framing

Lead with mechanically actionable overhangs:

- unminted free claims;
- mutable signing authority;
- ability to redirect claims into reserve;
- already-liquid reserve inventory;
- metadata replacement/freeze risk;
- upgradeability or hidden mint paths;
- concentrated holders.

Separate historical/spent risks (for example blockhash randomness after all assignments completed) from ongoing risks. Positive controls worth stating include hard ID cap, non-proxy source, frozen allocation tables, exhausted sale pool, no burns, and completed assignments.

## Verification checklist

- Verified source and deployed bytecode match?
- Cutoff block/time stated?
- All mint paths enumerated?
- Special token IDs included?
- SSTORE2 tables decoded from runtime bytecode?
- Reserve calldata decoded when no event exists?
- Mint events reconciled with `Transfer` mints?
- Burns checked?
- Holder map reconstructed rather than copied blindly?
- Team/reserve recipients separated from external whales?
- ERC-2981 tested directly?
- Metadata-module lock distinguished from parent replacement power?
- Facts and inference labeled separately?
- No transactions broadcast?
