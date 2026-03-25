# SE Morning Prep — Wix Enterprise Solutions Engineering

Automated demo prep system for the SE team. Each weekday at 7am, it scans your Google Calendar for upcoming external meetings, researches each company (web + Gong history + Coda demo guides), generates an HTML brief, and sends you a Slack summary.

---

## Team Setup (new members — run this once)

```bash
bash ~/Documents/SE\ Tools/gong_intel/setup.sh
```

The setup script will walk you through everything interactively:
- Installs Python dependencies
- Collects your credentials (Gong, Anthropic, Coda, Slack)
- Creates your `.env` file
- Generates your personal `CLAUDE.md` (with your Slack ID)
- Installs the 7am launchd automation (Mon–Fri)
- Adds terminal shortcuts to `~/.zshrc`

After setup, run `source ~/.zshrc` to activate the terminal shortcuts.

---

## Requirements

- **Claude Code** installed: `npm install -g @anthropic-ai/claude-code`
- **MCPs configured** in Claude Code (`.claude/settings.json`):
  - Google Calendar MCP
  - Slack MCP
  - Wix MCP
- **Python 3** with: `requests`, `python-dotenv`, `duckduckgo-search`

---

## Credentials you'll need

| Credential | Where to get it |
|---|---|
| **Gong Access Key + Secret** | Gong → Settings → API → Access Keys |
| **Anthropic API Key** | https://console.anthropic.com/settings/keys |
| **Coda API Token** | Coda → Settings → API → Generate Token |
| **Slack User ID** | Slack → click your profile photo → Copy member ID (looks like `U012AB3CD`) |
| **Slack Channel ID** | Ask your team lead for the SE prep channel ID |

---

## Terminal commands (after setup)

```bash
se-prep              # Same as 7am automation — scans next 48h
se-prep-week         # Scans next 14 days (use for testing or planning ahead)

# Prep for a specific company (skips calendar scan):
se-prep-for "Company Name" domain.com "Attendee One, Attendee Two"

# Build a Wix demo site from an existing brief:
se-demo-site "Company Name"
```

---

## How it works

1. **Calendar scan** — finds external meetings in the next 48h (non-Wix attendees, not declined, not all-day)
2. **Research** — for each meeting: DuckDuckGo web research, Gong call history, Coda demo guides
3. **Brief generation** — Claude synthesizes everything into an HTML brief + site parameters JSON, saved to `Briefs/`
4. **Notification** — macOS notification fires immediately; Slack summary sent to team channel with meeting details, recommended focus, and Gong/Coda status
5. **Wix demo site** — on request, creates a fully personalised Wix Studio site using the brief parameters

---

## File overview

| File | Purpose |
|---|---|
| `morning_prep.py` | Core pipeline: web research → Gong → Coda → Claude synthesis → HTML brief |
| `CLAUDE.md` | Instructions Claude Code reads automatically when run from this folder |
| `CLAUDE.md.template` | Team template — `setup.sh` generates your personal `CLAUDE.md` from this |
| `setup.sh` | One-command team onboarding script |
| `install_aliases.sh` | Standalone alias installer (used if not running full setup) |
| `.env.template` | Copy to `.env` and fill in credentials |
| `com.leeu.se-morning-prep.plist` | Lee's launchd plist (7am Mon–Fri automation) |
| `Briefs/` | Generated HTML briefs and site parameter JSON files |

---

## Manual run (without terminal shortcuts)

```bash
cd ~/Documents/SE\ Tools/gong_intel
claude --print --dangerously-skip-permissions "Run the SE morning prep flow as described in CLAUDE.md"
```

Or for a specific company:
```bash
python3 morning_prep.py --domain company.com --name "Company Name" --attendees "Name1, Name2"
```

---

## Troubleshooting

**No brief generated / synthesis timeout** — re-run with `--days 30` to reduce Gong data pulled

**Coda guides not found** — check that your `CODA_API_TOKEN` is set in `.env` and the token has read access to the SE demo guides doc

**Slack message not received** — messages sent from your own account don't trigger notifications; the macOS notification (Chime sound) fires separately and works regardless

**launchd not running** — check: `launchctl list | grep se-morning-prep`. To reload: `launchctl unload ~/Library/LaunchAgents/com.wix.se-morning-prep.plist && launchctl load ~/Library/LaunchAgents/com.wix.se-morning-prep.plist`
