---
name: public-wallet-xlsx-delivery
description: "Use when Emad pastes wallets. Deliver a public XLSX."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [wallets, xlsx, google-drive, collection]
---

# Public Wallet XLSX Delivery

## Trigger

Use whenever Emad states a wallet target, begins pasting wallet addresses, or says a wallet batch is done.

## Inputs

- Optional target count stated by Emad.
- Wallet addresses pasted individually or in batches.
- Completion signal: target count reached or Emad says `done`.

## Steps

1. Treat every collection as a new campaign. Never merge it with an older wallet list.
2. Preserve each address exactly as pasted. Validate `0x` plus 40 hexadecimal characters, deduplicate EVM addresses case-insensitively, and preserve first-seen order.
3. Persist the campaign after every paste in a campaign-specific TXT under `~/Downloads/`; never overwrite an older campaign.
4. Acknowledge tersely: `#N — logged`. For a batch, acknowledge the range. Do not ask mid-collection questions.
5. Always deliver a real `.xlsx`, never a Google Doc, Google-native Sheet, CSV, or TXT. Create a numbered `Wallets` sheet with headers `#` and `Wallet`; format wallet cells as text.
6. Reopen and verify the workbook: exact count, order, strings, uniqueness, sheet, and dimensions.
7. Google Drive upload and public sharing require one consolidated approval per batch. When a target is known, obtain that one approval for upload plus `anyone-with-link` reader sharing. Never auto-approve for Emad.
8. Once approved, immediately upload when the target is reached or Emad says done; do not ask again if that approval remains valid.
9. Verify Drive metadata, permission readback, and public reachability without login.
10. Reply with the public link and absolute local `.xlsx` path.

## Failure cases

- Count mismatch: stop before upload and report expected versus collected.
- Invalid address: exclude it and identify the invalid entry.
- Duplicate: keep the first occurrence and report it at completion.
- Approval missing or expired: obtain a fresh one-time approval before upload/share, but still build locally.
- Sheets/Docs API disabled: retain `.xlsx`; upload through Drive API.

## Verification

- Programmatically compare the reopened `.xlsx` against the persisted source.
- Confirm Drive file name/type and `permissions: type=anyone, role=reader`.
- Confirm the public URL is reachable without authentication.
- Report exact count, link, and absolute local path.
