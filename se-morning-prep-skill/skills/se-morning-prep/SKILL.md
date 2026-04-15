---
name: se-morning-prep
description: "Run the SE morning prep flow — scan Google Calendar for external meetings in the next 48h, search Slack for internal context, research each company, generate HTML briefs, and send a Slack summary. Optionally builds Wix demo sites."
---

You are running the SE Morning Prep flow for a Wix Enterprise Solutions Engineer.

## Prerequisites check

Before starting, verify the scripts folder exists:
- Default location: `~/Documents/SE Tools/gong_intel/`
- If `morning_prep.py` is not found there, tell the user to run `bash ~/Documents/SE\ Tools/gong_intel/setup.sh` first and stop.

---

## STEP 1 — Find External Meetings

Call `gcal_list_events` with:
- timeMin = now
- timeMax = now + 48 hours
- condenseEventDetails: false

An EXTERNAL meeting has ALL of:
- At least one @wix.com attendee (internal) AND at least one non-@wix.com attendee (client)
- The SE's status is NOT "declined"
- NOT all-day
- Title does NOT contain: "OOO", "Focus", "Reclaim"

Extract per meeting: `domain` (from external attendee email), `company_name`, `attendees` (comma-separated names of non-@wix.com people).

**If no external meetings found:**
```bash
osascript -e 'display notification "No external meetings in the next 48h — enjoy the clear schedule!" with title "🟢 SE Morning Prep" sound name "Chime"'
```
Then send a Slack message to the user's configured channel: "No external meetings in the next 48h — enjoy the clear schedule! 🟢"
Then stop.

---

## STEP 2 — For Each External Meeting

### 2a. Check for an existing brief

Before doing any research, check if a brief already exists for this company in `~/Documents/SE Tools/gong_intel/Briefs/`. Look for a file matching `{slug}_brief_*.html` (e.g. `broadridge_brief_*.html`).

**If a brief exists from today** → skip to STEP 3. No new research needed.

**If a brief exists from a previous day** → do a lightweight update check:
1. Search Slack for any new mentions since the brief was generated
2. If new meaningful Slack context is found (new blockers, deal updates, stakeholder changes) → re-run the full flow (steps 2b onward) and note "Updated" in the Slack message
3. If nothing new → reuse the existing brief. Note "No updates — using existing brief from [date]" in the Slack message

**If no brief exists** → run the full flow below.

### 2b. Search Slack for Internal Context

Search Slack for internal context about this company. Use `slack_search_public_and_private` with these queries (run all three):
- `"COMPANY NAME"` — direct mentions
- `"DOMAIN"` — email domain mentions (e.g. in deal threads)
- Names of the external attendees — in case colleagues mentioned them

Compile relevant results (deal status, blockers, internal sentiment, deadlines, action items) into a text summary. Save it to a temp file:
```bash
cat > /tmp/slack_context_SLUG.txt << 'SLACK_EOF'
[Paste compiled Slack findings here]
SLACK_EOF
```

If no Slack results found, skip the file — morning_prep.py handles missing context gracefully.

### 2c. Run morning_prep.py — data fetch only

```bash
cd ~/Documents/SE\ Tools/gong_intel && python3 morning_prep.py \
  --data-only \
  --domain DOMAIN \
  --name "COMPANY NAME" \
  --attendees "Name1, Name2, Name3" \
  [--slack-context /tmp/slack_context_SLUG.txt]
```

Omit `--slack-context` if no Slack results were found. This saves all raw data (web research, Gong transcripts, Coda pages, Slack context) to `/tmp/{slug}_raw_data.json`. No API key needed.

### 2d. Synthesize the brief natively (no API key needed)

Read `/tmp/{slug}_raw_data.json`. Using the data in that file, produce a brief JSON with **exactly** these fields and save it to `/tmp/{slug}_brief.json`:

```json
{
  "gong_intel": {
    "last_interaction": "YYYY-MM-DD",
    "call_count": 0,
    "products_discussed": [],
    "pain_points": [],
    "open_questions": [],
    "key_quotes": [],
    "recommended_focus": "...",
    "summary": "..."
  },
  "selected_verticals": ["Studio Editor", "CMS"],
  "company_summary": "...",
  "industry": "...",
  "company_size": "...",
  "tech_stack": [],
  "why_wix": "...",
  "attendees": [{"name":"...","title":"...","background":"...","talk_to":"..."}],
  "pain_points": [],
  "open_questions": [],
  "key_quotes": [],
  "recommended_focus": "...",
  "deal_context": "...",
  "demo_script": [{"vertical":"...","headline":"...","key_features":[],"talking_points":[],"discovery_questions":[]}],
  "agenda": [{"title":"...","duration":"X min","notes":"..."}],
  "has_gong_history": true,
  "has_coda_guides": true,
  "gong_last_interaction": "YYYY-MM-DD",
  "gong_call_count": 0
}
```

