#!/usr/bin/env python3
"""
morning_prep.py — SE Demo Prep: Web Research + Gong Intel → Enriched Brief
============================================================================
Researches a company and its attendees from the web, pulls Gong call history,
then synthesizes everything into a single HTML demo brief via Claude.

SETUP (one-time):
  pip3 install requests python-dotenv duckduckgo-search

USAGE (on-demand):
  python3 morning_prep.py \\
    --domain broadridge.com \\
    --name "Broadridge Financial" \\
    --attendees "Jill Beglin, Karen Montagna, Shawn MacEwen"

OUTPUT:
  Saves Broadridge_Financial_Brief_2026-03-25.html to the same folder.
  Prints path to stdout when done.
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Load credentials ──────────────────────────────────────────────────────────
load_dotenv()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CODA_API_TOKEN    = os.environ.get("CODA_API_TOKEN", "")
# Coda URL format: https://coda.io/d/[slug]_d[docId]
# Strip leading 'd' if user pasted the full URL suffix (e.g. dHAjz6ieZVT → HAjz6ieZVT)
_raw_doc_id = os.environ.get("CODA_DOC_ID", "HAjz6ieZVT")
CODA_DOC_ID = _raw_doc_id[1:] if _raw_doc_id.startswith("d") and len(_raw_doc_id) > 8 else _raw_doc_id
OUTPUT_DIR = Path(__file__).parent / "Briefs"
OUTPUT_DIR.mkdir(exist_ok=True)  # create Briefs/ if it doesn't exist yet


# ── WEB RESEARCH ──────────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo. Returns list of {title, href, body} dicts."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except ImportError:
        print("[Web] duckduckgo-search not installed. Run: pip3 install duckduckgo-search",
              file=sys.stderr)
        return []
    except Exception as e:
        print(f"[Web] Search error: {e}", file=sys.stderr)
        return []


def format_results(results: list[dict]) -> str:
    """Convert search results to a readable text block."""
    lines = []
    for r in results:
        lines.append(f"• {r.get('title', '')}")
        body = r.get('body', '').strip()
        if body:
            lines.append(f"  {body[:300]}")
    return "\n".join(lines)


def research_company(company_name: str, domain: str) -> str:
    print(f"[Web] Researching {company_name}...", file=sys.stderr)
    overview  = web_search(f"{company_name} company overview what they do industry size employees")
    tech      = web_search(f"{company_name} technology platform tech stack website CMS")
    news      = web_search(f"{company_name} news 2025 2026")

    return (
        f"=== COMPANY OVERVIEW: {company_name} ({domain}) ===\n"
        f"{format_results(overview)}\n\n"
        f"=== TECHNOLOGY / PLATFORM ===\n"
        f"{format_results(tech)}\n\n"
        f"=== RECENT NEWS ===\n"
        f"{format_results(news)}\n"
    )


def research_attendee(name: str, company: str) -> str:
    print(f"[Web] Researching attendee: {name}...", file=sys.stderr)
    results = web_search(f'"{name}" {company} role title background', max_results=4)
    return (
        f"=== ATTENDEE: {name} @ {company} ===\n"
        f"{format_results(results)}\n"
    )


# ── CODA DEMO GUIDES ─────────────────────────────────────────────────────────

# All known verticals in the SE Knowledge Base
ALL_VERTICALS = [
    "Classic Editor", "AI Site Chat", "Wix Vibe", "Wixel", "Studio Editor",
    "eCom", "Events", "Services", "Blogs", "SEO", "Forms", "Blocks", "CMS", "Velo"
]

# Aliases for fuzzy page matching — maps vertical name to extra search terms
VERTICAL_ALIASES = {
    "velo": ["velo", "dev mode", "developer", "code"],
    "forms": ["forms", "form", "contact form", "submissions"],
    "cms": ["cms", "content management", "data collection", "collection", "database"],
    "ecom": ["ecom", "e-commerce", "store", "shop", "wix stores"],
    "blogs": ["blog", "blogs"],
    "events": ["events", "event", "wix events", "bookings"],
    "services": ["services", "service", "bookings", "wix bookings"],
    "seo": ["seo", "search engine"],
    "blocks": ["blocks", "app market", "wix blocks"],
    "studio editor": ["studio editor", "studio", "editor"],
    "classic editor": ["classic editor", "classic", "adi"],
    "ai site chat": ["ai site chat", "ai chat", "chat", "site chat"],
    "wix vibe": ["vibe", "wix vibe"],
    "wixel": ["wixel"],
}


def determine_relevant_verticals(company_name: str, company_research: str,
                                  gong_intel: dict | None) -> list[str]:
    """Ask Claude which verticals are most relevant for this prospect."""
    gong_context = ""
    if gong_intel:
        products = ", ".join(gong_intel.get("products_discussed", []))
        pains    = "; ".join(gong_intel.get("pain_points", [])[:3])
        gong_context = f"\nProducts discussed in Gong calls: {products}\nKey pain points: {pains}"

    prompt = f"""You are a Wix SE analyst. Based on this prospect info, choose the 3-4 most relevant Wix product verticals to demo.

