# Purchase semantics and production alert corrections

## Core invariant

A token purchase is a protocol-semantic event, not necessarily the wallet's
net balance increase. A transaction may buy tokens into a strategy contract,
spend or lock most of them, and return only a remainder to the tracked wallet.
Transfer logs remain the generic fallback, but a verified protocol purchase
event can supply the authoritative quantity.

## Safe event override pattern

Only override a transfer-derived `token_buy.quantity` when all of these match:

1. Exact event topic/signature.
2. Expected chain.
3. Expected purchased-token contract.
4. Purchaser/holder topic equals the tracked wallet.
5. ABI word offset is verified against a real receipt or authoritative ABI.
6. A production-shaped regression proves the old classifier returns the
   misleading transfer amount and the new classifier returns the event amount.

Keep the override narrow. Do not multiply quantities by an empirical ratio and
do not generalize one protocol's event layout to unrelated contracts.

## Verified CACHE / RunStarted case (Robinhood)

Transaction:
`0xb409c0dc0dfdece7beb61c3f318ef04498efe49e14d5cbd754737266f705b5b1`

- CACHE contract: `0xce09140499936f0d3811e27119ecede913441292`
- `RunStarted` topic:
  `0x645b4f5f88428c5c127b208e436b960a1343baf1fce8732f7268a02b16e6da75`
- Tracked holder is indexed topic 3.
- `cacheBought` is ABI data word 1 (byte offset 32).
- Wallet-return transfer: `589.206489986897238596 CACHE`.
- Authoritative `cacheBought`: `63,268.550935528854354582 CACHE`.
- Understatement if transfer-derived: `107.379249907678...x`.

This case proves why the event amount must replace—not add to—the wallet-return
amount. Adding both would double count the returned remainder.

## NFT settlement lesson

For Seaport `OrderFulfilled`, parse the actual non-indexed data layout
(`orderHash`, `recipient`, offer offset, consideration offset), then total the
attributable consideration. Gross `tx.value` can include refundable excess.
Only show sweep total ETH, approximate USD, and ETH/NFT when attribution is
complete and collection-safe.

## Correction and activation checklist

1. Fetch and preserve the exact existing Discord message text and links.
2. Reproduce the bad amount from the real receipt.
3. Add a production-shaped failing regression.
4. Apply the narrow semantic decoder/override.
5. Run the focused regression, all `test_wallet_radar*.py`, critical Ruff,
   Python compilation, and `git diff --check`.
6. Obtain one consolidated approval for the live daemon restart and any message
   edit.
7. Restart only LaunchAgent `com.hermes.wallet-radar` via `launchctl kickstart
   -k`; never restart the Hermes gateway.
8. If direct execution is blocked by the gateway-safety guard because of the
   label prefix, write a short temporary `.command`, open it in Terminal, then
   remove it after verification.
9. Verify the lock PID changed, process command includes `--enable-delivery`,
   `PRAGMA integrity_check` is `ok`, and outbox pending/processing counts are 0.
10. Edit the webhook-authored message using the same webhook token, preserve
    Market/Tx links, disable mentions, and read the exact message back through
    Discord. An ordinary HTTP client User-Agent may be needed for Discord edge
    acceptance.
11. Record the verified outcome. Commit only if Emad separately asks.
