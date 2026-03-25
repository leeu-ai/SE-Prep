# SE Morning Prep — Wix Enterprise Solutions Engineering

Automated demo prep system for the SE team. Each weekday at 7am, it scans your Google Calendar for upcoming external meetings, researches each company (web + Gong history + Coda demo guides), generates an HTML brief, and sends you a Slack summary.

---

## Quick Start (new team members)

```bash
# 1. Clone the repo
git clone https://github.com/leeu-ai/SE-Prep.git ~/Documents/SE\ Tools/gong_intel

# 2. Run setup (interactive — takes ~2 minutes)
bash ~/Documents/SE\ Tools/gong_intel/setup.sh

# 3. Activate terminal shortcuts
source ~/.zshrc
```

That's it. The setup script installs dependencies, collects your credentials, sets up the 7am automation, and adds terminal shortcuts.

---

## Requirements

- **Claude Code** — `npm install -g @anthropic-ai/claude-code`
- **MCPs in Claude Code** — Google Calendar, Slack, Wix (configure in `.claude/settings.json`)
- **Python 3** with: `requests`, `python-dotenv`, `duckduckgo-search` (setup.sh installs these)

---

## Credentials you'll need

| Credential | Where to get it | Shared? |
|---|---|---|
| **Gong Access Key + Secret** | Pre-filled in setup (team key) | Yes |
| **Anthropic API Key** | https://console.anthropic.com/settings/keys | No — use your own |
| **Coda API Token** | https://coda.io/account → API Settings | No — use your own |
| **Slack User ID** | Slack → click profile photo → Copy member ID | No — yours |

---

## Terminal commands

```bash
se-prep              # Same as 7am automation — scans next 48h
se-prep-week         # Scans next 14 days (for testing or planning ahead)

# Prep for a specific company:
se-prep-for "Company Name" domain.com "Attendee One, Attendee Two"

# Build a Wix demo site from an existing brief:
se-demo-site "Company Name"

# Pull latest updates from the team:
se-update
```

---

## How it works

1. **Calendar scan** — finds external meetings (non-Wix attendees, not declined, not all-day)
2. **Research** — DuckDuckGo web research, Gong call history, Coda demo guides
3. **Brief generation** — Claude synthesizes everything into an HTML brief + site parameters JSON
4. **Notification** — macOS notification + Slack summary with meeting details and recommended focus
5. **Wix demo site** — on request, creates a fully personalised Wix Studio site

---

## Staying updated

When the team pushes improvements to scripts or CLAUDE.md:
```bash
se-update            # pulls latest from GitHub
bash setup.sh        # re-run only if setup.sh itself changed
```

Your `.env` (credentials) and `Briefs/` (output) are gitignored — they won't be overwritten by updates.

---

## File overview

| File | Purpose |
|---|---|
| `morning_prep.py` | Core pipeline: web → Gong → Coda → Claude → HTML brief |
| `gong_intel.py` | Gong API client: fetch transcripts, summarize with Claude |
| `CLAUDE.md` | Instructions Claude Code reads (generated per-person from template) |
| `CLAUDE.md.template` | Team template with `{{SLACK_USER_ID}}` / `{{SLACK_CHANNEL_ID}}` placeholders |
| `setup.sh` | One-command team onboarding |
| `install_aliases.sh` | Standalone alias installer |
| `.env.template` | Credential template (for reference) |
| `.gitignore` | Keeps `.env`, `Briefs/`, logs out of git |

---

## Troubleshooting

**No brief generated / synthesis timeout** — re-run with `--days 30` to reduce Gong data

**Coda guides not found** — check `CODA_API_TOKEN` in `.env` and that the token has read access

**Slack message not received** — self-sent messages don't trigger alerts; the macOS notification (Chime sound) fires separately

**launchd not running** — `launchctl list | grep se-morning-prep` to check. Reload: `launchctl unload ~/Library/LaunchAgents/com.wix.se-morning-prep.plist && launchctl load ~/Library/LaunchAgents/com.wix.se-morning-prep.plist`

**Updating after git pull** — your `CLAUDE.md` is generated from the template, so if the template changed, re-run `bash setup.sh` to regenerate it
