#!/bin/bash
# =============================================================================
# SE Morning Prep — Team Setup Script
# =============================================================================
# Run this once to configure the full SE morning prep system for your Mac.
#
# For new team members — clone the repo first, then run this:
#   git clone https://github.com/leeu-ai/SE-Prep.git ~/Documents/SE\ Tools/gong_intel
#   bash ~/Documents/SE\ Tools/gong_intel/setup.sh
#
# For existing users — just run this again after a git pull to refresh config.
# =============================================================================

set -e

TOOLS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ZSHRC="$HOME/.zshrc"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║         SE Morning Prep — Setup                      ║"
echo "║         Wix Enterprise Solutions Engineering         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Python dependencies ───────────────────────────────────────────────
echo "📦 Installing Python dependencies..."
pip3 install --quiet --break-system-packages requests python-dotenv duckduckgo-search 2>/dev/null || \
pip3 install --quiet requests python-dotenv duckduckgo-search
echo "   ✅ Done"
echo ""

# ── Step 2: Create Briefs folder ──────────────────────────────────────────────
mkdir -p "$TOOLS_DIR/Briefs"
echo "📁 Briefs/ folder ready"
echo ""

# ── Step 3: Collect credentials ───────────────────────────────────────────────
echo "🔑 Let's set up your credentials."
echo "   (Press Enter to keep the default where shown)"
echo ""

# Gong keys — pre-filled with team credentials
echo "   ── Gong (team credentials — defaults are pre-filled) ──"
read -p "   Gong Access Key [DUQEG3CGIPOQU6I7DSZLXWUPNTTM7JSZ]: " GONG_KEY
GONG_KEY="${GONG_KEY:-DUQEG3CGIPOQU6I7DSZLXWUPNTTM7JSZ}"
read -p "   Gong Access Key Secret [pre-filled]: " GONG_SECRET
GONG_SECRET="${GONG_SECRET:-eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjIwODk1MjcwOTcsImFjY2Vzc0tleSI6IkRVUUVHM0NHSVBPUVU2STdEU1pMWFdVUE5UVE03SlNaIn0.jzI4iwlkyZ4qwMxgHSZi21SSYhoKOfr_gQliGBJDjRc}"
read -p "   Gong Base URL [https://us-40005.api.gong.io]: " GONG_URL
GONG_URL="${GONG_URL:-https://us-40005.api.gong.io}"
echo ""

# Personal keys — must be entered per person
echo "   ── Personal keys (you must provide your own) ──"
read -p "   Anthropic API Key (console.anthropic.com/settings/keys): " ANTHROPIC_KEY
while [ -z "$ANTHROPIC_KEY" ]; do
  echo "   ⚠️  Anthropic API key is required — the research pipeline needs it."
  read -p "   Anthropic API Key: " ANTHROPIC_KEY
done

read -p "   Coda API Token (coda.io/account → API Settings): " CODA_TOKEN
echo ""

# ── Step 4: Collect Slack info ────────────────────────────────────────────────
echo "💬 Slack configuration"
echo "   Your Slack user ID: open Slack → click your profile → 'Copy member ID'"
echo "   It looks like: U012AB3CD"
read -p "   Your Slack User ID: " SLACK_USER_ID
while [ -z "$SLACK_USER_ID" ]; do
  echo "   ⚠️  Slack user ID is required for @mention notifications."
  read -p "   Your Slack User ID: " SLACK_USER_ID
done

echo ""
echo "   Slack channel ID for notifications: C0ANF28TR6F (team default)"
echo "   Press Enter to use the team default, or paste a different channel ID."
read -p "   Slack Channel ID [C0ANF28TR6F]: " SLACK_CHANNEL
SLACK_CHANNEL="${SLACK_CHANNEL:-C0ANF28TR6F}"
echo ""

# ── Step 5: Write .env ────────────────────────────────────────────────────────
ENV_FILE="$TOOLS_DIR/.env"
cat > "$ENV_FILE" << EOF
# ── Gong API (team credentials) ──────────────────────────────────────────────
GONG_ACCESS_KEY=${GONG_KEY}
GONG_ACCESS_KEY_SECRET=${GONG_SECRET}
GONG_BASE_URL=${GONG_URL}

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=${ANTHROPIC_KEY}

# ── Coda ──────────────────────────────────────────────────────────────────────
CODA_API_TOKEN=${CODA_TOKEN}
CODA_DOC_ID=HAjz6ieZVT

# ── Slack ─────────────────────────────────────────────────────────────────────
SLACK_USER_ID=${SLACK_USER_ID}
SLACK_CHANNEL_ID=${SLACK_CHANNEL}
EOF

echo "   ✅ .env created at $ENV_FILE"
echo ""

