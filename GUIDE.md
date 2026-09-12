# Set up your own AI agent

Hermes, Discord, the skills, Vercel, and choosing between your computer and a
server. Copy and paste a few lines, then talk to the finished thing in Discord.

About **$5 a month**, most of it optional.

Same guide as the published page: https://andyemad.github.io/nft-mint-rarity-toolkit/

---

## 1. What you need

| You need | Cost | What it is for |
|---|---|---|
| A computer | Free | Runs the agent. Windows, Mac or Linux |
| A Discord account | Free | How you talk to the agent, from phone or desktop |
| An OpenCode subscription | ~$5/month | The agent's brain. The only thing you have to pay for |
| A Vercel account (optional) | Free | Only if you want a page or small site online |
| A small server (optional) | ~$5/month | Only if you want it running while your computer is off |

Start with the first three. The last two come later and you can skip either.

---

## 2. Set up Hermes

You paste one line into a terminal. It installs itself.

**Windows** — open the Start menu, type `PowerShell`, open it, paste:

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

**Mac** — Command + Space, type `Terminal`, press Enter, paste:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

**Linux** — same as Mac:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

It downloads what it needs and takes a few minutes. Let the text scroll.

Close the window, open a new one, and check it worked:

```bash
hermes doctor
```

That prints a checklist. Green is fine. If something is missing it tells you the
exact command to fix it.

### Give it a brain

Subscribe at **https://opencode.ai/go?ref=0N4C2C5TNK**, then add the key you get.

Windows — open the settings file in Notepad:

```powershell
notepad $env:USERPROFILE\.hermes\.env
```

Add this line at the bottom, then save and close:

```
OPENCODE_GO_API_KEY=YOUR_KEY_HERE
```

Mac and Linux:

```bash
printf 'OPENCODE_GO_API_KEY=%s\n' 'YOUR_KEY_HERE' >> ~/.hermes/.env
```

Then:

```bash
hermes model
hermes chat -q "hello, what model are you?"
```

If it answers, the agent works.

---

## 3. Set up Discord

After this you never need the terminal again, you just message it.

1. Go to https://discord.com/developers/applications and click **New Application**.
2. Left menu → **Bot**. Under **Privileged Gateway Intents** turn **Message Content
   Intent** ON. Skip this and your bot looks totally broken.
3. On that same page click **Reset Token** and copy it. Shown once. Treat it like a
   password.
4. Left menu → **Installation**. Enable **Guild Install**, make sure the scopes
   include `bot` and `applications.commands`, and copy the install link.
5. Open that link and add the bot to your server. You need to manage that server.
6. Get your user ID: Discord → **Settings → Advanced** → Developer Mode ON, then
   right-click your own name → **Copy User ID**.
7. Run the setup and paste in the token and the ID:

```bash
hermes gateway setup
```

Test it, then make it permanent:

```bash
hermes gateway run       # leave open, DM the bot in Discord
hermes gateway install   # Ctrl+C first, then these two
hermes gateway start
```

In direct messages it answers everything. In a server channel it only answers when
you @mention it.

If it never replies, it is almost always the Message Content Intent being off, or a
wrong user ID.

---

## 4. Download the skills

```bash
git clone https://github.com/andyemad/nft-mint-rarity-toolkit.git
cd nft-mint-rarity-toolkit
./install.sh
```

Check them any time with `hermes skills list`. Re-running the installer is safe.

No git? Download the ZIP from
https://github.com/andyemad/nft-mint-rarity-toolkit/archive/refs/heads/main.zip,
unzip it, open a terminal in that folder, run `bash install.sh`.

Three helpers the wallet and trading skills need:

```bash
pip install eth-account coincurve pycryptodome
```

---

## 5. What each skill does

You do not need to memorise these. The agent picks the right one. This is so you
know what to ask for.

### Minting

| Skill | What it does |
|---|---|
| `nft-mint-recon` | Finds the real contract, the real price, whether the mint is open, and which network. Stops you getting scammed by a fake price. |
| `seadrop-rapid-mint` | Mints from many wallets at once for drops that sell out in seconds. Creates the wallets and tells you how much to fund each. |
| `nft-floor-sweep` | Adds up every cheap listing in a collection and gives you the real total before you buy them all. |
| `onchain-claim-reverse-engineering` | Works out how a claim, free mint or refund page really works before you connect a wallet. |

### Rarity and buying

| Skill | What it does |
|---|---|
| `nft-rarity-engine` | Ranks every NFT by rarity using the same maths OpenSea uses, so the ranks match. Can catch a reveal before OpenSea updates. |
| `rh-chain-rarity-sniping` | After a reveal, buys the rarest items listed at normal floor prices. |
| `nft-secondary-buy` | Buys a listed NFT from the resale market, testing the purchase first so a broken order never costs a fee. |

### Is this thing real?

| Skill | What it does |
|---|---|
| `nft-minter-legitimacy-audit` | Tells you whether the minters were real people or a few wallets faking interest. |
| `web3-claim-verification` | Checks a project's claims against the blockchain. |
| `nft-market-analysis` | Floors, sales, holders, flip speed. What the numbers really say. |
| `nft-collection-price-analysis` | What a collection is worth and what can go wrong after you buy. |
| `nft-exit-discipline` | Rules for taking profit instead of holding forever. |

### Wallets