Use source tags in text fields where appropriate: `[WEB]`, `[GONG]`, `[SLACK]`, `[CODA]`

### 2e. Render the brief

```bash
cd ~/Documents/SE\ Tools/gong_intel && python3 morning_prep.py \
  --from-brief /tmp/{slug}_brief.json \
  --domain DOMAIN \
  --name "COMPANY NAME" \
  --attendees "Name1, Name2, Name3"
```

This renders the HTML brief and saves `{slug}_site_request.json` to `~/Documents/SE Tools/gong_intel/Briefs/`. Note the brief HTML path from `[Done] Brief saved to: ...`

### 2f. Verify Coda Demo Script

Read the generated HTML brief. If the "Personalized Demo Script" section is MISSING, note this in the Slack message so the SE knows to pull Coda guides manually.

---

## STEP 3 — Notification + Slack Summary

Fire a macOS notification immediately:
```bash
osascript -e 'display notification "Your SE briefs are ready — check Slack for details." with title "🌅 SE Morning Prep Complete" sound name "Chime"'
```

Then send a Slack message to the user's configured channel (from `.env` → `SLACK_CHANNEL_ID`), mentioning their user ID (`SLACK_USER_ID`):

```
<@SLACK_USER_ID> 🌅 *Good morning! Here's your SE prep for the next 48h:*

*1. [Company Name]* — [Meeting time, e.g. "Wed Mar 25 at 2:00 PM IST"]
📋 Brief: [brief filename]
🎯 Focus: [recommended_focus from site_request.json]
👥 Attendees: [names]
📞 Gong: [X calls found / No prior history]
📬 Slack: [✅ Internal context found / No internal mentions]
🗂️ Verticals: [selected_verticals from site_request.json]
📊 Coda: [✅ Demo script included / ⚠️ Pull manually]

[Repeat block for each meeting]

---
🌐 *Want a Wix demo site for any of these?*
Say: "Create demo site for [Company]" in Claude Code

_Briefs saved to: ~/Documents/SE Tools/gong_intel/Briefs/_
```

---

## STEP 4 — Wix Demo Site (only if explicitly requested)

If the user asked to create a Wix demo site (e.g. "create demo site for Acme"):

1. Read `~/Documents/SE Tools/gong_intel/Briefs/{slug}_site_request.json` for:
   - company_name, domain, industry, company_summary, why_wix
   - pain_points, tech_stack, recommended_focus, selected_verticals, attendees

2. **ListWixSites** — check if a demo site already exists for this company. If found → show the URL and stop.

3. **CreateWixBusinessGuide** — find the most appropriate Wix Studio template for the company's specific industry and use case. Be precise: a mortgage network needs a financial template, not a generic business one.

4. **ManageWixSite** — create the site from the chosen template, named "[Company] Demo — Wix Enterprise"

5. **CallWixSiteAPI** — deeply personalise the site. Do NOT skip this or do it superficially.

   **CMS Collections (REQUIRED):** Create and populate collections with realistic, company-specific content. Content should feel built FOR this specific prospect, not a generic demo. Use the company's actual geography, pricing tiers, brand names, and product categories from the brief's web research.
   - Minimum 5–8 CMS items per collection (not 1–2 placeholders)
   - Content uses the company's real brand names, geography, and product lines
   - Pain points from the brief are addressed visibly in the site structure
   - Forms configured for their actual use case (lead capture, booking, application, etc.)

   **Apps to install** based on selected_verticals:
   - eCom → `1380b703-ce81-ff05-f115-39571d94dfcd`
   - Events → `140603ad-af8d-84a5-2c80-a0f60cb47351`
   - Bookings/Services → `13d21c63-b5ec-5912-8397-c3a5ddb27a97`
   - Blog → `14bcded7-0066-7c35-14d7-466cb3f09103`
   - Forms → `14ce1214-b278-a7e4-1373-00cebd1bef7c`
   - Chat → `14517e1a-3ff0-af98-408e-2bd6953c36a2`

6. Publish the site and return the live URL.

---

## NOTES

- Scripts location: `~/Documents/SE Tools/gong_intel/`
- Briefs and JSONs: `~/Documents/SE Tools/gong_intel/Briefs/`
- Credentials are in `.env` in the scripts folder — loaded automatically
- Use `python3` not `python`
- 0 Gong calls = fine, just note "No prior history"
- If morning_prep.py times out on data fetch, re-run with `--days 90`
- NEVER use browser automation for Wix site creation — always use Wix MCP tools (ListWixSites, CreateWixBusinessGuide, ManageWixSite, CallWixSiteAPI)
- Read SLACK_CHANNEL_ID and SLACK_USER_ID from `~/Documents/SE Tools/gong_intel/.env`
