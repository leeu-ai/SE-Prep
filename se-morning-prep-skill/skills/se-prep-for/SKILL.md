---
name: se-prep-for
description: "Prep for a specific client — provide either a Google Calendar event URL or manually enter company name, domain, and attendees. Searches Slack for internal context, then goes straight to research, brief generation, and Slack summary."
---

You are running targeted SE prep for a specific client. No calendar scan — go straight to research and brief generation.

## STEP 1 — Gather Parameters

**IMPORTANT: Your very first action must be to ask the user for input before reading any files or doing any research.**

The user will provide EITHER a Google Calendar event URL OR manual details. Handle both:

---

### Option A — Google Calendar URL provided

Example URL format:
`https://calendar.google.com/calendar/u/0/r/eventedit/N2g3MmxoMjBwaW5pYTEwNXBvaWI5bGE4bnIgbGVldUB3aXguY29t`

**To extract the event ID:**
1. Take the base64 segment at the end of the URL (after `/eventedit/` or `/event?eid=`)
2. Decode it with Python:
```bash
python3 -c "import base64; print(base64.b64decode('BASE64_SEGMENT').decode())"
```
This returns `{eventId} {calendarId}` — e.g. `7h72lh20pinia105poib9la8nr leeu@wix.com`

3. Use the first part (before the space) as the event ID, and call `gcal_get_event` with it to retrieve the full event.

**From the event, extract:**
- **Company name** — from the meeting title or the external attendee's organization
- **Domain** — from the external (non-@wix.com) attendee's email address
- **Attendees** — comma-separated names of non-@wix.com people

If the event has no external attendees, tell the user it doesn't look like an external meeting and ask them to confirm the details manually.

---

### Option B — Manual input

The user provides some or all of:
- Company name (e.g. "Dominion Lending Centres")
- Domain (e.g. "dominionlending.ca")
- Attendees (comma-separated names)

If any are missing, ask for them before proceeding. All three are required to run the research.

---

## STEP 2 — Confirm Before Running

Before kicking off the research, confirm the extracted/provided details with the user:

"Got it — prepping for:
- **Company:** [Company Name]
- **Domain:** [domain.com]
- **Attendees:** [Name1, Name2]

Running research now..."

---

## STEP 3 — Check for an existing brief

Before doing any research, check if a brief already exists for this company in `~/Documents/SE Tools/gong_intel/Briefs/`. Look for a file matching `{slug}_brief_*.html`.

**If a brief exists from today** → skip to STEP 7. No new research needed.

**If a brief exists from a previous day** → do a lightweight update check:
1. Search Slack for any new mentions since the brief was generated
2. If new meaningful Slack context is found (new blockers, deal updates, stakeholder changes) → re-run the full flow (steps 4 onward) and note "Updated" in the Slack message
3. If nothing new → reuse the existing brief. Note "No updates — using existing brief from [date]" in the Slack message

**If no brief exists** → run the full flow below.

---

## STEP 4 — Search Slack for Internal Context

Search Slack for internal context about this company. Use `slack_search_public_and_private` with these queries (run all three):
- `"COMPANY NAME"` — direct mentions
- `"DOMAIN"` — email domain mentions
- Names of the external attendees

Compile relevant results (deal status, blockers, internal sentiment, deadlines, action items) into a text summary. Save it to a temp file:
```bash
cat > /tmp/slack_context_SLUG.txt << 'SLACK_EOF'
[Compiled Slack findings]
SLACK_EOF
```

If no Slack results found, skip the file — morning_prep.py handles missing context gracefully.

---

## STEP 5 — Run morning_prep.py — data fetch only

```bash
cd ~/Documents/SE\ Tools/gong_intel && python3 morning_prep.py \
  --data-only \
  --domain DOMAIN \
  --name "COMPANY NAME" \
  --attendees "Name1, Name2, Name3" \
  [--slack-context /tmp/slack_context_SLUG.txt]
```

Omit `--slack-context` if no Slack results were found. This saves all raw data (web research, Gong transcripts, Coda pages, Slack context) to `/tmp/{slug}_raw_data.json`. No API key needed.

---

## STEP 6 — Synthesize the brief natively (no API key needed)

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

Then render the HTML brief:

```bash
cd ~/Documents/SE\ Tools/gong_intel && python3 morning_prep.py \
  --from-brief /tmp/{slug}_brief.json \
  --domain DOMAIN \
  --name "COMPANY NAME" \
  --attendees "Name1, Name2, Name3"
```

Note the brief path from `[Done] Brief saved to: ...`

---

## STEP 7 — Verify Coda Demo Script

Read the generated HTML brief. If the "Personalized Demo Script" section is MISSING, flag it so the user knows to pull Coda guides manually.

---

## STEP 8 — Notification + Slack Summary

Fire a macOS notification:
```bash
osascript -e 'display notification "Brief ready for COMPANY NAME — check Slack." with title "📋 SE Prep Complete" sound name "Chime"'
```

Send a Slack message to the channel in `.env` → `SLACK_CHANNEL_ID`, mentioning `SLACK_USER_ID`:

```
<@SLACK_USER_ID> 📋 *Brief ready for [Company Name]:*

🎯 Focus: [recommended_focus from site_request.json]
👥 Attendees: [names]
📞 Gong: [X calls found / No prior history]
📬 Slack: [✅ Internal context found / No internal mentions]
🗂️ Verticals: [selected_verticals from site_request.json]
📊 Coda: [✅ Demo script included / ⚠️ Pull manually]
📋 Brief: [brief filename]

_Saved to: ~/Documents/SE Tools/gong_intel/Briefs/_
```

---

## STEP 9 — Offer Wix Demo Site

Ask: "Would you like me to create a Wix demo site for [Company Name]?"

If yes:

1. Read `~/Documents/SE Tools/gong_intel/Briefs/{slug}_site_request.json`

2. **ListWixSites** — check for an existing site. If found → return URL and stop.

3. **CreateWixBusinessGuide** — find the most appropriate Wix Studio template for this company's specific industry. Be precise, not generic.

4. **ManageWixSite** — create the site named "[Company] Demo — Wix Enterprise"

5. **CallWixSiteAPI** — deeply personalise the site. Do NOT skip or do superficially.

   **CMS Collections (REQUIRED):**
   - Minimum 5–8 items per collection — no placeholder entries
   - Use the company's real brand names, geography, and product lines from the brief
   - Pain points from the brief addressed visibly in the site structure
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
