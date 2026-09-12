# Run Hermes on a VPS, connect it to Discord, and host this toolkit

Everything you need to go from a blank server to an agent that answers you in
Discord with these skills installed.

Two decisions shape the whole setup:

- **The agent needs a machine that stays on.** Hermes is a long-running process
  with a live gateway, a scheduler, and a shell. That is a VPS.
- **Vercel cannot host the agent.** It is serverless, nothing stays resident, and
  there is no shell. Vercel hosts the download page.

Skills are files. Installing this toolkit copies `skills/**` into your Hermes
skills directory, and `install.sh` does that.

```
 ┌──────────────┐        ┌────────────────────────┐        ┌──────────────┐
 │  Discord     │◄──────►│  VPS: hermes gateway   │        │  Vercel      │
 │  (you, DMs)  │        │  + skills + cron       │        │  download    │
 └──────────────┘        └────────────────────────┘        └──────────────┘
                            permanent process               static page
```

## What you need

| Thing | Notes |
|---|---|
| VPS | Ubuntu 22.04 or 24.04, 2 vCPU, 4 GB RAM, 40 GB disk. 2 GB is enough for a gateway-only agent. You want 4 GB the moment you use browser automation or a local Whisper model. |
| Domain | Optional. Only if you want webhook routes reachable from outside. |
| LLM API key | Any supported provider. [OpenCode](https://opencode.ai/go?ref=0N4C2C5TNK) is a cheap way in. See the provider section below. |
| Discord account | You need Manage Server on the server the bot will join. |
| GitHub account | Only if you fork the toolkit. |

## 1. Provision and harden the VPS

```bash
# Create the box (Hetzner CX22, DigitalOcean 2vCPU-4GB, or similar).
# Add your SSH public key at creation time. Do not use password auth.

# First login
ssh root@YOUR_SERVER_IP

# Create a non-root user with sudo
adduser hermes
usermod -aG sudo hermes

# Copy your SSH key over so you can log in as that user
rsync --archive --chown=hermes:hermes ~/.ssh /home/hermes/

# Firewall: SSH only
ufw allow OpenSSH
ufw enable

# Let services survive logout. Skipping this is the usual reason a bot
# goes offline the moment you close your SSH session.
loginctl enable-linger hermes

# Log in as the agent user from here on
su - hermes
```

Then update and add the basics:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl tmux build-essential python3-venv
```

On a 2 GB box, add swap so a heavy build cannot OOM-kill the gateway:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. Install Hermes Agent

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

The installer handles Python, Node, ripgrep, ffmpeg, the repo clone, the virtual
environment, and the `hermes` command. Then:

```bash
source ~/.bashrc       # so the hermes command is on your PATH
hermes --version       # confirm the install
hermes doctor          # check dependencies and config, fix what it flags
```

Layout: code in `~/.hermes/hermes-agent/`, binary via `~/.local/bin/hermes`,
data in `~/.hermes/` (`config.yaml`, `.env`, `skills/`, `sessions/`, `logs/`).

## 3. Pick a model provider

```bash
hermes setup          # wizard for model, terminal, gateway, tools
hermes model          # change model or provider later
```

An OpenCode plan is a cheap way to run an always-on agent:

1. Sign up at **https://opencode.ai/go?ref=0N4C2C5TNK**
2. Copy the API key from the dashboard.
3. Put it in the environment file. Secrets go in `.env`, never in `config.yaml`:

```bash
hermes config env-path     # prints the file, usually ~/.hermes/.env
printf 'OPENCODE_GO_API_KEY=%s\n' 'YOUR_KEY_HERE' >> ~/.hermes/.env
chmod 600 ~/.hermes/.env
```

4. Select it and confirm it answers:

```bash
hermes model
hermes chat -q "say hi and tell me which model you are"
```

Other providers work the same way. Set `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`,
or `DEEPSEEK_API_KEY` in `.env`, or use OAuth with
`hermes auth add <provider> --type oauth`. Check auth with `hermes status --all`.

The gateway bills for every message it processes, so pick a sensible default
model rather than your most expensive one, and leave reasoning effort low unless a
task needs more.

## 4. Install the toolkit skills

```bash
# From a clone (recommended, you also get toolkit/ code)
git clone https://github.com/andyemad/nft-mint-rarity-toolkit.git
cd nft-mint-rarity-toolkit
./install.sh                      # into ~/.hermes/skills/
./install.sh --profile work       # into ~/.hermes/profiles/work/skills/
./install.sh --dry-run            # preview, write nothing

# Or one line, no clone
curl -fsSL https://raw.githubusercontent.com/andyemad/nft-mint-rarity-toolkit/main/install.sh | bash
```

The installer moves a same-named skill to `<name>.bak-<timestamp>` instead of
overwriting it, and running it twice does nothing the second time. To confirm:

```bash
hermes skills list | head -40
hermes chat -s nft-rarity-engine -q "summarise what this skill lets you do"
```

Extra dependencies for the signing and trading paths:

```bash
pip install eth-account coincurve pycryptodome
```

Keys stay out of the tree. They go in `~/.hermes/secrets/` at `chmod 600`, as
described in `SECURITY.md`.

## 5. Create the Discord bot

1. Go to **https://discord.com/developers/applications**, click **New
   Application**, name it, and create it.
2. On the **Bot** tab:
   - **Public Bot**: ON if you want to use the Installation tab for the invite.
     OFF is fine if you build the invite URL by hand.
   - **Privileged Gateway Intents**: enable **Message Content Intent**. Without
     it the bot receives no message text and looks completely broken.
   - **Reset Token**, then copy the token. Discord shows it once. Anyone with it
     controls the bot, so store it somewhere safe.
3. On the **Installation** tab (or build the URL yourself):
   - Installation Contexts: enable **Guild Install**
   - Install Link: **Discord Provided Link**
   - Scopes: **bot** and **applications.commands**
   - Permissions: View Channels, Send Messages, Embed Links, Attach Files, Read
     Message History. Add Send Messages in Threads and Add Reactions if you want
     the bot to work in threads and react for acknowledgements.

   Manual URL:

   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot+applications.commands&permissions=274878286912
   ```

   | Level | Permission integer |
   |---|---|
   | Minimal | `117760` |
   | Recommended (used above) | `274878286912` |

4. Open the invite URL, pick your server, and authorize. You need Manage Server
   on that server. The bot shows as offline until the gateway starts.
5. Get your user ID: in Discord, go to **Settings → Advanced**, turn **Developer
   Mode** on, then right-click your name and choose **Copy User ID**. It is a long
   number. You can copy channel and server IDs the same way.
6. Configure Hermes:

```bash
hermes gateway setup      # choose Discord, paste the bot token and your user ID
```

   Or edit `~/.hermes/.env` directly:

```bash
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_ALLOWED_USERS=284102345871466496        # comma-separate for more than one
DISCORD_HOME_CHANNEL=123456789012345678         # optional: where cron and reminders land
```

   Without `DISCORD_ALLOWED_USERS` or `DISCORD_ALLOWED_ROLES`, the gateway denies
   everyone. This is the second most common "it isn't responding".

7. Run it in the foreground once, before you set up the service:

```bash
hermes gateway run        # Ctrl-C to stop
```

   DM the bot, or mention it in a channel it can see.

### How it behaves in a server

| Context | Behaviour |
|---|---|
| DMs | Always answers, no mention needed, one session per DM |
| Server channels | Answers only when mentioned, unless the channel is listed in `DISCORD_FREE_RESPONSE_CHANNELS` |
| Threads | Replies in the thread with its own session namespace, separate from the parent channel |
| Multiple users | History is per-user per-channel by default (`group_sessions_per_user`) |

Other toggles, all in `.env`: `DISCORD_REQUIRE_MENTION=false`,
`DISCORD_FREE_RESPONSE_CHANNELS=<ids>`, `DISCORD_AUTO_THREAD`,
`DISCORD_IGNORE_NO_MENTION`.

## 6. Run the gateway as a service

```bash
hermes gateway install
hermes gateway start
hermes gateway status
```

Day to day:

```bash
hermes gateway restart
journalctl --user -u hermes-gateway -f
grep -i "failed to send\|error" ~/.hermes/logs/gateway.log | tail -20
```

If the bot goes offline when you close SSH, linger from step 1 is missing or the
service definition is stale. Re-run `hermes gateway install`.

Do not restart the gateway casually while it is mid-task. An in-flight session
dies with it and cron jobs miss their tick. Use `/restart` from chat, which drains
first.

## 7. Host the download page on Vercel

The gateway cannot run on Vercel. The download page can, which is what you want: a
public URL where someone reads what the toolkit does and grabs the ZIP or the
one-line installer.

```bash
mkdir -p ~/toolkit-site && cd ~/toolkit-site
# copy site/index.html out of this repo, then:
npx vercel@latest deploy --prod
```

Or connect the repo in the Vercel dashboard and set the Root Directory to `site/`.
Every push then redeploys the page.

Vercel's Hobby plan soft-blocks a project that exceeds its included transfer
allowance. When that happens every deploy returns HTTP 402 while the dashboard
still looks healthy. Test with a throwaway deploy before you rely on it. If you
are blocked, Cloudflare Pages serves the same static files:

```bash
npx wrangler@latest pages deploy site --project-name=nft-mint-rarity-toolkit
```

The downloads are the same either way:

| Artifact | URL |
|---|---|
| Source ZIP | `https://github.com/andyemad/nft-mint-rarity-toolkit/archive/refs/heads/main.zip` |
| One-line installer | `curl -fsSL https://raw.githubusercontent.com/andyemad/nft-mint-rarity-toolkit/main/install.sh \| bash` |
| Skills only | the `skills/` directory |

## 8. Verify the whole chain

Work down this list. Each step isolates one layer, so a failure tells you where to
look rather than just "the bot is broken".

```bash
hermes --version                       # 1. binary on PATH
hermes doctor                          # 2. dependencies and config
hermes chat -q "reply with OK"         # 3. provider and key
hermes skills list | grep rarity       # 4. toolkit skills present
hermes gateway status                  # 5. service running
tail -20 ~/.hermes/logs/gateway.log    # 6. gateway connected to Discord
```

Then DM the bot, and mention it in a channel.

| Symptom | Cause |
|---|---|
| Online but silent in channels | Not mentioned. Mention it, or add the channel to `DISCORD_FREE_RESPONSE_CHANNELS` |
| Appears dead everywhere | Message Content Intent is not enabled in the Developer Portal |
| Gateway up, everyone denied | `DISCORD_ALLOWED_USERS` is missing or wrong |
| Died after closing SSH | `sudo loginctl enable-linger $USER`, then reinstall the service |
| "No models provided" or 401 | Wrong or missing provider key in `~/.hermes/.env`, re-run `hermes model` |
| Skills not loading | `hermes skills list` to confirm, then `/reload-skills` in a running session |
| Dies during long tasks | 2 GB RAM ran out. Add swap or resize to 4 GB |

## 9. Security for a public-facing agent

Hermes runs real shell commands, so treat the box accordingly.

- Keep the VPS firewalled to SSH. Do not enable the API Server adapter or webhook
  routes until you need them and understand the auth model.
- Use `DISCORD_ALLOWED_USERS`, not `DISCORD_ALLOW_ALL_USERS`. In a public server,
  allow-all means strangers can drive a shell on your machine.
- Leave `approvals.mode` at `manual` or `smart` so destructive commands need a
  human yes.
- Keys live in `~/.hermes/secrets/` at `chmod 600`. Never in a repo, never pasted
  into a chat.
- Back up `~/.hermes/` off the box. `hermes profile export` produces a tar.gz you
  can move somewhere else.
- Update deliberately with `hermes update`, then re-check `hermes doctor`.

## OpenCode

Sign up with my referral link: **https://opencode.ai/go?ref=0N4C2C5TNK**

Use it as the Hermes provider from step 3, or as a standalone coding agent. The
key goes in `~/.hermes/.env` as `OPENCODE_GO_API_KEY`, then select it with
`hermes model`.