| Skill | What it does |
|---|---|
| `ethereum-wallet-operations` | Creates wallets, backs up keys properly, moves tokens without exposing them. |
| `wallet-radar-operations` | Watches wallets you care about and pings you when they buy. |
| `public-wallet-xlsx-delivery` | Turns a list of wallets into a clean shareable spreadsheet. |
| `pseudonym-identity-research` | Links anonymous handles and wallets belonging to the same person. |

### Making your own collection

| Skill | What it does |
|---|---|
| `nft-collection-production` | Art plan, traits, pricing, mint page, contract mechanics, all in one place. |
| `nft-trait-taxonomy` | Keeps every attribute consistent and grouped so metadata does not become a mess. |
| `nft-trait-curation` | Audits each trait for duplicates and anything that looks wrong before launch. |

### Tools and research

| Skill | What it does |
|---|---|
| `ethereum-data-pipelines` | Reads the blockchain without paying for an API. The engine under a lot of the others. |
| `rh-mint-command-center` | A local mint control room: plan, rehearse, manage wallets, watch the floor, audit results. |
| `mint-field-guide` | A read-only dashboard of upcoming mints and market movement. |
| `pow-mint-mining` | Handles drops where you find a lucky number instead of paying. Runs that search for you. |
| `onchain-puzzle-mining` | The search itself, on your machine or rented hardware, with checking so nothing is wasted. |
| `onchain-puzzle-solving` | Solves the riddles some drops use as a gate, by reading the game's own code. |
| `onchain-game-economy-analysis` | Takes an on-chain game apart to show where value comes from. |
| `polymarket` | Reads prediction-market prices. |
| `proof-of-play-archive` | Background research on Proof of Play and Pirate Nation. |
| `agent-protocol-identity` | Lets an agent prove who it is when it posts online. |
| `flop-technocore-agent-ops` | Running an agent with its own public account without leaking anything private. |
| `internet-computer-development` | Notes for building on the Internet Computer blockchain. |

---

## 6. Set up Vercel

Vercel puts a page or a website online for free. You do not need it to run the
agent. You need it if you want a public link of your own.

Sign up at https://vercel.com/signup. The free plan covers everything here.

### The easy way

1. Vercel → **Add New → Project**
2. Connect GitHub and pick the repository
3. If your web files live in a folder, set **Root Directory** to it (for this
   guide's page that folder is `docs`)
4. **Deploy**

Every push to GitHub after that rebuilds the site automatically.

### The terminal way

```bash
npm install -g vercel
vercel login
vercel --prod          # from inside the folder you want online
```

### Try it with this guide's page

```bash
git clone https://github.com/andyemad/nft-mint-rarity-toolkit.git
cd nft-mint-rarity-toolkit
npx vercel deploy docs --prod
```

### Your own domain

Optional. Project **Settings → Domains**, add a domain you own, or keep the free
`your-project.vercel.app` address.

**What Vercel cannot do:** run your agent. It only serves websites loaded on demand.
The agent is a program that has to stay switched on. If a deploy fails with a
**402** error, that account went past the free plan's transfer allowance. Make a new
project, or use GitHub Pages or Cloudflare Pages, which serve the same files.

---

## 7. Your computer or a server?

Both work. The difference is what happens when you close your laptop.

| | On your own computer | On a small server |
|---|---|---|
| Cost | Free | ~$5/month |
| Stays on when you shut the lid | No | Yes |
| Scheduled jobs and overnight alerts | Miss their window | Fire on time |
| Reach it from your phone | Only while the computer is on | Always |
| Setup | Already done | Same three commands on the server |

**Moving to a server:** get one from Hetzner or DigitalOcean, pick **Ubuntu**, take
the smallest option, and run the same Linux install line from step 2 on it. Then
repeat the Discord and skills steps. Your computer and the server are separate
agents, and each gets its own Discord bot token.

Sensible order: start on your own computer today, rent a server once you have
something you want running while you sleep.

---

## 8. What it costs

| Thing | Cost | Needed? |
|---|---|---|
| Hermes agent | Free | Yes |
| The 31 skills | Free | Yes |
| OpenCode subscription | ~$5/month | Yes, this is the brain |
| Vercel | Free | Only if you want a page online |
| Your own computer | Free | Fine, but it sleeps |
| Small server | ~$5/month | Only for running around the clock |

Honest total: about **$5 a month**, or $10 if you also want it awake all night.

---

## 9. If something goes wrong

| What you see | What to do |
|---|---|
| `hermes` is not recognised | Close the terminal and open a new one. Still failing? Restart and retry. |
| Bot online but never answers | Message Content Intent is off. The number one cause. |
| Answers in DMs, silent in a server | Normal. In servers it only answers when @mentioned |
| It says you are not allowed | Your Discord user ID is wrong. Copy it again with Developer Mode on |
| Vercel deploy fails with 402 | Past the free transfer allowance. New project, or GitHub Pages / Cloudflare Pages |
| The agent stopped overnight | It was on your computer. Move it to a server if you need it always on |
| It asks for more money | Check your OpenCode usage page. Long jobs use more than chatting |
| Skills do not show up | `hermes skills list` to confirm, then `/reload-skills` in a chat |
| You are lost | Run `hermes chat` and describe what you are trying to do |

---

Nothing here is financial advice. Minting and trading lose money for most people
who try it. Set a limit before you start and never use money you need.