# ── Step 6: Generate CLAUDE.md from template ──────────────────────────────────
TEMPLATE="$TOOLS_DIR/CLAUDE.md.template"
CLAUDE_MD="$TOOLS_DIR/CLAUDE.md"

if [ -f "$TEMPLATE" ]; then
  sed \
    -e "s|{{SLACK_USER_ID}}|${SLACK_USER_ID}|g" \
    -e "s|{{SLACK_CHANNEL_ID}}|${SLACK_CHANNEL}|g" \
    -e "s|{{TOOLS_DIR}}|${TOOLS_DIR}|g" \
    "$TEMPLATE" > "$CLAUDE_MD"
  echo "   ✅ CLAUDE.md generated from template"
else
  echo "   ⚠️  CLAUDE.md.template not found — using existing CLAUDE.md"
fi
echo ""

# ── Step 7: Generate & install launchd plist ──────────────────────────────────
PLIST_NAME="com.wix.se-morning-prep.plist"
PLIST_SRC="$TOOLS_DIR/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

cat > "$PLIST_SRC" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wix.se-morning-prep</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/claude</string>
        <string>--print</string>
        <string>--dangerously-skip-permissions</string>
        <string>Run the SE morning prep flow as described in CLAUDE.md</string>
    </array>

    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
    </array>

    <key>WorkingDirectory</key>
    <string>${TOOLS_DIR}</string>

    <key>StandardOutPath</key>
    <string>${TOOLS_DIR}/claude_morning_prep.log</string>

    <key>StandardErrorPath</key>
    <string>${TOOLS_DIR}/claude_morning_prep.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

# Unload old version if it exists
launchctl unload "$PLIST_DEST" 2>/dev/null || true

cp "$PLIST_SRC" "$PLIST_DEST"
launchctl load "$PLIST_DEST"
echo "   ✅ 7am launchd automation installed and active"
echo ""

# ── Step 8: Install shell aliases ────────────────────────────────────────────
# Remove any old SE prep aliases
sed -i '' '/SE Morning Prep shortcuts/,/─────────────────────────────────────────────────────────────────────────────/d' "$ZSHRC" 2>/dev/null || true

cat >> "$ZSHRC" << ALIASES

# ── SE Morning Prep shortcuts ─────────────────────────────────────────────────
SE_TOOLS="${TOOLS_DIR}"

# Automated morning flow — 48h calendar window (same as 7am launchd)
alias se-prep='cd "\$SE_TOOLS" && claude --print --dangerously-skip-permissions "Run the SE morning prep flow as described in CLAUDE.md"'

# On-demand — scans next 14 days (for on-demand use)
alias se-prep-week='cd "\$SE_TOOLS" && claude --print --dangerously-skip-permissions "Run the SE morning prep flow as described in CLAUDE.md, but scan Google Calendar for the next 14 days instead of 48 hours."'

# Prep for a specific company: se-prep-for "Company" domain.com "Name1, Name2"
se-prep-for() {
  cd "\$SE_TOOLS" && claude --print --dangerously-skip-permissions \
    "Run morning_prep.py for company \"\$1\", domain \$2, attendees \"\${3:-}\". Send results to Slack channel ${SLACK_CHANNEL} and fire a macOS notification when done. Then ask me if I want a Wix demo site."
}

# Create Wix demo site from a saved brief: se-demo-site "Company"
se-demo-site() {
  local slug
  slug=\$(echo "\$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_//;s/_\$//')
  cd "\$SE_TOOLS" && claude --print --dangerously-skip-permissions \
    "Create a Wix demo site for \"\$1\" using the parameters in Briefs/\${slug}_site_request.json. Deeply personalise CMS collections with at least 5-8 realistic, company-specific items using real brand names, geography, and product lines."
}

# Update from GitHub: se-update
alias se-update='cd "\$SE_TOOLS" && git pull origin main && echo "✅ Updated to latest version"'
# ─────────────────────────────────────────────────────────────────────────────
ALIASES

echo "   ✅ Shell aliases installed"
echo ""

# ── Done ──────────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✅  Setup complete!                                ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. source ~/.zshrc                  (or open a new terminal tab)"
echo "  2. Install Claude Code if you haven't:"
echo "       npm install -g @anthropic-ai/claude-code"
echo "  3. Connect your MCPs in Claude Code:"
echo "       • Google Calendar"
echo "       • Slack"
echo "       • Wix"
echo "  4. Test it: se-prep-week"
echo ""
echo "Commands:"
echo "  se-prep            → 48h scan (same as 7am automation)"
echo "  se-prep-week       → 14-day scan (for on-demand use)"
echo "  se-prep-for \"Company\" domain.com \"Names\""
echo "  se-demo-site \"Company\""
echo "  se-update          → git pull latest changes from the team"
echo ""
