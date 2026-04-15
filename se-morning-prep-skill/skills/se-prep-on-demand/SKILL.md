---
name: se-prep-on-demand
description: "On-demand SE prep — scans the next 14 days of Google Calendar, lets you pick which meetings to prep for, searches Slack for internal context, generates HTML briefs, and optionally creates Wix demo sites. Use this when you want to prep for a specific upcoming meeting rather than just the next 48h."
---

You are running the SE Morning Prep on-demand flow for a Wix Enterprise Solutions Engineer. This is the interactive version — you'll see all external meetings in the next 14 days and choose which ones to research.

## Prerequisites check

Verify the scripts folder exists at `~/Documents/SE Tools/gong_intel/`. If `morning_prep.py` is not found, tell the user to run `bash ~/Documents/SE\ Tools/gong_intel/setup.sh` first and stop.

---

## STEP 1 — Scan 14 Days of Calendar

Call `gcal_list_events` with:
- timeMin = now
- timeMax = now + 14 days
- condenseEventDetails: false

An EXTERNAL meeting has ALL of:
- At least one @wix.com attendee AND at least one non-@wix.com attendee
- The SE's status is NOT "declined"
- NOT all-day
- Title does NOT contain: "OOO", "Focus", "Reclaim"

Build a numbered list of external meetings found, including:
- Company name (from external attendee domain)
- Date and time
- Non-Wix attendee names

If no external meetings found → tell the user and stop.

---

## STEP 2 — Let User Pick

Present the list of external meetings and ask the user which ones to prep for. For example:

"Found 4 external meetings in the next 14 days:
1. Dominion Lending Centres — Mon Mar 30 at 2:00 PM
2. RE/MAX — Wed Apr 1 at 10:00 AM
3. Coldwell Banker — Thu Apr 2 at 3:00 PM
4. Ylopo — Fri Apr 3 at 11:00 AM

Which would you like to prep for? (say 'all' or list numbers, e.g. '1, 3')"

Wait for the user's response before proceeding.

---

## STEP 3 — For Each Selected Meeting

### 3a. Check for an existing brief

Before doing any research, check if a brief already exists for this company in `~/Documents/SE Tools/gong_intel/Briefs/`. Look for a file matching `{slug}_brief_*.html`.

**If a brief exists from today** → skip to STEP 5 for this company.

**If a brief exists from a previous day** → do a lightweight update check:
1. Search Slack for any new mentions since the brief was generated
2. If new meaningful Slack context found → re-run the full flow (steps 3b onward)
3. If nothing new → reuse the existing brief and note "No updates — using existing brief from [date]"

**If no brief exists** → run the full flow below.

### 3b. Search Slack for Internal Context

Search Slack for internal context about the company. Use `slack_search_public_and_private` with these queries (run all three):
- `"COMPANY NAME"` — direct mentions
- `"DOMAIN"` — email domain mentions
- Names of the external attendees

Compile relevant results into a text summary. Save to a temp file:
```bash
cat > /tmp/slack_context_SLUG.txt << 'SLACK_EOF'
[Compiled Slack findings]
SLACK_EOF
```

If no Slack results found, skip the file — morning_prep.py handles missing context gracefully.

### 3c. Run morning_prep.py — data fetch only

```bash
cd ~/Documents/SE\ Tools/gong_intel && python3 morning_prep.py \
  --data-only \
  --domain DOMAIN \
  --name "COMPANY NAME" \
  --attendees "Name1, Name2, Name3" \
  [--slack-context /tmp/slack_context_SLUG.txt]
```

Omit `--slack-context` if no Slack results were found. This saves all raw data to `/tmp/{slug}_raw_data.json`. No API key needed.

### 3d. Synthesize the brief natively (no API key needed)

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

### 3e. Render the brief

```bash
cd ~/Documents/SE\ Tools/gong_intel && python3 morning_prep.py \
  --from-brief /tmp/{slug}_brief.json \
  --domain DOMAIN \
  --name "COMPANY NAME" \
  --attendees "Name1, Name2, Name3"
```

Note the brief HTML path from `[Done] Brief saved to: ...`

---

## STEP 4 — Verify Coda Demo Scripts

For each brief generated, read the HTML and check whether the "Personalized Demo Script" section is present. Note which ones are missing — the user will need to pull those Coda guides manually.

---

## STEP 5 — macOS Notification + Slack Summary

Fire a macOS notification:
```bash
osascript -e 'display notification "Your SE briefs are ready — check Slack for details." with title "🌅 SE Prep Complete" sound name "Chime"'
```

Then send a Slack message to the channel in `.env` → `SLACK_CHANNEL_ID`, mentioning `SLACK_USER_ID`:

```
<@SLACK_USER_ID> 🌅 *SE prep complete — here's your summary:*

*1. [Company Name]* — [Meeting time]
📋 Brief: [brief filename]
🎯 Focus: [recommended_focus from site_request.json]
👥 Attendees: [names]
📞 Gong: [X calls found / No prior history]
📬 Slack: [✅ Internal context found / No internal mentions]
🗂️ Verticals: [selected_verticals from site_request.json]
📊 Coda: [✅ Demo script included / ⚠️ Pull manually]

[Repeat for each meeting prepped]

---
🌐 *Want a Wix demo site for any of these?*
Say: "Create demo site for [Company]"

_Briefs saved to: ~/Documents/SE Tools/gong_intel/Briefs/_
```

---

## STEP 6 — Offer Wix Demo Sites

After the Slack summary, ask the user: "Would you like me to create a Wix demo site for any of these companies?"

If yes, for each requested company:

1. Read `~/Documents/SE Tools/gong_intel/Briefs/{slug}_site_request.json`

2. **ListWixSites** — check for an existing site. If found → return URL and skip.

3. **CreateWixBusinessGuide** — find the most appropriate Wix Studio template for the company's specific industry. Be precise — not generic.

4. **ManageWixSite** — create the site named "[Company] Demo — Wix Enterprise"

5. **CallWixSiteAPI** — deeply personalise the site. This is the most important step. Do NOT skip.

   **CMS Collections (REQUIRED):**
   - Minimum 5–8 items per collection — no placeholder entries
   - Use the company's real brand names, geography, product lines from the brief
   - Pain points from the brief addressed visibly in site structure
   - Forms configured for their actual use case

   **Apps by vertical:**
   - eCom → `1380b703-ce81-ff05-f115-39571d94dfcd`
   - Events → `140603ad-af8d-84a5-2c80-a0f60cb47351`
   - Bookings/Services → `13d21c63-b5ec-5912-8397-c3a5ddb27a97`
   - Blog → `14bcded7-0066-7c35-14d7-466cb3f09103`
   - Forms → `14ce1214-b278-a7e4-1373-00cebd1bef7c`
   - Chat → `14517e1a-3ff0-af98-408e-2bd6953c36a2`

6. Publish and return the live URL.

---

## NOTES

- Scripts location: `~/Documents/SE Tools/gong_intel/`
- Briefs: `~/Documents/SE Tools/gong_intel/Briefs/`
- Use `python3` not `python`
- 0 Gong calls = fine — note "No prior history"
- If morning_prep.py times out on data fetch, re-run with `--days 90`
- NEVER use browser automation for Wix site creation — always use Wix MCP tools only
- Read SLACK_CHANNEL_ID and SLACK_USER_ID from `~/Documents/SE Tools/gong_intel/.env`
