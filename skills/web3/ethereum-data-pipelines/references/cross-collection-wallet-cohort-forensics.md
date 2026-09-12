# Cross-Collection Wallet Cohort Forensics

Use when the ask is **"find me the wallets that were early across these N collections"**
(shared minters / sweepers / a common crowd between launches), or any variant of
"who is the same set of people showing up at every drop".

Distinct from single-launch vetting (`nft-minter-legitimacy-audit`) and from
rolling watchlists (`nft-smart-wallet-watchlists.md`) — here the unit of analysis is
**the wallet set that recurs across collections**, plus per-wallet P&L and handles.

Verified 2026-09-11 on the Robinhood-Chain quartet DogiHood / ALIENS /
Robinhooders / the target collection (21,416 mints + 17,986 sales, 5,211 distinct wallets).
Working dir: `~/Projects/rh-wallet-forensics/`.

---

## 1. CRITICAL — denomination check before ANY valuation

**Never compute a sale price as `int(payment.quantity) / 10**decimals` without reading
`payment.symbol`.** On these launches the events feed mixes in stablecoin-settled sales
and the raw number looks like ETH.

```python
def pay(ev):
    """-> (eth_amount, usd_amount). Never blend the two."""
    p = ev.get("payment") or {}
    sym = (p.get("symbol") or "").upper()
    q = int(p.get("quantity") or 0) / 10 ** int(p.get("decimals") or 18)
    if sym in ("ETH", "WETH"):
        return q, 0.0
    if sym in ("USDG", "USDC", "USDT", "DAI"):
        return 0.0, q
    return 0.0, 0.0
```

Measured damage — the target collection sale events by symbol:
`{'ETH': 7.7999 (5867 sales), 'WETH': 1.3336 (1432), 'USDG': 81.52 (435)}`.

A wallet that sold five the target collection for `0.34 + 0.19 + 0.18 + 0.18 + 0.18` USDG
(= ~$1.07) was reported as **+1.07 ETH ≈ +$2,640** when the symbol was ignored. It was
the single biggest "winner" in the dataset and it was pure denomination error.
This bug has now fired twice; treat the symbol check as mandatory plumbing, not a nicety.
When reporting, give **net ETH and net stablecoin in separate columns**, and say which
launches are affected (here only the target collection had USDG sales; the other three are ETH/WETH only).

## 2. Defining "early" changes the answer by 4x — pick deliberately

Two families, very different results on the same data:

| definition | wallets in 2+ launches |
|---|---|
| entry-RANK tier (first 250 minters of each collection) | **0** |
| entry-rank tier, first 1000 minters of each | 9 |
| wall-clock first 30 min of each launch | 40 |
| wall-clock first 2 h | 145 |
| wall-clock first 6 h | 245 |
| wall-clock first **24 h** | **280** |
| wall-clock first 72 h | 352 |

Rank tiers look stricter but are wildly compressed in time: DogiHood minted its whole
4,980 supply in 1.2 h, so "first 250 minters" is roughly the **first 5 minutes**. That is
why rank tiers show almost no overlap while 24 h windows show hundreds.

Practical default: **wall-clock first 24 h of each launch = `mint >= 1 OR buy >= 1`**,
then widen/narrow and label the window in the deliverable. Absolute statement to reuse:
*"early" means the wallet minted or bought within the first 24 hours after that launch's
first event.* If you used a different cut, say so — the count swings by hundreds.

## 3. The broadest filter is "ever touched", and it is the honest denominator

Before narrowing, always compute participation at all: per collection, collect every
distinct `to_address` from mint events and every `buyer`/`seller` from sale events.

On this data: DogiHood 1,762 / the target collection 1,710 / Robinhooders 1,468 / ALIENS 940
distinct participants; **5,211 wallets total**, of which 4,794 joined exactly one launch,
415 joined two, 72 joined three, **10 joined all four**. Report this ladder first — it is
what makes the smaller cohort list legible instead of arbitrary.

## 4. Cohort assembly

Per wallet, accumulate a per-collection record while streaming events once:
`mint, early_mint, buy, early_buy, spend, sold, proceeds, usd, first_ts, first_sell_ts`,
plus `max_burst` = the largest count of mints in a single second.

Sort by `(-launches_touched, -early_launch_count, -net_eth)`. That ordering puts the
"always first" crew on top and the one-launch tourists at the bottom in one pass.

`max_burst` must skip the launch flood: a same-second set of 752 wallets is just the
public mint opening, not a coordinated ring.

## 5. Handle / identity enrichment

`GET /api/v2/accounts/{address}` (keyed, `~/.hermes/secrets/opensea_key`) returns
`username`, `ens_name`, `bio`, `social_media_accounts[]`, `website`. Extract X handles with
`[s['username'] for s in (socials or []) if s.get('platform') == 'twitter']`.

- Pace ~0.5 s/call; 430 wallets took ~5 min. Write incrementally (every 25) so a
  timeout does not lose the batch.
- Yield measured on 497 wallets: **426 had an OpenSea handle, only 45 had an X handle**.
  Most of this crowd is pseudonymous on OpenSea only — do not imply X presence you
  did not resolve.
