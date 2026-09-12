# The complete setup

Everything needed to run a Hermes agent that can mint, snipe, rank and audit
on-chain NFT launches, including the proof-of-work and GPU minting side.

Written to be followed top to bottom. Roughly 30 minutes if you already have a
server, longer if you need to create one.

**What it costs:** a VPS if you want the agent always on (about $5/month), and an
LLM subscription. The one that makes this cheap is OpenCode Go, around $5/month,
running `deepseek-v4.1-flash`. Everything else here is free and open source.

---

## Contents

1. [What this actually gives you](#1-what-this-actually-gives-you)
2. [Get Hermes running](#2-get-hermes-running)
3. [Connect OpenCode Go](#3-connect-opencode-go)
4. [Install the skills](#4-install-the-skills)
5. [Proof-of-work and GPU minting](#5-proof-of-work-and-gpu-minting)
6. [The rest of the minting toolkit](#6-the-rest-of-the-minting-toolkit)
7. [Connect Discord](#7-connect-discord)
8. [Verify it all works](#8-verify-it-all-works)
9. [What breaks, and why](#9-what-breaks-and-why)

---

## 1. What this actually gives you

A Hermes agent is a long-running process with a shell, a scheduler and a set of
tools. This setup gives it:

- **31 skills** distilled from real on-chain work: mint execution, rarity
  ranking that matches OpenSea rank for rank, reveal sniping, secondary buys,
  wallet forensics, contract analysis, collection production.
- **A rundown toolkit**: rarity engines, a SeaDrop multi-wallet mint tool, a
  Seaport buy path with a fill diagnostic, wallet P&L reconstruction, keyless
  volume and minter-legitimacy analysis.
- **Proof-of-work minting that actually runs at scale**: a verified CUDA kernel
  and a Modal farm that mines Hashcats over N H100 shards, verifying every
  solution against a CPU reference before it broadcasts.
- **A scheduler**, so watch-a-collection-and-ping-me jobs keep running while you
  sleep.

It runs the same on a laptop and a server. A server just means it keeps running
when you close the lid.

---

## 2. Get Hermes running

### On a VPS (recommended for anything that should keep running)

Ubuntu 22.04 or 24.04, 2 vCPU, 4 GB RAM, 40 GB disk. 2 GB is enough for the agent
alone; take 4 GB if you will run a browser or a local transcription model.

```bash
ssh root@YOUR_SERVER_IP

adduser hermes && usermod -aG sudo hermes
rsync --archive --chown=hermes:hermes ~/.ssh /home/hermes/
ufw allow OpenSSH && ufw enable
loginctl enable-linger hermes     # without this, services die when SSH closes

su - hermes
sudo apt update && sudo apt install -y git curl tmux build-essential python3-venv
```

### On your own machine

Skip straight to the install. macOS, Linux and WSL2 all work.

### Install

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc
hermes --version
hermes doctor
```

The installer handles Python, Node, ripgrep, ffmpeg, the repo clone and the
virtual environment. `hermes doctor` tells you what else it needs.

---

## 3. Connect OpenCode Go

This is the part that keeps the cost at about $5/month.

1. Subscribe at **https://opencode.ai/go?ref=0N4C2C5TNK**
2. Copy the API key from the dashboard.
3. Put it in the environment file:

```bash
hermes config env-path       # prints the file, usually ~/.hermes/.env
printf 'OPENCODE_GO_API_KEY=%s\n' 'YOUR_KEY_HERE' >> ~/.hermes/.env
chmod 600 ~/.hermes/.env
```

4. Select the provider and model:

```bash
hermes model                 # choose OpenCode Go, then deepseek-v4.1-flash
hermes chat -q "reply with OK and name the model you are"
```

The dashboard tracks two windows, a 5-hour one and a weekly one, and shows what
percentage you have used with the reset time. If you are doing long autonomous
runs, that is the number to watch.

### Why this model

`deepseek-v4.1-flash` is fast and cheap enough to leave running on a scheduler.
Tool-heavy work costs more than chat, so if you are farming a mint, check the
usage window after your first long run rather than assuming.

### Using something else

Any provider works. Set `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`,
`DEEPSEEK_API_KEY` or similar in `~/.hermes/.env`, or authenticate with
`hermes auth add <provider> --type oauth`, then pick it in `hermes model`.

---

## 4. Install the skills

```bash
git clone https://github.com/andyemad/nft-mint-rarity-toolkit.git
cd nft-mint-rarity-toolkit
./install.sh
```

That copies all 31 skills into `~/.hermes/skills/`. Use `--profile NAME` to
install into a named profile, `--dry-run` to preview, and re-running it is safe,
because it moves conflicting skills aside instead of overwriting them.

```bash
hermes skills list | head -40
hermes chat -s nft-rarity-engine -q "what does this skill let you do"
```

Extra dependencies for the signing and trading paths:

```bash
pip install eth-account coincurve pycryptodome
```

---

## 5. Proof-of-work and GPU minting

This is the part people ask about most, so here is the whole loop.

### What a PoW mint is

The contract gives you a target and asks for a nonce whose hash lands under it.
You are not clicking a button; you are searching. Two schemes are covered:

```
Hashcats   keccak256( miner(20) ‖ nonce(32) ‖ prev(32) ‖ anchor(32) ) < target
FAB4200    keccak256( chainid(32) ‖ contract(20) ‖ minter(20) ‖ nonce(32) ) < target
```

Hashcats links each token to the previous one through `prev`, and pins the round
to a block with `anchor`. FAB4200 is a straight search with a difficulty floor
(40 bits at the time of writing, which is maximum).

Both preimages fit in a single Keccak block, which is what makes a GPU kernel
orders of magnitude faster than a CPU one.

### Why CPU mining does not work

At 40 bits the expected work is around 1.1e12 hashes per solve. A laptop does
tens of millions per second. An H100 does about 7 GH/s. One of those finishes in
minutes; the other finishes next week.

### The kernel ships with a self-check

```bash
cd toolkit/pow
./hcminer selfcheck 0x<miner> 0x<prev> 0x<anchor>
```

That compares the optimised fast path against an independent reference Keccak over
200,000 nonces. There is also a `verify` mode that takes work values computed in
Python and confirms the kernel agrees with them. Run it before you rent anything,
because a kernel with an endianness bug mines forever and finds nothing.

The two bugs worth knowing: the nonce has to be byte-swapped before it is XORed
into the state word, and the leading-zero test has to run against the digest word
in the right byte order. Both are fixed in the shipped source.

### The farm

`toolkit/pow/hashcats-farm/` is the full loop: a verified CUDA kernel, a Modal
H100 farm of N shards, and local signing and broadcast.

```bash
pip install modal eth-account pycryptodome coincurve
modal setup

modal run hashcats_modal.py --mode probe     # kernel vs CPU reference
modal run hashcats_modal.py --mode bench     # GH/s on an H100
python3 hashcats.py state                    # current round
python3 farm.py --shards 4 --minutes 30 --dry   # verify + simulate, no spend
python3 farm.py --shards 8 --minutes 30 --key ~/.hermes/secrets/hashcats_key
```

Every candidate solution is verified against a Python keccak **and** re-checked
against the live round before broadcast, so a stale nonce never costs gas.

Two things that will stop you, both worth pre-empting:

- **Fund the wallet that broadcasts.** A working farm with an empty wallet
  produces nothing.
- **Read the round once, then mine.** The Robinhood RPC rate-limits per IP on
  reads and writes; a shard polling in a loop gets 429s and looks like a protocol
  error.

### Build the kernel yourself

```bash
gcc -O3 -fopenmp -o hcminer hcminer.c
nvcc -O3 -o hcminer_cuda hcminer.cu
```

Do not use `-march=native` for a cloud build: the build host is not the execution
host, and the binary dies with SIGILL. On macOS, clang has no OpenMP, so either
install `libomp` or build single-threaded with the small stub documented in
`toolkit/pow/README.md`.

**Cost expectation, stated plainly:** a GPU mint is a contest entry, not a
button. You pay for compute whether or not you land a token, and other miners are
racing the same round. Do the arithmetic on your own spend, and stop when the
round goes stale.

---

## 6. The rest of the minting toolkit

```bash
cd toolkit

# rarity: rank a collection, matching OpenSea
python3 rarity/rarity_engine.py compute
HELD="12,44,91" python3 rarity/gen_dash.py

# recon before spending anything
python3 analysis/collection_volume.py <contract> 3000000
python3 analysis/minter_legitimacy.py <contract> <deploy_block>
python3 analysis/sweep_scope.py <opensea-slug>

# SeaDrop public mint across many wallets
python3 mint/seadrop_fire.py recon  <collection>
python3 mint/seadrop_fire.py wallet <collection> 3
python3 mint/seadrop_fire.py fire   <collection> --keyfile ~/.hermes/secrets/x_key --quantity 1

# buy from secondary, dry run first
python3 sniper/buy_secondary.py <slug> --target-eth 0.001
python3 sniper/buy_secondary.py <slug> --live

# wallet P&L, mints and buys separated, gas counted
python3 wallets/wallet_recon.py <address>
```

Every spending path simulates with `eth_call` first and needs an explicit flag to
broadcast. That is deliberate. Read the README in each directory before you use
it.

For launches like **SpawnHood** (`opensea.io/collection/spawnhood`, Robinhood plus
Ordinals) the useful skills are `nft-mint-recon` for working out what the mint
actually is, `ethereum-data-pipelines` for reverse-engineering an unknown mint
site, `nft-minter-legitimacy-audit` for judging whether the minters are real, and
`rh-chain-rarity-sniping` for getting rare ones at the floor after reveal.

---

## 7. Connect Discord

Useful if you want to talk to the agent from your phone instead of a terminal.

1. **https://discord.com/developers/applications** → New Application.
2. **Bot** tab: enable **Message Content Intent**. Without it the bot receives no
   text and looks dead. Then **Reset Token** and copy it.
3. **Installation** tab: Guild Install, scopes `bot` and `applications.commands`,
   permissions `274878286912`. Or use this URL directly:

   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot+applications.commands&permissions=274878286912
   ```

4. Invite it to your server. You need Manage Server there.
5. Copy your user ID (Settings → Advanced → Developer Mode, then right-click your
   name → Copy User ID).
6. Configure and start:

```bash
hermes gateway setup        # choose Discord, paste the token and user ID
hermes gateway run          # foreground test first
hermes gateway install      # then as a service
hermes gateway start
```

Add to `~/.hermes/.env` if you configure manually:

```bash
DISCORD_BOT_TOKEN=your-token
DISCORD_ALLOWED_USERS=your-user-id
DISCORD_HOME_CHANNEL=channel-id-for-notifications
```

Without `DISCORD_ALLOWED_USERS` the gateway denies everyone. In server channels
the bot only answers when mentioned, unless you list the channel in
`DISCORD_FREE_RESPONSE_CHANNELS`.

---

## 8. Verify it all works

```bash
hermes --version                       # 1. installed
hermes doctor                          # 2. dependencies and config
hermes chat -q "reply with OK"         # 3. provider and key
hermes skills list | grep rarity       # 4. skills present
hermes gateway status                  # 5. Discord service up
tail -20 ~/.hermes/logs/gateway.log    # 6. gateway connected
```

Then a real end-to-end test with no spending:

```bash
cd toolkit
python3 rarity/rarity_engine.py compute         # needs an OpenSea key
python3 pow/hashcats.py state 2>/dev/null || true
modal run pow/hashcats_modal.py --mode probe    # kernel agrees with CPU
python3 pow/hashcats-farm/farm.py --shards 2 --minutes 5 --dry
```

---

## 9. What breaks, and why

| Symptom | Cause |
|---|---|
| Bot online but silent | Not mentioned, or Message Content Intent is off |
| Gateway up, everyone denied | `DISCORD_ALLOWED_USERS` missing or wrong |
| Bot dies when SSH closes | `loginctl enable-linger` missing, or service definition stale |
| 403 from the Robinhood RPC | Python `urllib` without a browser `User-Agent` |
| 429 from the Robinhood RPC | It rate-limits per IP on reads and writes: batch and back off |
| Kernel mines forever, finds nothing | Endianness in the nonce XOR, or the leading-zero test on the wrong byte order. Run `selfcheck` |
| Farm finds solutions, nothing mints | The broadcasting wallet is unfunded |
| GPU build dies with SIGILL | `-march=native` on a different build host |
| Rarity ranks disagree with OpenSea | Trait-frequency heuristic instead of OpenRarity information content |
| Skills installed but not loading | `/reload-skills` in a running session, or `hermes skills list` to confirm |

---

## Where things live

- **Repository:** https://github.com/andyemad/nft-mint-rarity-toolkit
- **Skills:** `skills/`, indexed in `SKILLS.md`
- **Toolkit:** `toolkit/`, each directory with its own README
- **Secrets:** `~/.hermes/secrets/`, `chmod 600`, never in the repo

Nothing here is financial advice. Every strategy in it has a real loss mode
documented next to it, and several of the skills exist specifically to record a
method that failed.