COMPANY: {company_name}
RESEARCH SUMMARY: {company_research[:1500]}
{gong_context}

AVAILABLE VERTICALS: {', '.join(ALL_VERTICALS)}

Return ONLY a valid JSON array of vertical names from the list above.
Example: ["Studio Editor", "CMS", "Velo", "Forms"]
Choose the verticals that most directly address their use case and pain points."""

    headers = {"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    body = {"model": "claude-sonnet-4-6", "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]}

    try:
        resp = requests.post("https://api.anthropic.com/v1/messages",
                             headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        raw = resp.json()["content"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        verticals = json.loads(raw.strip())
        print(f"[Coda] Relevant verticals: {verticals}", file=sys.stderr)
        return verticals
    except Exception as e:
        print(f"[Claude] Could not determine verticals: {e} — using defaults.", file=sys.stderr)
        return ["Studio Editor", "CMS", "Forms"]


def coda_export_page(doc_id: str, page_id: str, api_token: str) -> str:
    """Export a Coda page as markdown. Polls until complete."""
    import time
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}

    resp = requests.post(
        f"https://coda.io/apis/v1/docs/{doc_id}/pages/{page_id}/export",
        headers=headers, json={"outputFormat": "markdown"}, timeout=15
    )
    if not resp.ok:
        print(f"[Coda] Export request failed: {resp.status_code}", file=sys.stderr)
        return ""

    request_id = resp.json().get("id", "")
    if not request_id:
        return ""

    for _ in range(15):
        time.sleep(3)
        poll = requests.get(
            f"https://coda.io/apis/v1/docs/{doc_id}/pages/{page_id}/export/{request_id}",
            headers={"Authorization": f"Bearer {api_token}"}, timeout=15
        )
        if poll.ok:
            data = poll.json()
            if data.get("status") == "complete":
                download_url = data.get("downloadLink", "")
                if download_url:
                    return requests.get(download_url, timeout=15).text
            elif data.get("status") == "failed":
                print(f"[Coda] Export failed for page {page_id}", file=sys.stderr)
                return ""
    print(f"[Coda] Export timed out for page {page_id}", file=sys.stderr)
    return ""


def pull_coda_demo_guides(verticals: list[str]) -> str:
    """
    Fetch demo guide content from the Coda SE Knowledge Base for the given verticals.
    Returns concatenated markdown content.
    """
    if not CODA_API_TOKEN:
        print("[Coda] No CODA_API_TOKEN set — skipping demo guides.", file=sys.stderr)
        return ""

    headers = {"Authorization": f"Bearer {CODA_API_TOKEN}"}

    # List all pages — try current CODA_DOC_ID, then fallback with/without 'd' prefix
    doc_ids_to_try = [CODA_DOC_ID]
    if CODA_DOC_ID.startswith("d"):
        doc_ids_to_try.append(CODA_DOC_ID[1:])   # without 'd'
    else:
        doc_ids_to_try.append("d" + CODA_DOC_ID)  # with 'd'

    resp = None
    used_doc_id = CODA_DOC_ID
    for doc_id_attempt in doc_ids_to_try:
        r = requests.get(
            f"https://coda.io/apis/v1/docs/{doc_id_attempt}/pages?limit=100",
            headers=headers, timeout=15
        )
        print(f"[Coda] Trying doc ID '{doc_id_attempt}' → {r.status_code}", file=sys.stderr)
        if r.ok:
            resp = r
            used_doc_id = doc_id_attempt
            break

    if resp is None or not resp.ok:
        print(f"[Coda] Could not list pages after all attempts. "
              f"Check CODA_API_TOKEN and CODA_DOC_ID.", file=sys.stderr)
        return ""

    # Paginate through all pages (Coda default limit is 25, max 100)
    pages = []
    page_data = resp.json()
    pages.extend(page_data.get("items", []))
    while page_data.get("nextPageToken"):
        next_token = page_data["nextPageToken"]
        r2 = requests.get(
            f"https://coda.io/apis/v1/docs/{used_doc_id}/pages?limit=100&pageToken={next_token}",
            headers=headers, timeout=15
        )
        if not r2.ok:
            break
        page_data = r2.json()
        pages.extend(page_data.get("items", []))

    print(f"[Coda] Total pages found: {len(pages)}", file=sys.stderr)

    # Sort pages alphabetically so matching is deterministic regardless of API return order
    pages.sort(key=lambda p: p["name"].lower())

    # Build lookup structures
    # parent_id → [child pages]
    parent_map: dict[str, list] = {}
    # name.lower() → page_id
    name_to_id: dict[str, str] = {}
    id_to_name: dict[str, str] = {}

    for page in pages:
        name_to_id[page["name"].lower()] = page["id"]
        id_to_name[page["id"]] = page["name"]
        parent_id = page.get("parent", {}).get("id") if page.get("parent") else None
        if parent_id:
            parent_map.setdefault(parent_id, []).append(page)

    content_parts = []
    for vertical in verticals:
        v_lower = vertical.lower()
        search_terms = VERTICAL_ALIASES.get(v_lower, [v_lower])

        # Find the vertical's parent page (fuzzy match with aliases).
        # Collect all matches and prefer the most specific one (shortest name)
        # so that e.g. "CMS" beats "CMS + Velo — Help Center" when searching for "cms".
        parent_id = None
        best_match_name = None
        for name, pid in name_to_id.items():
            if any(term in name or name in term for term in search_terms):
                if best_match_name is None or len(name) < len(best_match_name):
                    parent_id = pid
                    best_match_name = name

        if not parent_id:
            print(f"[Coda] No page found for vertical '{vertical}'", file=sys.stderr)
            continue

        # Look for a "Demo Guide" child page under this vertical
        # Also fall back to any child page with "script", "flow", "guide", or "talking" in the name
        children = parent_map.get(parent_id, [])
        target_page = None
        for child in children:
            child_name = child["name"].lower()
            if any(kw in child_name for kw in ["demo guide", "demo", "script", "guide", "flow", "talking point"]):
                target_page = child
                break

        if not target_page:
            target_page = {"id": parent_id, "name": vertical}

        print(f"[Coda] Fetching: {vertical} → {target_page['name']} ({target_page['id']})",
              file=sys.stderr)
        content = coda_export_page(used_doc_id, target_page["id"], CODA_API_TOKEN)
        if content:
            content_parts.append(f"=== DEMO GUIDE: {vertical.upper()} ===\n{content[:4000]}")
        else:
            print(f"[Coda] No content returned for {vertical}", file=sys.stderr)

    result = "\n\n".join(content_parts)
    if result:
        print(f"[Coda] Retrieved {len(content_parts)} demo guide(s).", file=sys.stderr)
    return result


# ── GONG INTEL ────────────────────────────────────────────────────────────────

def load_gong_functions():
    """Dynamically import Gong functions from gong_intel.py."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gong_intel", Path(__file__).parent / "gong_intel.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pull_gong_intel(domain: str, days: int = 90) -> tuple[list, dict]:
    """Returns (calls_list, intel_dict). intel_dict is None if no calls found."""
    ACCESS_KEY        = os.environ.get("GONG_ACCESS_KEY", "")
    ACCESS_KEY_SECRET = os.environ.get("GONG_ACCESS_KEY_SECRET", "")
    if not ACCESS_KEY or not ACCESS_KEY_SECRET:
        print("[Gong] No credentials found — skipping Gong intel.", file=sys.stderr)
        return [], None

    try:
        gi = load_gong_functions()
        calls = gi.find_calls_for_domain(domain, days_back=days)
        if not calls:
            print("[Gong] No calls found for this domain.", file=sys.stderr)
            return [], None

        call_ids = [c["metaData"]["id"] for c in calls if "metaData" in c]
        transcripts = gi.get_transcripts(call_ids)
        for call in calls:
            cid = call.get("metaData", {}).get("id", "")
            call["_transcript"] = transcripts.get(cid, "")

        intel = gi.summarize_with_claude(domain, calls)
        return calls, intel
    except Exception as e:
        print(f"[Gong] Error: {e}", file=sys.stderr)
        return [], None


