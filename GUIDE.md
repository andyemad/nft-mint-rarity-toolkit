# Set up your own minting agent

A step by step guide to running an AI agent on your own computer (or a cheap
server), talking to it through Discord, and giving it 31 ready-made NFT skills.

You do not need to code. You do not need a mining rig. The total cost is about
**$5 a month**, and most of the optional extras are free.

This file is the same guide as the published page at
https://andyemad.github.io/nft-mint-rarity-toolkit/

---

## What you are actually building

Hermes is an AI assistant that runs on your own machine. Unlike a chat website, it
can do things: open pages, read the blockchain, run a script, watch a collection
overnight and message you when something happens.

This toolkit adds 31 skills to it. A skill is a set of instructions the agent loads
when a job comes up. You never run them yourself. You type in Discord, in normal
English:

> **You type:** "rank everything in this collection by rarity and tell me which ones
> are listed cheap"
>
> **It does:** reads the collection, scores every NFT, pulls the listings, and
> answers in the chat.

After setup you never have to open a terminal again. Discord is where you live.

---

## What you need

| You need | Cost | Why |
|---|---|---|
| A computer, or a rented server | $0, or ~$5/month for a server | Your own computer works. A server means it keeps running when you shut the laptop |
| A Discord account | Free | How you talk to the agent, from your phone or desktop |
| An OpenCode subscription | ~$5/month | The agent's brain. The only thing you have to pay for |
| A Modal account (GPU minting only) | Free, includes $30/month of compute | Some mints need heavy computing. You rent it by the second instead of buying hardware |

**You do not need a mining rig or an expensive graphics card.** Everything runs on
an ordinary laptop. When a mint needs heavy computing you borrow it for a few
minutes on the free credits.

---

## 1. Install the agent

You paste one line into a terminal. That is the hardest part of the guide.

**Windows** — open the Start menu, type `PowerShell`, open it, paste:

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

**Mac** — press Command + Space, type `Terminal`, open it, paste:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

**Linux** — same as Mac:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

The installer fetches everything it needs on its own. It takes a few minutes. Close
the window, open a fresh one, and check it worked:

```bash
hermes doctor
```

That prints a checklist of everything it needs. Green means fine.

**Want it running 24/7?** Your own computer is fine, but the agent stops when you
shut it down. Rent a small server for about $5/month from Hetzner or DigitalOcean,
choose Ubuntu when they ask, and run the Linux line on that server instead.

---

## 2. Give it a brain (about $5/month)

1. Subscribe at **https://opencode.ai/go?ref=0N4C2C5TNK**
2. Copy the key it shows you.
3. Put the key in the settings file.

Windows — open the file in Notepad and add your key on its own line at the bottom:

```powershell
notepad $env:USERPROFILE\.hermes\.env
```

```
OPENCODE_GO_API_KEY=YOUR_KEY_HERE
```

Mac and Linux:

```bash
hermes config env-path
printf 'OPENCODE_GO_API_KEY=%s\n' 'YOUR_KEY_HERE' >> ~/.hermes/.env
```

4. Tell the agent to use it and say hello:

```bash
hermes model
hermes chat -q "hello, what model are you?"
```

If it answers, you have a working agent. Watch your usage the first week: the
OpenCode dashboard shows a 5-hour window and a weekly one, and long autonomous jobs
use more than chatting.

---

## 3. Download the 31 skills

```bash
git clone https://github.com/andyemad/nft-mint-rarity-toolkit.git
cd nft-mint-rarity-toolkit
./install.sh
```

That copies all 31 skills into your agent. Check them any time with
`hermes skills list`. Running it again later is safe.

No git installed? Download the ZIP from
https://github.com/andyemad/nft-mint-rarity-toolkit/archive/refs/heads/main.zip,
unzip it, open a terminal inside the folder, and run `bash install.sh`.

Extra pieces needed by the wallet and trading skills:

```bash
pip install eth-account coincurve pycryptodome
```

---

## 4. Connect Discord

1. Go to https://discord.com/developers/applications and click **New Application**.
2. Click **Bot** in the left menu. Under **Privileged Gateway Intents** turn
   **Message Content Intent** ON. Without it the bot looks completely broken.
3. Still on the Bot page, click **Reset Token** and copy it. Treat it like a password.
4. Click **Installation**, enable **Guild Install**, and make sure the scopes include
   `bot` and `applications.commands`.
5. Open the install link it shows you and add the bot to your server.
6. Get your user ID: Discord → **Settings → Advanced** → turn on **Developer Mode**,
   then right-click your own name and choose **Copy User ID**.
7. Run the setup and paste in the token and the ID:

```bash
hermes gateway setup
```

Then start it and test:

```bash
hermes gateway run
```

Send the bot a direct message in Discord. It should answer. When you are happy,
press Ctrl + C and make it start on its own from now on:

```bash
hermes gateway install
hermes gateway start
```

In direct messages it replies to everything. In a server channel it only replies
when you @mention it, so it does not spam your friends.

If it never replies, it is almost always the Message Content Intent being off, or a
wrong user ID.

---

## 5. Free GPU minting (the $30 credit)

Some NFTs are not sold, they are solved. Instead of paying a price you search for a
lucky number, millions of times. That is a proof-of-work mint, and it is where
Hashcats, FAB4200 and similar drops come from.

Your laptop can do it, but it would take days. A rented graphics card does it in
minutes, and you do not have to buy one:

**Modal gives you $30 of free computing every month on their free plan.** That is
roughly **7 hours of their fastest graphics cards**, at around $4/hour. For
occasional mint attempts you will likely never pay.

1. Make a free account at https://modal.com. The $30 is included.
2. Install and connect:

```bash
pip install modal
modal setup
```

3. Check the fast part works, then do a practice run that spends nothing:

```bash
cd toolkit/pow/hashcats-farm
modal run hashcats_modal.py --mode probe
python3 farm.py --shards 2 --minutes 5 --dry
```

The practice run finds lucky numbers and checks them but never sends anything. Drop
`--dry` to do it for real, with a wallet holding a little ETH.

Be honest with yourself about this one. GPU minting is a race against everyone else
trying the same drop, and you pay for computing time even when you lose. Use the
free credits, keep attempts short, and do not top up expecting a guaranteed win.

---

## 6. What every skill does

You do not need to memorise these. The agent picks the right one automatically.
This list is so you know what to ask for.

### Minting

| Skill | What it does |
|---|---|
| `nft-mint-recon` | Works out what a mint really is: the real contract, the real price, whether it is actually open, and which network. The one that stops you getting scammed by a fake price. |
| `seadrop-rapid-mint` | Mints from many wallets at once for drops that sell out in seconds. Creates the wallets, tells you exactly how much to fund each one, and fires at the opening moment. |
| `pow-mint-mining` | Handles proof-of-work drops where you find a lucky number instead of paying. Setup, rented GPU, and the checking so you never waste a transaction. |
| `onchain-puzzle-mining` | The actual number crunching, on your machine or rented hardware, with a self-check so it never runs for hours on a broken calculation. |
| `onchain-puzzle-solving` | Solves the riddles and puzzles some drops use as a gate, by reading the game's own code. |
| `onchain-claim-reverse-engineering` | Works out how a claim, free mint or refund page really works before you connect a wallet. |
| `nft-floor-sweep` | Adds up every cheap listing in a collection and gives you the real total before you buy them all. |

### Rarity and sniping

| Skill | What it does |
|---|---|
| `nft-rarity-engine` | Ranks every NFT in a collection by rarity using the same maths OpenSea uses, so the ranks match. Can catch a reveal before OpenSea updates. |
| `rh-chain-rarity-sniping` | After a reveal, buys the rarest items that are listed at normal floor prices. |
| `nft-secondary-buy` | Buys a listed NFT from the resale market, always testing the purchase first so a broken order never costs a fee. |

