# Set up your own AI agent

Hermes, Discord, the skills, Vercel, and choosing between your computer and a
server. Copy and paste a few lines, then talk to the finished thing in Discord.

About **$10 a month**, most of it optional.

Same guide as the published page: https://andyemad.github.io/nft-mint-rarity-toolkit/

---

## 1. What you need

| You need | Cost | What it is for |
|---|---|---|
| A computer | Free | Runs the agent. Windows, Mac or Linux |
| A Discord account | Free | How you talk to the agent, from phone or desktop |
| An OpenCode subscription | ~$10/month | The agent's brain. The only thing you have to pay for |
| A Vercel account (optional) | Free | Only if you want a page or small site online |
| A small server (optional) | ~$5/month | Only if you want it running while your computer is off |
| A Nous Portal account (optional) | Pricing on the Portal | Nous can host the agent for you, so you never touch a server |

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

## 3. Set up Discord or Telegram

After this you never need the terminal again, you just message it. Pick whichever
app you already use; both work the same afterwards.

### Discord

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

### Telegram

Telegram is the quicker one. Hermes creates the bot for you.

1. Run the setup, pick **Telegram**, then choose **Automatic**:

```bash
hermes gateway setup
```

2. A QR code appears with a link under it. Point your phone's camera at it, or open
   the link. Telegram opens; tap **Create Bot**.
3. Back in the terminal it detects your Telegram account and asks whether to allow
   it. Say yes, and yes to the couple of questions after that.

Test it, then make it permanent:

```bash
hermes gateway run       # leave open, message your new bot in Telegram
hermes gateway install   # Ctrl+C first, then these two
hermes gateway start
```

Prefer to make the bot yourself? Message **@BotFather**, send `/newbot`, answer its
two questions (the username must end in `bot`), and copy the token it gives you.
Get your user ID from **@userinfobot**. Choose **Manual** in the setup and paste in
both.

In a private chat it answers everything. In a group it only answers when you
@mention it or reply to it.

If it replies with a pairing code instead of an answer, run
`hermes pairing approve telegram <code>` and message it again.

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
| `pow-mint-mining` | Hashcats, FAB4200 and others like them give you the item for finding a lucky number instead of paying. Runs that search for you. |
| `onchain-puzzle-mining` | The search itself, on your machine or rented hardware, with checking so nothing is wasted. |
| `onchain-puzzle-solving` | Solves the riddles some drops use as a gate, by reading the game's own code. |
| `onchain-game-economy-analysis` | Takes an on-chain game apart to show where value comes from. |
| `polymarket` | Reads prediction-market prices. |
| `proof-of-play-archive` | Background research on Proof of Play and Pirate Nation. |
| `agent-protocol-identity` | Lets an agent prove who it is when it posts online. |
| `flop-technocore-agent-ops` | Running an agent with its own public account without leaking anything private. |
| `internet-computer-development` | Notes for building on the Internet Computer blockchain. |

---

## 6. Mint Hashcats (and drops like it)

Some drops do not have a price. Instead of paying, you find a lucky number, and
whoever finds one first gets the cat. That is what "solved rather than bought"
means.

Your laptop can do it, but it would take days, and people with rented computers
find them in minutes. So you rent one for a few minutes.

### Rent a computer for a few minutes (free to start)

**Modal** rents computers by the second. You do not buy anything. Sign up and it
comes with **$30 of free computing every month**, roughly seven hours of their fast
machines at about $4/hour. For occasional attempts you will probably never pay.

1. Sign up free at https://modal.com. The $30 is included.
2. Then, once:

```bash
pip install modal
modal setup
```

The second command opens a browser and links your account. That is the whole setup.

### What to type in Discord

Mention your bot and paste this:

```
@yourbot use the pow-mint-mining skill on hashcats. show me the current round and get everything ready, but don't spend anything yet
```

When you want to go for it:

```
@yourbot go ahead and mine the current round. stop when you find one, or after 15 minutes
```

And to see the result:

```
@yourbot did we get one? show me the transaction
```

### What it handles for you

- Checks the whole setup first, so a run never starts out broken
- Does the searching on the rented computer, not yours
- Checks every answer before spending anything, so one that arrived too late never costs a fee
- Sends the transaction from your wallet and gives you the link

### The two things only you can do

- **Put a little ETH in your wallet.** Winning still costs a few cents in fees. Nothing can do that part for you.
- **Keep attempts short.** Rounds move on constantly and work for a finished round is wasted. Short and frequent beats one long run.