# ── CLAUDE: SYNTHESIZE EVERYTHING ────────────────────────────────────────────

def synthesize_brief(
    company_name: str,
    domain: str,
    attendees: list[str],
    company_research: str,
    attendee_research: str,
    gong_intel: dict | None,
    calls: list,
    coda_content: str = "",
    selected_verticals: list | None = None,
) -> dict:
    """
    Ask Claude to synthesize web research + Gong intel + Coda demo guides into a
    structured brief JSON. Returns a dict with sections the HTML renderer uses.
    """
    gong_block = ""
    if gong_intel:
        gong_block = f"""
=== GONG CALL HISTORY ({len(calls)} calls) ===
Last interaction: {gong_intel.get('last_interaction', 'N/A')}
Products discussed: {', '.join(gong_intel.get('products_discussed', []))}
Pain points: {json.dumps(gong_intel.get('pain_points', []), indent=2)}
Open questions: {json.dumps(gong_intel.get('open_questions', []), indent=2)}
Key quotes: {json.dumps(gong_intel.get('key_quotes', []), indent=2)}
Gong summary: {gong_intel.get('summary', '')}
Gong recommended focus: {gong_intel.get('recommended_focus', '')}
"""
    else:
        gong_block = "=== GONG CALL HISTORY ===\nNo previous calls found for this company.\n"

    coda_block = ""
    if coda_content:
        verticals_str = ", ".join(selected_verticals) if selected_verticals else "selected verticals"
        coda_block = f"""
=== CODA DEMO GUIDES ({verticals_str}) ===
Use the following demo guide content to generate a personalized demo script tailored to this prospect.
Each guide below is for a specific Wix vertical. Extract the most relevant talking points, key features
to highlight, and discovery questions that fit this company's context.

{coda_content[:6000]}
"""

    # Trim inputs to keep prompt within a manageable size
    company_research_trimmed  = company_research[:2500]
    attendee_research_trimmed = attendee_research[:1500]

    prompt = f"""You are a Wix Solutions Engineering analyst preparing a pre-meeting brief.
Company: {company_name} ({domain})
Attendees: {', '.join(attendees) if attendees else 'Unknown'}
Meeting date: {datetime.now().strftime('%B %d, %Y')}

Below is research from the web, Gong call history, and Coda demo guides for the relevant Wix verticals.
Synthesize everything into a structured pre-meeting brief.

{company_research_trimmed}

{attendee_research_trimmed}

{gong_block}
{coda_block}

Return ONLY a valid JSON object (no markdown, no extra text) with exactly these fields:
{{
  "company_summary": "2-3 sentence overview of what the company does, their scale, and why they matter as a prospect",
  "industry": "Industry category",
  "company_size": "Estimated headcount or revenue band if found",
  "tech_stack": ["known or inferred technologies they use"],
  "why_wix": "1-2 sentences on why they are evaluating Wix / what problem Wix solves for them",
  "attendees": [
    {{
      "name": "Full Name",
      "title": "Inferred or known title",
      "background": "1-2 sentence background and what to know before meeting them",
      "talk_to": "One specific thing to say or ask this person"
    }}
  ],
  "pain_points": ["pain point 1", "pain point 2"],
  "open_questions": ["question 1", "question 2"],
  "key_quotes": ["quote 1", "quote 2"],
  "recommended_focus": "2-3 sentence specific recommendation for what to demo and how to frame the meeting",
  "demo_script": [
    {{
      "vertical": "Vertical name (e.g. Studio Editor)",
      "headline": "One-line hook tailored to this prospect",
      "key_features": ["Feature 1 relevant to them", "Feature 2"],
      "talking_points": ["Specific talking point 1", "Specific talking point 2", "Specific talking point 3"],
      "discovery_questions": ["Question to ask the prospect 1", "Question 2"]
    }}
  ],
  "agenda": [
    {{"title": "Agenda item title", "duration": "X min", "notes": "What to cover and why"}}
  ],
  "has_gong_history": {str(bool(gong_intel)).lower()},
  "has_coda_guides": {str(bool(coda_content)).lower()},
  "selected_verticals": {json.dumps(selected_verticals or [])},
  "gong_last_interaction": "{gong_intel.get('last_interaction', '') if gong_intel else ''}",
  "gong_call_count": {len(calls)}
}}"""

    headers = {
        "x-api-key":         ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    body = {
        "model":      "claude-sonnet-4-6",
        "max_tokens": 8192,
        "messages":   [{"role": "user", "content": prompt}],
    }

    print("[Claude] Synthesizing brief...", file=sys.stderr)
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers, json=body, timeout=180
        )
        resp.raise_for_status()
        raw = resp.json()["content"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[Claude] Error: {e}", file=sys.stderr)
        return None


# ── HTML RENDERER ─────────────────────────────────────────────────────────────

def render_brief_html(
    company_name: str,
    domain: str,
    brief: dict,
    gong_intel: dict | None,
    calls: list,
) -> str:
    today = datetime.now().strftime("%B %d, %Y")

    # Attendee cards
    attendee_html = ""
    for a in brief.get("attendees", []):
        initials = "".join(p[0].upper() for p in a.get("name", "?").split()[:2])
        attendee_html += f"""
        <div class="stakeholder">
          <div class="avatar">{initials}</div>
          <div class="info">
            <div class="name">{a.get('name', '')}</div>
            <div class="role">{a.get('title', '')}</div>
            <div class="note">{a.get('background', '')}</div>
            <div class="talk-to">💬 <strong>Talk to:</strong> {a.get('talk_to', '')}</div>
          </div>
        </div>"""

    # Pain points, open questions
    def make_ul(items):
        return "".join(f"<li>{i}</li>" for i in items) if items else "<li>None identified</li>"

    # Agenda
    agenda_html = ""
    for i, item in enumerate(brief.get("agenda", []), 1):
        agenda_html += f"""
        <div class="agenda-item">
          <div class="agenda-num">{i}</div>
          <div class="agenda-content">
            <div class="agenda-title">{item.get('title', '')} <span class="dur">{item.get('duration', '')}</span></div>
            <div class="agenda-desc">{item.get('notes', '')}</div>
          </div>
        </div>"""

    # Tech stack chips
    tech_chips = "".join(
        f'<span class="chip">{t}</span>'
        for t in brief.get("tech_stack", [])
    )

    # Demo Script section (from Coda)
    demo_script_html = ""
    demo_script_items = brief.get("demo_script", [])
    if demo_script_items:
        blocks = []
        for ds in demo_script_items:
            features_li = "".join(f"<li>{f}</li>" for f in ds.get("key_features", []))
            talking_li  = "".join(f"<li>{t}</li>" for t in ds.get("talking_points", []))
            questions_li = "".join(f"<li>{q}</li>" for q in ds.get("discovery_questions", []))
            blocks.append(f"""
        <div class="demo-script-block">
          <div class="demo-script-header">
            <div>
              <div class="demo-script-vertical">{ds.get('vertical', '')}</div>
              <div class="demo-script-headline">{ds.get('headline', '')}</div>
            </div>
          </div>
          <div class="demo-script-body">
            {'<div class="demo-script-section"><div class="demo-script-label">Key Features to Show</div><ul>' + features_li + '</ul></div>' if features_li else ''}
            {'<div class="demo-script-section"><div class="demo-script-label">Talking Points</div><ul>' + talking_li + '</ul></div>' if talking_li else ''}
            {'<div class="demo-script-section"><div class="demo-script-label">Discovery Questions</div><ul class="questions">' + questions_li + '</ul></div>' if questions_li else ''}
          </div>
        </div>""")
        demo_script_html = "\n".join(blocks)

    demo_script_section = ""
    if demo_script_html:
        verticals_used = ", ".join(brief.get("selected_verticals", []))
        demo_script_section = f"""
  <div class="card">
    <h2>Personalized Demo Script <span class="coda-badge">CODA</span></h2>
    <p style="font-size:12px;color:#9AA3B2;margin-bottom:16px;">Verticals selected based on prospect research: <strong>{verticals_used}</strong></p>
    {demo_script_html}
  </div>"""

    # Gong section
    gong_section = ""
    if gong_intel:
        from gong_intel import render_html_section, GONG_CSS
        gong_section = f"<!-- GONG_INJECT_AFTER -->\n<!-- GONG_SECTION_START -->\n{render_html_section(company_name, gong_intel, calls)}\n<!-- GONG_SECTION_END -->"
    else:
        gong_section = """<!-- GONG_INJECT_AFTER -->
<div style="margin:32px 0;padding:20px 24px;background:#F4F6FA;border:1px solid #E8ECF2;border-radius:10px;font-size:14px;color:#5A6478;">
  <strong>No Gong history found</strong> — this appears to be a new prospect. No previous calls in the last 90 days.
</div>"""

    # Quotes
    quotes_html = "".join(
        f'<blockquote class="quote">"{q}"</blockquote>'
        for q in brief.get("key_quotes", [])
    )
    quotes_block = f"""
    <div class="card">
      <h2>Key Quotes</h2>
      {quotes_html}
    </div>""" if quotes_html else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Demo Brief — {company_name} | {today}</title>
  <style>
    :root {{
      --blue:#116DFF; --dark:#1A2236; --mid:#5A6478;
      --light:#F4F6FA; --border:#E8ECF2;
      --green:#18A649; --amber:#F5A623; --red:#E7321C;
    }}
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#F0F2F7; color:var(--dark); padding:32px 24px; }}
    .page {{ max-width:900px; margin:0 auto; }}
    .brief-header {{ background:var(--dark); border-radius:12px 12px 0 0; padding:28px 32px; display:flex; justify-content:space-between; align-items:flex-start; }}
    .brief-header h1 {{ font-size:24px; font-weight:800; color:#fff; }}
    .brief-header .sub {{ font-size:13px; color:#9AA3B2; margin-top:4px; }}
    .wix-badge {{ background:var(--blue); color:#fff; font-size:11px; font-weight:800; letter-spacing:.08em; padding:4px 10px; border-radius:6px; display:inline-block; }}
    .brief-header .date {{ font-size:13px; color:#9AA3B2; margin-top:6px; }}
    .meta-strip {{ background:#fff; border:1px solid var(--border); border-top:none; padding:14px 32px; display:flex; gap:32px; flex-wrap:wrap; font-size:13px; color:var(--mid); }}
    .meta-strip strong {{ color:var(--dark); }}
    .card {{ background:#fff; border:1px solid var(--border); border-top:none; padding:24px 32px; }}
    .card:last-of-type {{ border-radius:0 0 12px 12px; }}
    .card h2 {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.08em; color:#9AA3B2; margin-bottom:16px; }}
    .two-col {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; }}
    .col-label {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#9AA3B2; margin-bottom:8px; }}
    ul.bullet {{ list-style:none; padding:0; }}
    ul.bullet li {{ font-size:13px; padding:4px 0 4px 14px; position:relative; }}
    ul.bullet li::before {{ content:'›'; position:absolute; left:0; color:var(--blue); font-weight:700; }}
    .callout {{ border-radius:8px; padding:14px 18px; font-size:13.5px; line-height:1.6; margin-bottom:12px; }}
    .callout.amber {{ background:#FFF5E0; border-left:4px solid var(--amber); }}
    .callout.red {{ background:#FFF0EE; border-left:4px solid var(--red); }}
    .callout.green {{ background:#F0FAF3; border-left:4px solid var(--green); }}
    .callout-label {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; margin-bottom:4px; }}
    .callout.amber .callout-label {{ color:#6B4300; }}
    .callout.red .callout-label {{ color:#7A1A10; }}
    .callout.green .callout-label {{ color:#0D5E26; }}
    .stakeholder {{ display:flex; align-items:flex-start; gap:14px; padding:12px 0; border-bottom:1px solid var(--border); }}
    .stakeholder:last-child {{ border-bottom:none; }}
    .avatar {{ width:38px; height:38px; border-radius:50%; background:var(--blue); color:#fff; display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:700; flex-shrink:0; }}
    .stakeholder .info .name {{ font-size:14px; font-weight:600; }}
    .stakeholder .info .role {{ font-size:12px; color:var(--mid); margin-top:2px; }}
    .stakeholder .info .note {{ font-size:12px; color:var(--dark); margin-top:4px; font-style:italic; }}
    .stakeholder .info .talk-to {{ font-size:12px; color:#116DFF; margin-top:6px; }}
    .agenda-item {{ display:flex; gap:16px; align-items:flex-start; padding:12px 0; border-bottom:1px solid var(--border); }}
    .agenda-item:last-child {{ border-bottom:none; }}
    .agenda-num {{ width:28px; height:28px; border-radius:50%; background:var(--blue); color:#fff; font-size:13px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; margin-top:1px; }}
    .agenda-title {{ font-size:14px; font-weight:600; }}
    .agenda-title .dur {{ font-size:12px; color:var(--mid); font-weight:400; margin-left:6px; }}
    .agenda-desc {{ font-size:13px; color:var(--mid); margin-top:3px; line-height:1.5; }}
    .chip {{ display:inline-block; background:var(--light); border:1px solid var(--border); border-radius:20px; padding:4px 12px; font-size:12px; font-weight:500; margin:3px 3px 3px 0; }}
    .quote {{ background:var(--light); border-left:3px solid var(--blue); padding:10px 16px; margin:8px 0; font-size:13.5px; font-style:italic; border-radius:0 6px 6px 0; }}
    .web-badge {{ display:inline-block; background:#EEF4FF; border:1px solid #C0D4FF; color:var(--blue); border-radius:4px; font-size:10px; font-weight:700; padding:2px 6px; margin-left:6px; vertical-align:middle; letter-spacing:.04em; }}
    .gong-badge {{ display:inline-block; background:#FFF0EC; border:1px solid #FFCDB8; color:#FF4C00; border-radius:4px; font-size:10px; font-weight:700; padding:2px 6px; margin-left:6px; vertical-align:middle; letter-spacing:.04em; }}
    .coda-badge {{ display:inline-block; background:#F0FBF4; border:1px solid #A8E2BC; color:#1A7A3A; border-radius:4px; font-size:10px; font-weight:700; padding:2px 6px; margin-left:6px; vertical-align:middle; letter-spacing:.04em; }}
    .demo-script-block {{ border:1px solid var(--border); border-radius:8px; margin-bottom:16px; overflow:hidden; }}
    .demo-script-header {{ background:var(--light); padding:12px 18px; display:flex; align-items:center; justify-content:space-between; }}
    .demo-script-vertical {{ font-size:14px; font-weight:700; color:var(--dark); }}
    .demo-script-headline {{ font-size:13px; color:var(--mid); margin-top:3px; font-style:italic; }}
    .demo-script-body {{ padding:14px 18px; }}
    .demo-script-section {{ margin-bottom:12px; }}
    .demo-script-label {{ font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#9AA3B2; margin-bottom:6px; }}
    .demo-script-body ul {{ list-style:none; padding:0; }}
    .demo-script-body ul li {{ font-size:13px; padding:3px 0 3px 14px; position:relative; color:var(--dark); }}
    .demo-script-body ul li::before {{ content:'›'; position:absolute; left:0; color:var(--blue); font-weight:700; }}
    .demo-script-body ul.questions li::before {{ content:'?'; color:var(--amber); }}
  </style>
</head>
<body>
<div class="page">

  <div class="brief-header">
    <div>
      <h1>{company_name}</h1>
      <div class="sub">SE Demo Brief &nbsp;·&nbsp; Wix Enterprise</div>
    </div>
    <div style="text-align:right">
      <span class="wix-badge">WIX ENTERPRISE</span>
      <div class="date">{today}</div>
    </div>
  </div>

  <div class="meta-strip">
    <div>🏢 <strong>Industry:</strong> {brief.get('industry', 'N/A')}</div>
    <div>👥 <strong>Size:</strong> {brief.get('company_size', 'N/A')}</div>
    <div>🌐 <strong>Domain:</strong> {domain}</div>
    <div>📞 <strong>Gong calls:</strong> {brief.get('gong_call_count', 0)} {'(last: ' + brief.get('gong_last_interaction','') + ')' if brief.get('gong_last_interaction') else '(new prospect)'}</div>
    <div>🔍 <strong>Sources:</strong> <span class="web-badge">WEB</span>{'<span class="gong-badge">GONG</span>' if brief.get('has_gong_history') else ''}{'<span class="coda-badge">CODA</span>' if brief.get('has_coda_guides') else ''}</div>
  </div>

  <div class="card">
    <h2>Company Snapshot <span class="web-badge">WEB</span></h2>
    <p style="font-size:14px;line-height:1.7;margin-bottom:16px;">{brief.get('company_summary', '')}</p>
    <div class="two-col">
      <div>
        <div class="col-label">Why Evaluating Wix</div>
        <p style="font-size:13px;line-height:1.6;">{brief.get('why_wix', '')}</p>
      </div>
      <div>
        <div class="col-label">Known Tech Stack</div>
        {tech_chips if tech_chips else '<span style="font-size:13px;color:#9AA3B2;">Not identified</span>'}
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Recommended Focus <span class="{'gong-badge' if brief.get('has_gong_history') else 'web-badge'}">{'GONG+WEB' if brief.get('has_gong_history') else 'WEB'}</span></h2>
    <div class="callout amber">
      <div class="callout-label">🎯 SE Recommendation</div>
      {brief.get('recommended_focus', '')}
    </div>
  </div>

  <div class="card">
    <h2>Pain Points &amp; Open Questions <span class="{'gong-badge' if brief.get('has_gong_history') else 'web-badge'}">{'GONG+WEB' if brief.get('has_gong_history') else 'WEB'}</span></h2>
    <div class="two-col">
      <div>
        <div class="col-label">Pain Points</div>
        <ul class="bullet">{make_ul(brief.get('pain_points', []))}</ul>
      </div>
      <div>
        <div class="col-label">Open Questions</div>
        <ul class="bullet">{make_ul(brief.get('open_questions', []))}</ul>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Attendees <span class="web-badge">WEB</span></h2>
    {attendee_html if attendee_html else '<p style="font-size:14px;color:#9AA3B2;">No attendee details provided.</p>'}
  </div>

  <div class="card">
    <h2>Demo Agenda</h2>
    {agenda_html}
  </div>

  {demo_script_section}

  {quotes_block}

  {gong_section}

</div>
</body>
</html>"""


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SE Morning Prep: Web + Gong → Demo Brief")
    parser.add_argument("--domain",    required=True, help="Company email domain (e.g. broadridge.com)")
    parser.add_argument("--name",      required=True, help="Company display name")
    parser.add_argument("--attendees", default="",    help="Comma-separated attendee names")
    parser.add_argument("--days",      type=int, default=90, help="Gong lookback days (default: 90)")
    parser.add_argument("--output",    default="",    help="Output filename stem (auto-generated if omitted)")
    args = parser.parse_args()

    attendee_list = [a.strip() for a in args.attendees.split(",") if a.strip()]
    company_slug  = re.sub(r"[^a-z0-9]+", "_", args.name.lower()).strip("_")
    today_str     = datetime.now().strftime("%Y-%m-%d")
    out_filename  = args.output or f"{company_slug}_brief_{today_str}.html"
    out_path      = OUTPUT_DIR / out_filename

    # 1. Web research
    company_research  = research_company(args.name, args.domain)
    attendee_research = "\n".join(
        research_attendee(name, args.name) for name in attendee_list
    ) if attendee_list else ""

    # 2. Gong intel
    calls, gong_intel = pull_gong_intel(args.domain, days=args.days)

    # 3. Coda demo guides
    selected_verticals = determine_relevant_verticals(args.name, company_research, gong_intel)
    coda_content       = pull_coda_demo_guides(selected_verticals)

    # 4. Synthesize with Claude
    brief = synthesize_brief(
        company_name=args.name,
        domain=args.domain,
        attendees=attendee_list,
        company_research=company_research,
        attendee_research=attendee_research,
        gong_intel=gong_intel,
        calls=calls,
        coda_content=coda_content,
        selected_verticals=selected_verticals,
    )

    if not brief:
        print("[Error] Could not generate brief. Check your ANTHROPIC_API_KEY.", file=sys.stderr)
        sys.exit(1)

    # 5. Render HTML
    html = render_brief_html(
        company_name=args.name,
        domain=args.domain,
        brief=brief,
        gong_intel=gong_intel,
        calls=calls,
    )

    out_path.write_text(html, encoding="utf-8")
    print(f"[Done] Brief saved to: {out_path}")

    # 6. Save site request JSON (always — used by Cowork/scheduled task)
    site_request = {
        "company_name":      args.name,
        "domain":            args.domain,
        "industry":          brief.get("industry", ""),
        "company_summary":   brief.get("company_summary", ""),
        "why_wix":           brief.get("why_wix", ""),
        "pain_points":       brief.get("pain_points", []),
        "tech_stack":        brief.get("tech_stack", []),
        "recommended_focus": brief.get("recommended_focus", ""),
        "selected_verticals": brief.get("selected_verticals", selected_verticals),
        "attendees":         brief.get("attendees", []),
        "brief_file":        str(out_path),
        "generated_at":      datetime.now().isoformat(),
    }
    site_request_path = OUTPUT_DIR / f"{company_slug}_site_request.json"
    site_request_path.write_text(json.dumps(site_request, indent=2), encoding="utf-8")

    # 7. Interactive site creation prompt (only when run in a real terminal)
    if sys.stdin.isatty():
        print()
        print("─" * 60)
        print(f"  🌐  Generate a personalized Wix demo site?")
        print(f"      Company : {args.name}")
        print(f"      Industry: {brief.get('industry', 'N/A')}")
        print(f"      Verticals: {', '.join(brief.get('selected_verticals', selected_verticals))}")
        print("─" * 60)
        try:
            answer = input("  Create site? (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"

        if answer == "y":
            print()
            print(f"[Site] Site request saved to: {site_request_path}")
            print()
            print("  ✅  Open Cowork and say:")
            print(f'      "Create a Wix demo site from {site_request_path.name}"')
            print()
            print("  Claude will read the brief and build a personalised")
            print("  Wix site tailored to this prospect automatically.")
            print()
        else:
            print(f"\n[Site] Skipped. You can still trigger it later — site")
            print(f"       params saved to: {site_request_path.name}")
            print()


if __name__ == "__main__":
    main()
