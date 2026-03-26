# SE Morning Prep — Claude Code Project

This project automates demo prep for Lee Unger (leeu@wix.com),
Team Lead Solutions Engineering at Wix Enterprise.

When run, execute the full SE morning prep flow described below.

---

## THE FULL FLOW

### STEP 1 — Find External Meetings

Call `gcal_list_events` with:
- timeMin = now
- timeMax = now + 48 hours
- condenseEventDetails: false

An EXTERNAL meeting has ALL of:
- At least one @wix.com attendee (internal) AND at least one non-@wix.com attendee (client)
- Lee's status is NOT "declined"
- NOT all-day
- Title does NOT contain: "OOO", "Focus", "Reclaim"

Extract per meeting: `domain` (from external attendee email), `company_name`, `attendees` (comma-separated names of non-@wix.com people).

If no external meetings found → fire a macOS notification:
```bash
osascript -e 'display notification "No external meetings in the next 48h — enjoy the clear schedule!" with title "🟢 SE Morning Prep" sound name "Chime"'
```
Then send to channel C0ANF28TR6F: "<@U080X2JJDBK> No external meetings in the next 48h — enjoy the clear schedule! 🟢"
Then stop.

---

### STEP 2 — For Each External Meeting

#### 2a. Search Slack for Internal Context

Before running the script, search Slack for internal context about this company. Use `slack_search_public_and_private` with these queries (run all three):
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

#### 2b. Run morning_prep.py (data fetch phase)

```bash
cd ~/Documents/SE\ Tools/gong_intel && python3 morning_prep.py \
  --data-only \
  --domain DOMAIN \
  --name "COMPANY NAME" \
  --attendees "Name1, Name2, Name3" \
  [--slack-context /tmp/slack_context_SLUG.txt]
```

This saves all raw data (web research, Gong transcripts, all Coda pages, Slack context) to `/tmp/{slug}_raw_data.json`. No API key needed.

#### 2c. Claude synthesizes the brief (native — no API key)

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

#### 2d. Render the brief (Python)

```bash
cd ~/Documents/SE\ Tools/gong_intel && python3 morning_prep.py \
  --from-brief /tmp/{slug}_brief.json \
  --domain DOMAIN \
  --name "COMPANY NAME" \
  --attendees "Name1, Name2, Name3"
```

This renders the HTML brief and saves `{slug}_site_request.json` to `~/Documents/SE Tools/gong_intel/Briefs/`.

Note the brief HTML path from `[Done] Brief saved to: ...`

#### 2c. Verify Coda Demo Script

Read the generated HTML brief. If "Personalized Demo Script" section is MISSING:
- Note this in the Slack message so Lee knows to pull Coda guides manually

---

### STEP 3 — macOS Notification + Slack

First, fire a macOS notification so Lee gets an immediate alert (this works regardless of Slack settings):

```bash
osascript -e 'display notification "Your SE briefs are ready — check Slack for details." with title "🌅 SE Morning Prep Complete" sound name "Chime"'
```

Then send a Slack message to channel C0ANF28TR6F (NOT a DM — this channel triggers a real notification):

```
<@U080X2JJDBK> 🌅 *Good morning! Here's your SE prep for the next 48h:*

*1. [Company Name]* — [Meeting time, e.g. "Wed Mar 25 at 2:00 PM IST"]
📋 Brief: [brief filename]
🎯 Focus: [recommended_focus from brief — read from site_request.json]
👥 Attendees: [names]
📞 Gong: [X calls found / No prior history]
🗂️ Verticals: [selected_verticals from site_request.json]
📬 Slack: [✅ Internal context found / No internal mentions]
📊 Coda: [✅ Demo script included / ⚠️ Pull manually]

[Repeat block for each meeting]

---
🌐 *Want a Wix demo site for any of these?*
Open Claude Code in this folder and say: "Create demo site for [Company]"

_Briefs saved to: ~/Documents/SE Tools/gong_intel/Briefs/_
```

---

### STEP 4 — Wix Demo Site (only if explicitly requested)

If the user asked to create a Wix demo site (e.g. "create demo site for Dominion"):

1. Read `Briefs/{slug}_site_request.json` for all parameters:
   - company_name, domain, industry, company_summary, why_wix
   - pain_points, tech_stack, recommended_focus, selected_verticals, attendees

2. **ListWixSites** — check if a demo site already exists for this company (search by name). If found → show the URL and stop.

3. **CreateWixBusinessGuide** — find the most appropriate Wix Studio template for the company's specific industry and use case. Be precise: a mortgage brokerage network needs a financial/real estate template, not a generic business one.

4. **ManageWixSite** — create the site from the chosen template, named "[Company] Demo — Wix Enterprise"

