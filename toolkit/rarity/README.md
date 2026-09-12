# Rarity

Rank an entire collection by rarity, detect reveals, and render the result.

The ranking formula is **OpenRarity information content**:

```
score = Σ −log₂( count(trait_value) / total_supply )
lower score = rarer
```

This matches OpenSea's rarity tab rank-for-rank (verified on a 5000-token
collection). A `1/percent` trait-frequency heuristic is NOT the same thing and
was empirically wrong — don't ship it.

## Files

| File | What it does |
|---|---|
| `rarity_engine.py` | Generic scaffold: reveal watcher + full rarity computation + wallet comparison. Start here. |
| `combox_rarity.py` | Full-supply sweep via the OpenSea v2 paginated endpoint, then rank; `fetch` / `rank` / `mine`. |
| `bakemono_rarity.py` | Same engine plus a wallet-holdings fetch, so you can rank *your* tokens against the supply. |
| `adambomb_rarity.py` | Ingest a large reference collection (traits + token copy) for studying trait architecture. |
| `gen_dash.py` | Turns `scores.json` + `traits.json` into a single-file dark HTML dashboard with rank bands. |
| `trait_sampler.py` | Sample N tokens of any collection straight from chain metadata (no marketplace API) and print per-trait distributions. |

## Usage

```bash
# generic: watch for a reveal, then compute
python3 rarity_engine.py watch
python3 rarity_engine.py compute

# full sweep of a revealed collection
python3 combox_rarity.py fetch     # -> traits.json
python3 combox_rarity.py rank      # -> scores.json

# rank the tokens you hold (comma-separated token ids)
HELD="12,44,91" python3 bakemono_rarity.py mine

# dashboard for your holdings
HELD="12,44,91" python3 gen_dash.py     # -> dashboard_out.html

# chain-metadata sampling, no API key
python3 trait_sampler.py --rpc https://eth.rpc.blxrbdn.com \
    --ca 0x<contract> --supply 5000 -n 150
```

## Config points

Each engine has module-level constants at the top: `CONTRACT`, `CHAIN`,
`SUPPLY`, `RPC`, `BASE` (where JSON state is written) and `WALLET`. Edit them, or
copy the file and treat it as a template — that is how they were written.

Data is cached on disk (`~/.hermes/rarity/<collection>/{traits,scores}.json`) so
a re-rank costs nothing.

## Pitfalls this code already handles

- **Reveal detection.** Pre-reveal, every token shares one metadata URI. Sample
  several `tokenURI`s and compare CIDs; if they are identical, there is nothing
  to rank yet. A reveal flips `tokenURI`, but OpenSea can lag behind chain.
- **IPFS gateways are unreliable.** Keep a gateway chain
  (`gateway.pinata.cloud`, `{cid}.ipfs.w3s.link`) and fall back to OpenSea's
  per-token endpoint. `nftstorage.link` began returning 403.
- **Python needs a browser User-Agent.** Default `urllib` gets 403 from both the
  OpenSea API and the Robinhood Chain RPC even with a valid key.
- **Sanity-check trait coverage.** One token with empty traits skewed hundreds of
  ranks. Compare your trait totals against the marketplace before publishing.
- **Rate limits at the reveal moment.** Bursts get 429s; urllib hides the body,
  curl shows it. Pacing is the fix (~43 min for a first 5000-token sweep).
