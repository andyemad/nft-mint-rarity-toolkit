# Run Hermes on a VPS, connect it to Discord, and host this toolkit for download

A complete, copy-paste path from a blank VPS to an agent that answers you in
Discord with these skills installed.

Two things to understand up front, because they decide the architecture:

- **The agent must run on a machine that stays on.** Hermes is a long-lived
  process with a live gateway, a scheduler, and a terminal. A VPS is the right
  home for it. **Vercel cannot host the agent** — it is serverless, nothing stays
  resident, and there is no shell. Vercel hosts the *download page*.
- **Skills are plain files.** Installing this toolkit means copying
  `skills/**` into your Hermes skills directory. `install.sh` does exactly that.

```
 ┌──────────────┐        ┌────────────────────────┐        ┌──────────────┐
 │  Discord     │◄──────►│  VPS: hermes gateway   │        │  Vercel      │
 │  (you, DMs)  │        │  + skills + cron       │        │  download    │
 └──────────────┘        └────────────────────────┘        └──────────────┘
                            permanent process               static page
```

---

## Part 0 — What you need

| Thing | Notes |
|---|---|
| VPS | Ubuntu 22.04/24.04, 2 vCPU, **4 GB RAM**, 40 GB disk. 2 GB runs a gateway-only agent; 4 GB is needed the moment you use browser automation or a local Whisper model. |
| Domain | Optional. Only needed if you want the webhook routes publicly reachable. |
| LLM API key | Any supported provider. [OpenCode](https://opencode.ai/go?ref=0N4C2C5TNK) is a cheap way in (see Part 3). |
| Discord account | You need **Manage Server** on the server you want the bot in. |
| GitHub account | Only if you fork the toolkit to your own account. |

---

## Part 1 — Provision and harden the VPS

```bash
# 1. Create the box (Hetzner CX22 / DigitalOcean 2vCPU-4GB / any equivalent).
#    Add your SSH public key at creation time — do not use password auth.

# 2. First login
ssh root@YOUR_SERVER_IP

# 3. Create a non-root user with sudo
adduser hermes
usermod -aG sudo hermes

# 4. Copy your SSH key over so you can log in as that user
rsync --archive --chown=hermes:hermes ~/.ssh /home/hermes/

# 5. Firewall: SSH only, everything else closed
ufw allow OpenSSH
ufw enable

# 6. Make services survive logout (this is the #1 cause of "my bot died")
loginctl enable-linger hermes

# 7. Log in as the agent user from here on
su - hermes
```

Housekeeping that saves pain later:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl tmux build-essential python3-venv
# 2 GB box only: add swap so a heavy build does not OOM-kill the gateway
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile \
  && sudo mkswap /swapfile && sudo swapon /swapfile \
  && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## Part 2 — Install Hermes Agent

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

This installs Python, Node, ripgrep, ffmpeg, clones the repo, builds the venv and
puts `hermes` on your PATH. Then:

```bash
# reload your shell so the hermes command is found
source ~/.bashrc

hermes --version      # confirms the install
hermes doctor         # checks dependencies and config — fix anything it flags
```

Install layout: code in `~/.hermes/hermes-agent/`, binary via
`~/.local/bin/hermes`, data in `~/.hermes/` (`config.yaml`, `.env`, `skills/`,
`sessions/`, `logs/`).

---

## Part 3 — Pick a model provider

```bash
hermes setup          # guided wizard: model, terminal, gateway, tools
# or, to just change the model/provider later:
hermes model
```

For a cheap always-on agent, an OpenCode plan works well:

1. Sign up at **https://opencode.ai/go?ref=0N4C2C5TNK**
2. Copy the API key from the dashboard.
3. Put it in the environment file (**secrets live in `.env`, never in
   `config.yaml`**):

```bash
hermes config env-path                    # prints the file to edit, usually ~/.hermes/.env
printf 'OPENCODE_GO_API_KEY=%s\n' 'YOUR_KEY_HERE' >> ~/.hermes/.env
chmod 600 ~/.hermes/.env
```

4. Select the provider and model:

```bash
hermes model            # choose OpenCode Go, then a model
hermes chat -q "say hi and tell me which model you are"
```

Any other provider works identically — `OPENROUTER_API_KEY`,
`ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, or OAuth via `hermes auth add <provider>
--type oauth`. Verify auth with `hermes status --all`.

**Cost control on a VPS:** the gateway bills for every message it processes. Set a
sensible default model rather than your most expensive one, and leave reasoning
effort low unless a task needs more.

---

## Part 4 — Install this toolkit's skills

```bash
# Option A — from a clone (recommended: you get toolkit/ code too)
git clone https://github.com/andyemad/nft-mint-rarity-toolkit.git
cd nft-mint-rarity-toolkit
./install.sh                      # -> ~/.hermes/skills/
./install.sh --profile work       # -> ~/.hermes/profiles/work/skills/
./install.sh --dry-run            # preview, write nothing

# Option B — one-liner, no clone
curl -fsSL https://raw.githubusercontent.com/andyemad/nft-mint-rarity-toolkit/main/install.sh | bash
```

The installer backs up any same-named skill to `<name>.bak-<timestamp>` instead
of overwriting it, and re-running it is a no-op. Verify:

```bash
hermes skills list | head -40
hermes chat -s nft-rarity-engine -q "summarise what this skill lets you do"
```

Optional extra dependencies for the signing and trading paths:

```bash
pip install eth-account coincurve pycryptodome
```

**Secrets stay out of the tree, always.** Keys go in `~/.hermes/secrets/` with
`chmod 600` — see `SECURITY.md`. Never commit a key file.

---

## Part 5 — Create the Discord bot

1. Go to **https://discord.com/developers/applications** → **New Application** →
   name it → **Create**.
2. **Bot** tab:
   - **Public Bot**: ON if you want to use the Installation tab to generate the
     invite; OFF is fine if you build the invite URL manually.
   - **Privileged Gateway Intents** → enable **Message Content Intent**.
     *Without this the bot sees no message text and appears completely dead.*
   - **Reset Token** → copy the token. It is shown **once**. Treat it as a
     password: anyone with it controls the bot.
3. **Installation** tab (or build the URL manually):
   - Installation Contexts → enable **Guild Install**
   - Install Link → **Discord Provided Link**
   - Scopes: **bot** and **applications.commands**
   - Permissions: **View Channels, Send Messages, Embed Links, Attach Files,
     Read Message History** (+ *Send Messages in Threads*, *Add Reactions*)

   Manual URL form, if you prefer:

   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot+applications.commands&permissions=274878286912
   ```

   | Level | Permission integer |
   |---|---|
   | Minimal | `117760` |
   | Recommended (used above) | `274878286912` |

4. Open the invite URL, pick your server, **Authorize** (needs **Manage Server**).
   The bot shows as offline until the gateway starts.
5. Get your **user ID**: Discord → **Settings → Advanced → Developer Mode ON**,
   then right-click your name → **Copy User ID** (a long number). Do the same for
   a channel if you want to set a home channel.
6. Configure Hermes:

```bash
hermes gateway setup      # select Discord, paste the bot token + your user ID
```

   Or manually, in `~/.hermes/.env`:

```bash
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_ALLOWED_USERS=284102345871466496        # comma-separate for more
DISCORD_HOME_CHANNEL=123456789012345678         # optional: where cron/reminders land
```

   Without `DISCORD_ALLOWED_USERS` (or `DISCORD_ALLOWED_ROLES`), the gateway
   **denies everyone** — this is the second most common "it's not responding".
7. Test it live before you daemonize:

```bash
hermes gateway run        # foreground; Ctrl-C to stop
```

   DM the bot (DMs need no @mention) or @mention it in a channel it can see.

### How it behaves in a server

| Context | Behaviour |
|---|---|
| DMs | Always answers, no mention needed, own session per DM |
| Server channels | Answers only when **@mentioned** (unless the channel is in `DISCORD_FREE_RESPONSE_CHANNELS`) |
| Threads | Replies in-thread; own session namespace, isolated from the parent channel |
| Multiple users | Session history is per-user per-channel by default (`group_sessions_per_user`) |

Useful toggles, all in `.env`: `DISCORD_REQUIRE_MENTION=false`,
`DISCORD_FREE_RESPONSE_CHANNELS=<ids>`, `DISCORD_AUTO_THREAD`,
`DISCORD_IGNORE_NO_MENTION`.

---

## Part 6 — Run the gateway as a service

```bash
hermes gateway install     # writes the systemd/launchd service
hermes gateway start
hermes gateway status
```

Operate it:

```bash
hermes gateway restart
journalctl --user -u hermes-gateway -f           # live service log
grep -i "failed to send\|error" ~/.hermes/logs/gateway.log | tail -20
```

If the bot goes offline after you close SSH, linger (Part 1, step 6) is missing
or the service definition is stale — re-run `hermes gateway install`.

**Do not restart the gateway casually on a box that is mid-task.** An in-flight
session dies with it, and cron jobs miss their tick. Prefer `/restart` from chat,
which drains first.

---

## Part 7 — Host this toolkit for download (Vercel)

The gateway cannot run on Vercel. The download/landing page can, and that is what
you want: a public URL where someone reads the capability map and grabs the ZIP
or the one-line installer.

```bash
mkdir -p ~/toolkit-site && cd ~/toolkit-site
# copy site/index.html out of this repo, then:
npx vercel@latest deploy --prod
```

Or connect the GitHub repo to Vercel in the dashboard and set the **Root
Directory** to `site/` — every push then redeploys the page.

**Before you rely on Vercel, check your account is actually deploying.** A
project that exceeds the Hobby plan's included transfer gets soft-blocked and
every deploy returns **HTTP 402** while the dashboard still looks healthy. Confirm
with a throwaway deploy; if you are blocked, use Cloudflare Pages instead — same
static files, no account block:

```bash
npx wrangler@latest pages deploy site --project-name=nft-mint-rarity-toolkit
```

Either way the artifacts people download are the same:

| Artifact | URL |
|---|---|
| Source ZIP | `https://github.com/andyemad/nft-mint-rarity-toolkit/archive/refs/heads/main.zip` |
| One-line installer | `curl -fsSL https://raw.githubusercontent.com/andyemad/nft-mint-rarity-toolkit/main/install.sh \| bash` |
| Skills only | the `skills/` directory in the repo |

---

## Part 8 — Verify the whole chain

Work down this list; each row isolates one layer, so a failure tells you where to
look rather than "the bot is broken".

```bash
hermes --version                       # 1. binary on PATH
hermes doctor                          # 2. dependencies + config
hermes chat -q "reply with OK"         # 3. model provider + key
hermes skills list | grep rarity       # 4. toolkit skills present
hermes gateway status                  # 5. service up
tail -20 ~/.hermes/logs/gateway.log    # 6. gateway connected to Discord
```

Then in Discord: DM the bot, and @mention it in a channel.

| Symptom | Cause |
|---|---|
| Bot is online but never replies in channels | Not @mentioned — mention it, or add the channel to `DISCORD_FREE_RESPONSE_CHANNELS` |
| Bot appears dead everywhere | **Message Content Intent** not enabled in the Developer Portal |
| Gateway up, everyone denied | `DISCORD_ALLOWED_USERS` missing or wrong ID |
| Died after closing SSH | `sudo loginctl enable-linger $USER`, then reinstall the service |
| "No models provided" / 401 | Wrong or missing provider key in `~/.hermes/.env`; re-run `hermes model` |
| Skills not loading | `hermes skills list` to confirm, `/reload-skills` in a running session |
| Bot dies during long tasks | 2 GB RAM OOM — add swap (Part 1) or resize to 4 GB |

---

## Part 9 — Security notes for a public-facing agent

- **Never expose the terminal backend's host.** Hermes runs real shell commands.
  Keep the VPS firewalled to SSH, and do not enable the API Server adapter or
  webhook routes until you need them and understand the auth model.
- **Use `DISCORD_ALLOWED_USERS`, not `DISCORD_ALLOW_ALL_USERS`.** In a public
  server, allow-all means strangers can drive a shell on your box.
- **Approvals stay on.** Leave `approvals.mode` at `manual` (or `smart`) so
  destructive commands require a human yes.
- **Keys live in `~/.hermes/secrets/` at `chmod 600`,** never in the repo, never
  pasted into a chat.
- **Back up** `~/.hermes/` (config, skills, sessions, memory) somewhere off the
  box. `hermes profile export` produces a tar.gz you can move.
- **Update deliberately:** `hermes update` — then re-check `hermes doctor`.

---

## Appendix — OpenCode

Sign up with my referral link: **https://opencode.ai/go?ref=0N4C2C5TNK**

Use it as the Hermes provider (Part 3) or as a standalone coding agent. The key
goes in `~/.hermes/.env` as `OPENCODE_GO_API_KEY`, then select it with
`hermes model`.
