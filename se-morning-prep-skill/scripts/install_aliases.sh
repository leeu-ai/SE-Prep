#!/bin/bash
# Run this once to add SE prep shortcuts to your terminal
# Usage: bash ~/Documents/SE\ Tools/gong_intel/install_aliases.sh

ZSHRC="$HOME/.zshrc"

# Remove any old SE prep aliases first
sed -i '' '/SE Morning Prep shortcuts/,/─────────────────────────────────────────────────────────────────────────────/d' "$ZSHRC" 2>/dev/null

cat >> "$ZSHRC" << 'ALIASES'

# ── SE Morning Prep shortcuts ─────────────────────────────────────────────────
SE_TOOLS="$HOME/Documents/SE Tools/gong_intel"

# 7am automated flow — 48h window (same as launchd)
alias se-prep='cd "$SE_TOOLS" && claude --print --dangerously-skip-permissions "Run the SE morning prep flow as described in CLAUDE.md"'

# On-demand — scans next 14 days so you always find upcoming meetings
alias se-prep-week='cd "$SE_TOOLS" && claude --print --dangerously-skip-permissions "Run the SE morning prep flow as described in CLAUDE.md, but scan Google Calendar for the next 14 days instead of 48 hours."'

# Prep for a specific company (skips calendar scan entirely):
# se-prep-for "Broadridge Financial" broadridge.com "Jill Beglin, Karen Montagna"
se-prep-for() {
  cd "$SE_TOOLS" && claude --print --dangerously-skip-permissions \
    "Run morning_prep.py for company \"$1\", domain $2, attendees \"${3:-}\". Send results to Slack channel C0ANF28TR6F and fire a macOS notification when done. Then ask me if I want a Wix demo site."
}

# Create a Wix demo site from an existing brief:
# se-demo-site "Broadridge Financial"
se-demo-site() {
  local slug
  slug=$(echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_//;s/_$//')
  cd "$SE_TOOLS" && claude --print --dangerously-skip-permissions \
    "Create a Wix demo site for \"$1\" using the parameters in Briefs/${slug}_site_request.json. Deeply personalise the CMS collections with realistic prospect-relevant content — at least 5-8 items per collection using real brand names, geography and product lines. Do not skip personalisation."
}
# ─────────────────────────────────────────────────────────────────────────────
ALIASES

echo ""
echo "✅ SE prep aliases installed!"
echo ""
echo "Commands:"
echo "  se-prep            → automated flow, 48h calendar window (same as 7am launchd)"
echo "  se-prep-week       → on-demand, 14-day window — use this for testing"
echo "  se-prep-for \"Company\" domain.com \"Name1, Name2\""
echo "  se-demo-site \"Company\""
echo ""
echo "Run: source ~/.zshrc"
