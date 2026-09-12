# Clay StonKz reveal 8/24-25 — post-mortem + multi-collection sniper v2

## What happened at the reveal (the loss)

Timeline: artist announced reveal → Emad relayed twice → daemon was still
logging "pre-reveal" while OpenSea had ALREADY indexed all 6889 tokens with
traits. The daemon's OS-traits ranking source returned "0 tokens w/traits
across 35 pages" — a false negative caused by stale in-process state, not the
endpoint. Meanwhile IPFS fallback failed because nftstorage.link 403s. Net:
Emad's Mint Room rarity page showed the 503 "Reveal seen but metadata not
fetchable yet" and ranks appeared on OpenSea before our tooling. Emad: "rarity
loaded on opensea before you were able to do shit."

Root causes, in order of impact:

1. **Reveal detection watched only on-chain tokenURIs.** For a gated contract
   (Clay reverts every ownerOf; tokenURI flips late relative to OS indexing),
   on-chain is NOT the fastest signal. Fix: dual-channel detection — on-chain
   URI change OR any traited token in `GET /api/v2/chain/robinhood/contract/
   {CA}/nfts?limit=10` (one request, ~0.1s).
2. **Stale daemon process state** made the working OS pagination return 0.
   Diagnostic order that works: direct endpoint test with the key → reproduce
   function in isolation → restart daemon. Don't conclude "not indexed yet"
   until step 1 passes.
3. **Mint Room /api/rarity used ONLY nftstorage.link for metadata** (dead
   gateway) and **/api/rarity-gallery read only `process.env.OPENSEA_API_KEY`**
   which doesn't exist — the key fallback lives in
   `lib/server/opensea-listings.ts apiKey()` reading
   `~/.hermes/secrets/opensea_key`. Both routes now use OS-primary +
   pinata-fallback and share the secret-file key loader.

## Multi-collection sniper v2 (bunker-snipe/clay_sniper.py)

Rewritten from single-collection to a COLLECTIONS list processed as parallel
threads each tick:

```python
COLLECTIONS = [
    {"name": "claystonkz", "contract": "0xde0ace…1b44", "slug": "claystonkz",
     "supply": 6969,
     "pre_uri": "ipfs://bafkreiavsv…3itq"},
    {"name": "bandits",    "contract": "0x2e0a87e6…355a", "slug": "the-bandits",
     "supply": 1764, "pre_uri": None},   # gated → OS traits is the signal
]
```

- Shared wallet-level caps across ALL collections:
  `~/.hermes/rarity/snipe_params.json` (max_buys, max_per_buy_eth,
  daily_cap_eth, reserve_eth, top_ranks, floor_mult, poll_secs), state in
  `~/.hermes/rarity/snipe_state.json`, per-collection ranks in
  `~/.hermes/rarity/<name>/scores.json`. Caps are shared so two simultaneous
  reveals can't blow past limits.
- To add a collection: append to COLLECTIONS (pre_uri null if gated). Find
  slug/supply via keyless `/collections/{slug}` or search
  `/collections?chain=robinhood&search=NAME`.
- Verified cadence: ~11 full check cycles per 10s wall clock across both
  collections (poll_secs=3 + ~0.5-2s work per tick).
- Bandits specifics: tokenURI returns EMPTY string (gated differently than
  Clay's revert); supply 1764; pre-reveal 8/25.

## Speed floor honesty

Detection is ~instant (single OS request). Rank+match adds ~2-4s for 1764
tokens via OS traits (200/page × 9 pages). Total time-to-buy-signal after flip
≈ 4-6s. Near the floor for OpenSea-API-based tooling; going faster would need
websocket/event subscription on the contract.
