# Creating OpenSea (v2) listings on Robinhood Chain — working flow + the 500 fix

Context: programmatically listing NFTs you own from the bot wallet. This is the
**sell-side** counterpart of nft-secondary-buy. Verified diagnosis 2026-08-20.

## THE blocker: maker operator approval (the "500" fix)
OpenSea's `POST /listings/actions` returns **500 "Internal Server Error"** for a
maker listing when the wallet has NOT approved Seaport as an operator on the NFT
contract. This is collection-wide (any token from that contract 500s) and is NOT
a schema problem. Buying works without it (you are the fulfiller); **listing
requires it** (you are the maker/offerer).

Diagnose first:
```
isApprovedForAll(owner, operator)  # selector 0xe985e9c5, args = (owner, operator)
```
- contract = the NFT contract
- operator = Seaport 1.6 on RH: 0x0000000000000068f116a894984e2db1123eb395
  (also check the OpenSea conduit if in doubt — the conduitKey in existing
  listings, e.g. 0x61159fef…1d5e)
- If False → send ONE `setApprovalForAll(contract, Seaport, true)` tx from the
  wallet first. No value moves, RH gas ~0, reversible. Then relist.

## Listing flow (approved key)
1. `POST /listings/actions`
   body = {
     "address": wallet,
     "items": [{ "chain":"robinhood", "contract":CONTRACT, "token_id":"<id>",
                 "quantity":1,
                 "price":{"amount":"0.001000",
                          "currency":"0x0000000000000000000000000000000000000000"} }]
   }
2. `steps[0]["createListingsAction"]["signatureRequest"]["message"]` is a JSON
   *string* → json.loads → `m`.
3. `enc = encode_typed_data(full_message=m)` (eth_account.messages) then
   `sig = account.sign_message(enc)`.
4. Submit:
   body = {"parameters": m["message"],
           "protocol_address": m["domain"]["verifyingContract"],
           "signature": sig.signature.hex()}
   `POST /orders/robinhood/seaport/listings`

## Schema gotchas (avoid re-discovering)
- Top-level `expiration_time` and per-item `expiration_time` / `protocol_address`
  are **UNKNOWN FIELDS** → 400 "Unknown field 'expiration_time'". Do not add them;
  the signatureRequest message already carries the correct expiration/zone.
- A numeric `amount` string like "0.001000" is correct; no min-price field needed.

## If you see 401 "Invalid API key"
An OpenSea write-scope token from opensea.io/settings/developer is NOT a valid
v2 API key — that page's scopes (write:orders = cancel, write:drops, write:collections,
write:profile, write:wallets, write:tools) don't unlock order creation anyway.
Use the API key at ~/.hermes/secrets/opensea_key. Never paste a key into chat;
a pasted credential is deleted immediately after use and never stored.