- A `bio` field carrying a `VULCAN-xxxxxxxx` / `VERIFY-` / `GREMLIN-` / `gate` code is a
  third-party verification-gate tag. It shows up over-represented in multi-launch crowds
  (26.6% vs 13.6% baseline in the earlier pass) but is NOT identity and NOT proof of a
  shared operator.

## 6. Pattern battery — what to actually compute

Run all of these; they answer "find more patterns" without hand-waving:

1. **Attendance ladder** (§3) — ever / 2 / 3 / all.
2. **Carryover decay between consecutive launches** — `|early_a ∩ early_b|` as a % of the
   later launch's early set. Measured 9.1%, 9.0%, **3.6%** — the crowd thins as the
   series goes on; the freshest launch drew the fewest returning wallets.
3. **Supply concentration** — top-15 minters' share of each launch's mints. This is the
   launch-fairness tell and it varied enormously: **ALIENS 21.9%**, the target collection 10.2%,
   DogiHood 6.7%, **Robinhooders 1.5%**. High share ≈ big allowlist allocations to few
   wallets, low share ≈ flat public mint.
4. **Per-wallet mint-count fingerprint** — the modal exact mint count per collection.
   Here a hard **5-per-wallet cap** dominates (750 DogiHood, 942 Robinhooders, 847
   the target collection wallets minted exactly 5) while ALIENS used 10/20/50 allocations. A recurring
   cap is the signature of one mint engine / one allowlist policy, not of one person.
5. **Flip speed** — first-sale minus first-mint per wallet: median, p25/p75, and % sold
   under 30 min / under 3 h. Median here 142–146 min on three launches; Robinhooders had
   39% out inside 30 minutes.
6. **Internal trade ring** — count sales where buyer AND seller are both in the early crew.
   Here 617 such sales across 266 distinct pairs, biggest loop 24 sales between two
   wallets. Repeated two-way churn between crew members is wash-adjacent; report the pair
   list, not just the total.
7. **Co-mint clustering** — see §7; the answer is usually "not evidence".

## 7. Negative findings to state out loud (prevents over-claiming)

- **Same-second co-minting is NOT coordination.** Grouping mints by `event_timestamp`
  produces thousands of same-second wallet pairs (6,801 here) — but **zero pairs recur in a
  second launch**. The clusters are the organic public-mint flood. Do not present a
  same-second graph as a bot-ring finding.
- **Bots and profit are weakly related.** The 53 wallets that batch-minted 10+ tokens in one
  second were as likely to be down as up; the largest batch minter was a net loser.
- **The cohort is not a whale cohort.** Total net across all 497 multi-launch wallets was
  **+1.475 ETH (~$3.6k)**; 325 profitable vs 162 underwater; the largest single ETH winner
  was ~+0.15 ETH. Say the absolute number, not the multiple.

## 8. Deliverable shape (the user's correction — embed this)

The demand was for a readable list of wallets that were early across all of these
projects. A methodology-first answer was rejected, and a thin list was pushed back on:
there had to be more patterns than the obvious ones.

Therefore:

- **Lead with the list.** Plain numbered wallet lines: address, handle(s), one-line net.
  Analysis comes after, compressed into short bolded claims.
- **Never open with how you got it.** No pipeline narrative, no confidence preamble.
- **Do not stop at the narrowest intersection.** If "all N collections" yields ~10 wallets,
  immediately build the next tier up (3 of N, 2 of N) and the pattern battery *before*
  replying. A thin list is a wrong answer.
- **Give the counts ladder** so the list has context: X wallets touched the launches, Y in
  2+, Z in 3, N in all.
- **Corrections go first.** If a number in a previous reply was wrong, lead the next reply
  with the correction and the corrected figure.
- Full data goes to an `.xlsx` with one tab per pattern group (all-N / early-in-N-1 /
  in-2 / winners / losers / pure flippers / pure sweepers / batch minters / ALL), and the
  **absolute path** is given in the message — never a MEDIA attachment.

## 9. Reusable scripts in `~/Projects/rh-wallet-forensics/`

| script | purpose |
|---|---|
| `fetch_events.py` | page the OpenSea v2 events feed into `data/{slug}_{mint,sale}.json` |
| `build_all.py` | single-pass per-wallet aggregation, **denomination-safe** (§1) |
| `enrich_all.py` | `accounts/{addr}` identity enrichment, incremental writes |
| `deep.py` / `deep2.py` | rank tiers vs wall-clock tiers, burst clusters, overlap matrix |
| `comint.py` | same-second co-mint pairs across launches (§7 negative result) |
| `speed.py` | flip-speed + supply-concentration stats |
| `build_workbook.py` | 10-tab `.xlsx` deliverable |

Rebuild order after a fresh fetch: `build_all.py` → `enrich_all.py` → `build_workbook.py`.

## 10. Sources that were NOT usable this session

Do not plan around these without re-probing — they were blocked on 2026-09-11:
`robinhoodchain.blockscout.com/api/v2/*` returned **403 Forbidden** for address,
`/transactions`, and `/transaction` lookups from this Mac (browser UA did not help), so a
shared-funder / sybil trace could not be completed. If funding-source proof is required,
re-probe Blockscout first; if still blocked, say the trace is incomplete rather than
implying no common funder exists.
