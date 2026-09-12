# Multi-collection reveal sniper (bunker-snipe) — v2, 8/25

`~/Projects/bunker-snipe/clay_sniper.py` was rebuilt from single-collection
(Clay StonKz) into a parallel multi-collection reveal sniper after it lost the
Clay reveal race. This file is the design + ops reference.

## Why the Clay race was lost

OpenSea indexed revealed traits instantly, but the sniper's reveal DETECTION
only watched on-chain tokenURIs, and its rank pipeline wasted time on dead
IPFS gateways before falling back to OpenSea. Detection lag, not ranking,
was the bottleneck.

## v2 architecture

- `COLLECTIONS` list at top of the file; each entry:
  `{ name, contract, slug, supply, pre_uri }`. `pre_uri: null` when the
  contract gates/reverts tokenURI (e.g. The Bandits
  0x2e0a…355a on robinhood, 1764 supply).
- Collections are watched as PARALLEL THREADS every tick (~3s poll;
  ~11 full cycles / 10s incl work). Poll clamp in code is `(2, 120)` so 3s is
  legitimate; params live-edit at `~/.hermes/rarity/snipe_params.json`
  (`poll_secs`, `top_ranks`, caps) — picked up next tick without restart.
- **Dual-channel reveal detection** per collection:
  A) on-chain URI differs from `pre_uri`, OR
  B) OpenSea `/nfts` returns tokens WITH traits (the universal signal for
     gated contracts that revert every ownerOf/tokenURI).
- Ranking: OpenSea traits primary (fast, seconds for ~2k–7k supply), IPFS
  fallback with gateway chain (pinata first; nftstorage.link 403s from this
  Mac). Per-collection ranks cached at `~/.hermes/rarity/<name>/scores.json`.
- SHARED wallet-level caps across all collections (can't be blown past by two
  simultaneous reveals): max buys, per-buy cap, daily cap, reserve floor.
  Every buy eth_call-gated before broadcast; pings @operator per buy.
- State: `~/.hermes/rarity/snipe_state.json`.

## Adding a collection

Append to `COLLECTIONS`: name, contract address, OpenSea slug, totalSupply,
and pre-reveal URI if known (else null). Find candidates via OpenSea search
API `/collections?chain=robinhood&q=<name>` then verify chain + supply +
pre-reveal state via the contract endpoint and a trait probe.

## Ops notes

- Daemon detaches from its wrapper — a background-process "exited" notice is
  usually a false alarm. Check `ps aux | grep clay_sniper` and the log tail
  (`~/Projects/bunker-snipe/clay_sniper.log`) before restarting.
- Honest speed limit: detection is instant-ish (one poll cycle), but
  rank+match adds ~2–4s from OpenSea traits before a buy can fire. That is
  near the floor with OpenSea's API.

## Emad's expectations for this tool (learned 8/24–8/25)

- He was blunt after the Clay race loss ("rarity loaded on opensea before you
  were able to do shit… we have to make money"): this is a MONEY tool, speed
  is the product. Report honest limits up front, then close them — don't
  defend the old design.
- He verifies claims himself and catches gaps ("I don't see the x anywhere").
  Never claim a UI feature works without either a served-bundle grep or his
  confirmation; tell him to Cmd+Shift+R when shipping client-side changes.
- Every follow-up in one session (sort, labels, smooth loading, delete,
  no-default) was treated as part of ONE delivery, not new tasks. Keep
  iterating on the same artifact without re-asking scope.