### Is this thing real?

| Skill | What it does |
|---|---|
| `nft-minter-legitimacy-audit` | Tells you whether the wallets that minted were real people or a few wallets faking interest. |
| `web3-claim-verification` | Checks a project's claims against the blockchain. |
| `nft-market-analysis` | Floors, sales, holders, flip speed. What the numbers really say. |
| `nft-collection-price-analysis` | What a collection is worth, and what can go wrong after you buy. |
| `nft-exit-discipline` | Rules for taking profit instead of holding forever. |

### Wallets

| Skill | What it does |
|---|---|
| `ethereum-wallet-operations` | Creates wallets, backs up keys properly, moves tokens without exposing keys. |
| `wallet-radar-operations` | Watches wallets you care about and pings you when they buy. |
| `public-wallet-xlsx-delivery` | Turns a list of wallets into a clean shareable spreadsheet. |
| `pseudonym-identity-research` | Links anonymous accounts, handles and wallets belonging to the same person. |

### Making your own collection

| Skill | What it does |
|---|---|
| `nft-collection-production` | Everything for launching your own: art plan, traits, pricing, mint page, contract mechanics. |
| `nft-trait-taxonomy` | Keeps every trait consistent and grouped so your metadata does not become a mess. |
| `nft-trait-curation` | Audits each trait for duplicates and anything that looks off before launch. |

### Data, research and building

| Skill | What it does |
|---|---|
| `ethereum-data-pipelines` | Reads the blockchain without paying for an API. The engine under a lot of the others. |
| `rh-mint-command-center` | A full local mint control room: plan, rehearse, manage wallets, watch the floor, and audit what happened. |
| `mint-field-guide` | A read-only dashboard of upcoming mints and market movement, with the source noted for every number. |
| `onchain-game-economy-analysis` | Takes an on-chain game apart to show where value comes from. |
| `polymarket` | Reads prediction-market prices. |
| `proof-of-play-archive` | Background research on Proof of Play and Pirate Nation. |
| `agent-protocol-identity` | Gives an AI agent a verifiable identity when it posts online. |
| `flop-technocore-agent-ops` | How to run an agent with its own public account without leaking anything private. |
| `internet-computer-development` | Notes for building on the Internet Computer blockchain. |

---

## 7. What it costs

| Thing | Cost | Needed? |
|---|---|---|
| Hermes agent | Free | Yes |
| The 31 skills | Free | Yes |
| OpenCode subscription | ~$5/month | Yes, this is the brain |
| Your own computer | Free | Fine, but it stops when you shut down |
| Small server for 24/7 | ~$5/month | Optional |
| Modal for GPU minting | Free, $30/month included | Optional |
| Gas fees when you actually mint | Usually cents | Only when you mint, from your own wallet |

The honest answer is **about $5 a month**, maybe $10 if you want it awake all night.

---

## 8. If something goes wrong

| What you see | What to do |
|---|---|
| `hermes` is not recognised | Close the terminal and open a new one. Still failing? Restart and retry. |
| Bot online but never answers | Turn on Message Content Intent in the Discord developer page |
| Answers in DMs but not in a server | Normal. In servers it answers only when @mentioned |
| It says you are not allowed | Your Discord user ID is wrong. Copy it again with Developer Mode on |
| It stops when you close the laptop | Expected on your own computer. Get the $5 server for 24/7 |
| It asks for more money | Check your OpenCode usage page. Long jobs use more than chat |
| Skills do not show up | `hermes skills list` to confirm, then `/reload-skills` in a chat |
| You are lost | Run `hermes chat` and just say what you are trying to do |

---

Nothing here is financial advice. Minting and trading lose money for most people
who try it. Set a limit before you start and never mint with money you need.