**Be honest about the odds.** You are racing everyone else trying the same drop, and
you pay for the computing whether you win or lose. That is what the free credit is
for. Use it, keep attempts short, and do not top up expecting a guaranteed cat.

### Other drops this works on

Same idea, same kind of prompt, just name the one you want:

```
@yourbot use the pow-mint-mining skill on FAB4200 and tell me what it would cost me
```

---

## 7. Things to ask it

There is no special wording. **Paste a link and say what you want.** An OpenSea
link, a tweet, a mint website, a wallet address, a contract address. If it cannot
tell what you mean, it asks you.

### Paste an OpenSea link

```
@yourbot rank this whole collection by rarity and show me the top 20
@yourbot which rare ones here are listed cheap right now?
@yourbot what is the floor on this and is it going up or down?
@yourbot are the wallets that minted this real people or bots?
@yourbot is this worth buying at the current floor?
@yourbot how many people are holding this, and how concentrated is it?
```

### Paste a tweet that says "mint this"

This is the useful one. Drop the tweet in and it works out what the mint is, what
it really costs, whether it is still open, and whether the project looks real,
before anything touches your wallet.

```
@yourbot <tweet link> mint this
@yourbot <tweet link> what is this mint and is it real?
@yourbot <tweet link> can I mint this for free?
@yourbot <tweet link> what would minting 3 of these actually cost me?
@yourbot <tweet link> is this the real contract or a copy?
@yourbot <tweet link> set an alert for when this goes live
```

It will not just fire off a transaction. It reads the tweet, finds the contract,
checks the price and the supply on-chain, shows you what it found, and waits for
you to say go.

### Paste a mint website, or just a contract address

```
@yourbot can I mint this for free? <link>
@yourbot what is the real price on this? the page says 0.05
@yourbot is this mint still open or already sold out?
@yourbot how many wallets have minted this so far?
@yourbot is this contract a copy of another collection?
@yourbot what does this contract actually do? <address>
```

### Paste a wallet address

```
@yourbot what has this wallet been buying? <address>
@yourbot is this wallet actually profitable, or just busy?
@yourbot watch this wallet and message me when it buys something
@yourbot which collections did this wallet get into early?
@yourbot does this wallet look like a bot or a person?
```

### Ask it to watch something for you

```
@yourbot watch this collection and message me the moment it reveals
@yourbot tell me when the floor drops below 0.01
@yourbot ping me if anything from this collection sells under 0.005
@yourbot check this every ten minutes and only message me if something changes
@yourbot remind me when this mint opens in an hour
```

### Ask it to buy or mint for you

Every one of these checks first and tells you the cost before it does anything.
Nothing goes through until you say go.

```
@yourbot mint 1 for me, show me the cost and wait for my go ahead
@yourbot buy the cheapest rare one under 0.01
@yourbot buy 3 but never spend more than 0.03 in total
@yourbot don't spend anything without asking me first
@yourbot what is my wallet holding right now? <address>
```

### Ask it to explain something

```
@yourbot explain what a proof of work mint is, in simple terms
@yourbot why is this floor so low?
@yourbot what does "revealed" mean here?
@yourbot how do people fake volume on a collection?
@yourbot what is the difference between a mint and a buy?
```

**The general rule:** if you can paste it, it can probably look at it. Links,
screenshots, addresses, tweets, spreadsheets. If you are not sure how to ask, just
describe what you are trying to do and let it work the rest out.

---

## 8. Set up Vercel

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

## 9. Your computer, a server, or hosted?

All three work. The difference is what happens when you close your laptop, and how
much of it you have to look after yourself.

| | Your own computer | A small server | Nous hosts it (Hermes Cloud) |
|---|---|---|---|
| Cost | Free | ~$5/month | Listed on the Portal |
| Stays on when you shut the lid | No | Yes | Yes |
| Scheduled jobs and overnight alerts | Miss their window | Fire on time | Fire on time |
| Reach it from your phone | Only while it is on | Always | Always |
| Who keeps it updated | You | You | Nous |
| Setup | Already done | Same three commands on the server | Create it from the Portal's Agents page |

### Or let Nous host it for you

If running a server sounds like work you do not want, **Nous Research hosts Hermes
Cloud instances**. You get an agent that is always on, without picking a provider,
securing a box, or keeping it updated.

1. Make a **Nous Portal** account at https://portal.nousresearch.com
2. Open the **Agents** page and create an instance. Give it a name.
3. Connect Discord to it exactly as in step 3. Same commands, run on the instance.