5. **CallWixSiteAPI** — deeply personalise the site. This is the most important step — do NOT skip it or do it superficially.

   **CMS Collections (REQUIRED):** Create and populate collections with realistic, company-specific content. The content should feel like it was built FOR this specific prospect, not a generic demo. Examples by industry:
   - Mortgage/Lending: loan products, branch locations, broker profiles, calculators, application forms
   - Real estate franchise: property listings (real local addresses/prices), agent profiles, neighborhoods, open house events
   - Auto dealer network: vehicle inventory (real makes/models/prices), dealership locations, service packages, financing options
   - Florist franchise: arrangement catalog (seasonal, occasion-based), location finder, event booking, care guides
   - Use the company's actual geography, pricing tiers, brand names, and product categories wherever possible — pull from the web research in the brief

   **Apps to install** based on selected_verticals:
   - eCom → `1380b703-ce81-ff05-f115-39571d94dfcd`
   - Events → `140603ad-af8d-84a5-2c80-a0f60cb47351`
   - Bookings/Services → `13d21c63-b5ec-5912-8397-c3a5ddb27a97`
   - Blog → `14bcded7-0066-7c35-14d7-466cb3f09103`
   - Forms → `14ce1214-b278-a7e4-1373-00cebd1bef7c`
   - Chat → `14517e1a-3ff0-af98-408e-2bd6953c36a2`

   **Personalisation checklist before publishing:**
   - [ ] At least 5–8 CMS items per collection (not 1–2 placeholder entries)
   - [ ] Content uses the company's real brand names, geography, and product lines
   - [ ] Pain points from the brief are addressed visibly in the site structure
   - [ ] Forms are configured for their actual use case (lead capture, broker application, booking, etc.)

6. Publish the site and return the live URL.

---

---

## SE-PREP-FOR — Prep for a Specific Client

If the user says something like "prep for [company]", "se-prep-for", or pastes a Google Calendar URL, run this flow instead of the full morning scan.

### Input: Google Calendar URL

If the user provides a URL like:
`https://calendar.google.com/calendar/u/0/r/eventedit/N2g3MmxoMjBwaW5pYTEwNXBvaWI5bGE4bnIgbGVldUB3aXguY29t`

1. Extract the base64 segment (everything after `/eventedit/` or `?eid=`)
2. Decode it:
```bash
python3 -c "import base64; print(base64.b64decode('BASE64_SEGMENT').decode())"
```
Returns `{eventId} {calendarId}` — use the eventId (before the space) to call `gcal_get_event`

3. From the event extract: company name (from title or org), domain (from external attendee email), attendees (non-@wix.com names)

4. Confirm with the user before running:
"Got it — prepping for:
- **Company:** [name]
- **Domain:** [domain]
- **Attendees:** [names]
Running research now..."

### Input: Manual details

If the user provides company name, domain, and/or attendees directly — use those. Ask for any that are missing.

### Then: Slack search + morning_prep.py + notify

Once you have company name, domain, and attendees — run the same flow as STEP 2 and STEP 3 above:
1. Slack search → save context to `/tmp/slack_context_{slug}.txt`
2. `morning_prep.py --data-only ...` → saves `/tmp/{slug}_raw_data.json`
3. Read raw data JSON, synthesize brief natively → save `/tmp/{slug}_brief.json`
4. `morning_prep.py --from-brief /tmp/{slug}_brief.json ...` → renders HTML + site_request.json
5. macOS notification → Slack summary to C0ANF28TR6F mentioning `<@U080X2JJDBK>`

Then ask: "Would you like me to create a Wix demo site for [Company]?" and follow STEP 4 if yes.

---

## SE-PREP-ON-DEMAND — Interactive 14-Day Scan

If the user says "on demand prep" or "se-prep-on-demand", run this flow:

1. Call `gcal_list_events` with timeMin = now, timeMax = now + 14 days, condenseEventDetails: false
2. Filter for external meetings (same rules as STEP 1)
3. Present a numbered list of what was found and ask which ones to prep for
4. Wait for the user's response (they can say "all" or list numbers)
5. Run morning_prep.py for each selected meeting (same as STEP 2)
6. Send macOS notification + Slack summary to C0ANF28TR6F mentioning <@U080X2JJDBK> (same as STEP 3)
7. Ask if they want Wix demo sites for any of them (STEP 4)

---

## NOTES

- All scripts are in `~/Documents/SE Tools/gong_intel/`
- Briefs and JSON files are saved to `~/Documents/SE Tools/gong_intel/Briefs/`
- Credentials are in `.env` in the scripts folder — loaded automatically
- Use `python3` not `python`
- 0 Gong calls = fine, just a new prospect
- If morning_prep.py times out on synthesis, re-run with `--days 30`
- NEVER use browser automation for Wix site creation — always use Wix MCP tools