From then on you manage it from that web page: start, stop, restart, delete.
Pricing is listed on the Portal alongside the plans.

**One subscription can cover both jobs.** A Portal plan can also be the agent's
brain instead of a separate model subscription. It includes a large catalogue of
models plus managed web search, image generation and voice, all through one login.
`hermes setup --portal` wires it up. If you are already paying for OpenCode, you do
not need both.

**Already running an agent locally?** You can manage cloud instances by asking it
instead of clicking around a website:

```bash
hermes mcp add --url https://portal.nousresearch.com/mcp --auth oauth hermes-cloud
```

Then you can say "list my cloud agents", "what is that instance costing me", or
"restart the stopped one".

**Moving to a server:** get one from Hetzner or DigitalOcean, pick **Ubuntu**, take
the smallest option, and run the same Linux install line from step 2 on it. Then
repeat the Discord and skills steps. Your computer and the server are separate
agents, and each gets its own Discord bot token.

Sensible order: start on your own computer today, rent a server once you have
something you want running while you sleep.

---

## 10. What it costs

| Thing | Cost | Needed? |
|---|---|---|
| Hermes agent | Free | Yes |
| The 31 skills | Free | Yes |
| OpenCode subscription | ~$10/month | Yes, this is the brain |
| Vercel | Free | Only if you want a page online |
| Your own computer | Free | Fine, but it sleeps |
| Small server | ~$5/month | Only for running around the clock |
| Modal, for solving drops like Hashcats (optional) | Free, $30/month included | Only if you want to go after those drops |
| Nous Portal, hosting included (optional) | Listed on the Portal | Instead of your own server, and it can be the brain too |

Honest total: about **$10 a month**, or $15 if you also want it awake all night.

---

## 11. Vibe coding: make the skills better

Not all 31 skills are polished. That is on purpose, because **you can fix and extend
them by talking**, with no code. Full page:
https://andyemad.github.io/nft-mint-rarity-toolkit/prompts/

A skill is just written-down instructions your agent follows, so improving one is a
conversation. You say what is wrong or what you want added, it makes the change,
tests it, and shows you.

### The loop

1. **Say what you want** in plain English, in Discord.
2. **Let it work**, then ask it to explain what it changed in one line.
3. **Make it prove it** — "test it and show me the output". This is the step people
   skip and the one that matters.
4. **Repeat until right.** Two or three rounds is normal.

### Prompts to start with

```
@yourbot read through all the skills I installed and tell me which ones look unfinished, unclear or missing steps

@yourbot pick the weakest one and tell me exactly what is missing from it

@yourbot the rarity skill doesn't handle collections that are still hidden. add that and show me it working

@yourbot test that properly and paste the actual output

@yourbot save what you just worked out as a skill so you can do it again without me explaining
```

### When one breaks

```
@yourbot that didn't work. here's what it said: <paste the whole error>
@yourbot find out why that keeps failing instead of just trying again
@yourbot go back to how it was before, that change made it worse
@yourbot you said it works but it didn't. show me the proof before you say that again
```

Paste the whole error, not a summary. The ugly wall of text is what it needs.

### Teach it something new

```
@yourbot watch how I check a mint before buying, then write a skill so you can do it for me next time
@yourbot make a skill for finding collections where the floor just dropped
@yourbot make a skill that checks all my wallets and tells me anything I should look at
```

If you have explained the same thing twice, that is a skill. You never explain it a
third time.

### Build a whole small thing

```
@yourbot build me a page showing every collection I hold, with images and rarity rank
@yourbot put this on Vercel and give me the link when it's actually live
```

Ask for the live link, not "done", and open it yourself.

### Phrases worth memorising

| Say this | And you get |
|---|---|
| "show me your plan before you start" | You can redirect it before it does anything |
| "test it and show me the output" | A real fix instead of a confident sentence |
| "explain what you changed, in one line" | Control without reading code |
| "don't spend anything / don't change anything yet" | Thinking without consequences |
| "make it simpler" | Something you can actually follow |
| "go back to how it was" | An undo |
| "save that as a skill" | It becomes permanent |

### Staying out of trouble

- **Never paste a private key** into a chat. If you have, treat that wallet as burnt and move anything in it.
- **Ask for the plan before big changes.** Ten seconds, saves a mess.
- **One change at a time**, or you cannot tell which one broke it.
- **Keep your money behind a "no"**: "don't spend anything without asking me".
- **Back up first**: "copy my skills folder somewhere safe".
- **If it claims success and you cannot see it, it is not real.** Ask for the proof.

---

## 12. If something goes wrong

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
