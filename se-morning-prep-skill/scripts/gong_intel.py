#!/usr/bin/env python3
"""
gong_intel.py — Gong Call Intelligence for SE Demo Prep
========================================================
Pulls previous call transcripts for a company from Gong, then uses
Claude to summarize them into structured pre-meeting intelligence.

SETUP (one-time):
  1. Copy .env.template to .env and fill in your credentials
  2. pip install requests python-dotenv

USAGE:
  python gong_intel.py --domain abiworld.com --name "AB-InBev"
  python gong_intel.py --domain tesla.com --name "Tesla" --days 60

OUTPUT:
  Prints JSON to stdout. Pipe to inject_into_brief.py to insert into
  your demo brief HTML automatically.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

# ── Load credentials from .env ──────────────────────────────────────────────
load_dotenv()

ACCESS_KEY        = os.environ["GONG_ACCESS_KEY"]
ACCESS_KEY_SECRET = os.environ["GONG_ACCESS_KEY_SECRET"]
BASE_URL          = os.environ.get("GONG_BASE_URL", "https://api.gong.io")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

AUTH = (ACCESS_KEY, ACCESS_KEY_SECRET)   # requests handles Basic Auth encoding


# ── GONG API HELPERS ─────────────────────────────────────────────────────────

def gong_post(path: str, payload: dict) -> dict | None:
    """POST to the Gong API. Returns parsed JSON or None on error."""
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.post(url, json=payload, auth=AUTH, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        print(f"[Gong] HTTP {e.response.status_code} on {path}: {e.response.text[:300]}",
              file=sys.stderr)
        return None
    except Exception as e:
        print(f"[Gong] Request failed: {e}", file=sys.stderr)
        return None


def find_calls_for_domain(domain: str, days_back: int = 90, debug: bool = False) -> list[dict]:
    now = datetime.now(timezone.utc)
    from_dt = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")
    to_dt   = now.strftime("%Y-%m-%dT23:59:59Z")

    base_payload = {
        "filter": {
            "fromDateTime": from_dt,
            "toDateTime":   to_dt,
        },
        "contentSelector": {
            "exposedFields": {
                "parties": True,
                "content": {"topics": True}
            }
        }
    }

    print(f"[Gong] Searching calls from {from_dt[:10]} to {to_dt[:10]}...", file=sys.stderr)

    # Paginate through all results
    all_calls = []
    cursor = None
    page = 1
    while True:
        payload = dict(base_payload)
        if cursor:
            payload["cursor"] = cursor
        result = gong_post("/v2/calls/extensive", payload)
        if not result or "calls" not in result:
            break
        all_calls.extend(result["calls"])
        cursor = result.get("records", {}).get("cursor")
        print(f"[Gong] Page {page}: fetched {len(result['calls'])} calls (total so far: {len(all_calls)})", file=sys.stderr)
        if not cursor:
            break
        page += 1

    print(f"[Gong] Total calls fetched: {len(all_calls)}", file=sys.stderr)

    if debug:
        print("\n[DEBUG] All calls and participant emails in this date range:", file=sys.stderr)
        for call in all_calls:
            meta    = call.get("metaData", {})
            date    = meta.get("started", "")[:10]
            title   = meta.get("title", "Untitled")
            parties = call.get("parties", [])
            emails  = [p.get("emailAddress", "(no email)") for p in parties]
            print(f"  {date} | {title}", file=sys.stderr)
            for email in emails:
                print(f"           → {email}", file=sys.stderr)
        print("", file=sys.stderr)

    domain_lower = domain.lower()

    # Primary: match by email domain
    matches = [
        call for call in all_calls
        if any(domain_lower in p.get("emailAddress", "").lower()
               for p in call.get("parties", []))
    ]

    # Fallback: match by call title containing the domain (minus the TLD)
    if not matches:
        name_hint = domain_lower.split(".")[0]  # e.g. "ylopo" from "ylopo.com"
        matches = [
            call for call in all_calls
            if name_hint in call.get("metaData", {}).get("title", "").lower()
        ]
        if matches:
            print(f"[Gong] No email match — fell back to title search for '{name_hint}'.", file=sys.stderr)

    matches.sort(key=lambda c: c.get("metaData", {}).get("started", ""), reverse=True)
    top = matches[:5]

    print(f"[Gong] Found {len(top)} matching call(s) for domain '{domain}'.", file=sys.stderr)
    return top

def get_transcripts(call_ids: list[str]) -> dict[str, str]:
    """
    Pull full transcripts for a list of call IDs.
    Returns a dict of {call_id: "Speaker: text\nSpeaker: text\n..."}
    """
    if not call_ids:
        return {}

    payload = {"filter": {"callIds": call_ids}}
    result  = gong_post("/v2/calls/transcript", payload)

    if not result:
        return {}

    transcripts = {}
    for item in result.get("callTranscripts", []):
        call_id  = item["callId"]
        segments = []
        for sentence in item.get("transcript", []):
            speaker = sentence.get("speakerName", "Speaker")
            # Each sentence object has a list of sentence dicts
            for s in sentence.get("sentences", []):
                text = s.get("text", "").strip()
                if text:
                    segments.append(f"{speaker}: {text}")
        transcripts[call_id] = "\n".join(segments)

    print(f"[Gong] Transcripts retrieved for {len(transcripts)} call(s).", file=sys.stderr)
    return transcripts


# ── CLAUDE SUMMARIZATION ─────────────────────────────────────────────────────

def summarize_with_claude(company_name: str, calls: list[dict]) -> dict | None:
    """
    Feed call transcripts to Claude and get back structured SE intelligence.
    """
    if not ANTHROPIC_API_KEY:
        print("[Claude] No ANTHROPIC_API_KEY set — skipping summarization.", file=sys.stderr)
        return None

    # Build readable context block (cap transcript at 3000 chars each to stay in token budget)
    context_parts = []
    for call in calls:
        meta      = call.get("metaData", {})
        date      = meta.get("started", "")[:10]
        title     = meta.get("title", "Untitled Call")
        duration  = round(meta.get("duration", 0) / 60)
        transcript = call.get("_transcript", "No transcript available.")[:3000]
        context_parts.append(
            f"CALL: {title}\nDATE: {date}\nDURATION: {duration} min\n"
            f"TRANSCRIPT:\n{transcript}"
        )

    context_block = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are a Wix Solutions Engineering analyst. An SE is about to meet with {company_name}.
Below are transcripts from previous Gong calls with this account. Extract structured intelligence.

{context_block}

Return ONLY a valid JSON object with exactly these fields (no markdown, no extra text):
{{
  "last_interaction": "YYYY-MM-DD",
  "call_count": <integer>,
  "products_discussed": ["list of Wix products/features they've already seen or discussed"],
  "pain_points": ["specific pain points in their own words where possible"],
  "open_questions": ["unresolved questions or items they asked about"],
  "key_quotes": ["2-3 direct quotes from the prospect side (not the Wix rep)"],
  "recommended_focus": "1-2 sentence recommendation: what to prioritize in the upcoming demo",
  "summary": "3-4 sentence narrative of the account relationship and conversation history"
}}"""

    headers = {
        "x-api-key":          ANTHROPIC_API_KEY,
        "anthropic-version":  "2023-06-01",
        "content-type":       "application/json",
    }
    body = {
        "model":      "claude-sonnet-4-6",
        "max_tokens": 2048,
        "messages":   [{"role": "user", "content": prompt}],
    }

    print("[Claude] Summarizing transcripts...", file=sys.stderr)
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers, json=body, timeout=60
        )
        resp.raise_for_status()
        raw = resp.json()["content"][0]["text"].strip()
        # Strip markdown code fences if Claude wrapped the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        print("[Claude] Response was not valid JSON.", file=sys.stderr)
        print(raw, file=sys.stderr)
        return None
    except requests.HTTPError as e:
        print(f"[Claude] HTTP {e.response.status_code} error:", file=sys.stderr)
        print(e.response.text, file=sys.stderr)
        return None
    except Exception as e:
        print(f"[Claude] Error: {e}", file=sys.stderr)
        return None


# ── HTML RENDERER ─────────────────────────────────────────────────────────────

GONG_CSS = """
<style>
.gong-intel {
  margin: 32px 0;
  padding: 0;
  font-family: 'Segoe UI', system-ui, sans-serif;
}
.gong-header-bar {
  display: flex; align-items: center; gap: 12px;
  background: #1A2236; color: white;
  padding: 16px 24px; border-radius: 10px 10px 0 0;
}
.gong-header-bar h2 { font-size: 18px; font-weight: 700; margin: 0; }
.gong-header-bar .gong-logo {
  background: #FF4C00; color: white;
  border-radius: 6px; padding: 3px 8px;
  font-size: 12px; font-weight: 800; letter-spacing: 0.05em;
}
.gong-body { border: 1px solid #E8ECF2; border-top: none; border-radius: 0 0 10px 10px; }
.gong-meta {
  background: #F4F6FA; padding: 12px 24px;
  font-size: 13px; color: #5A6478;
  border-bottom: 1px solid #E8ECF2;
}
.gong-summary-block {
  padding: 16px 24px; font-size: 14px; color: #1A2236; line-height: 1.65;
  border-bottom: 1px solid #E8ECF2;
}
.gong-focus-block {
  display: flex; gap: 12px; align-items: flex-start;
  background: #FFF5E0; border-left: 4px solid #F5A623;
  padding: 14px 24px; font-size: 14px;
  border-bottom: 1px solid #E8ECF2;
}
.gong-focus-block .focus-label {
  font-weight: 700; color: #6B4300; white-space: nowrap; padding-top: 1px;
}
.gong-three-col {
  display: grid; grid-template-columns: 1fr 1fr 1fr;
  gap: 0; border-bottom: 1px solid #E8ECF2;
}
.gong-col { padding: 16px 20px; border-right: 1px solid #E8ECF2; }
.gong-col:last-child { border-right: none; }
.gong-col h4 {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: #9AA3B2; margin-bottom: 10px;
}
.gong-col ul { list-style: none; padding: 0; margin: 0; }
.gong-col ul li {
  font-size: 13px; padding: 4px 0 4px 14px; position: relative; color: #1A2236;
}
.gong-col ul li::before { content: '›'; position: absolute; left: 0; color: #116DFF; font-weight: 700; }
.gong-quotes-block { padding: 16px 24px; border-bottom: 1px solid #E8ECF2; }
.gong-quotes-block h4 {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: #9AA3B2; margin-bottom: 10px;
}
.gong-quote {
  background: #F4F6FA; border-left: 3px solid #116DFF;
  padding: 10px 16px; margin: 8px 0;
  font-size: 13.5px; font-style: italic; color: #1A2236; border-radius: 0 6px 6px 0;
}
.gong-calls-table { width: 100%; border-collapse: collapse; }
.gong-calls-table th, .gong-calls-table td {
  padding: 10px 20px; font-size: 13px; text-align: left;
  border-bottom: 1px solid #E8ECF2;
}
.gong-calls-table th { font-weight: 700; color: #9AA3B2; font-size: 11px; text-transform: uppercase; }
.gong-calls-table tr:last-child td { border-bottom: none; }
</style>
"""

def render_html_section(company_name: str, intel: dict, calls: list[dict]) -> str:
    """Render the Gong intel block as a self-contained HTML section."""

    # --- meta bar ---
    last = intel.get("last_interaction", "N/A")
    count = intel.get("call_count", len(calls))
    meta_html = f'Last interaction: <strong>{last}</strong> &nbsp;·&nbsp; <strong>{count} call(s)</strong> in Gong'

    # --- three-column lists ---
    def make_list(items):
        return "".join(f"<li>{i}</li>" for i in items) if items else "<li>None identified</li>"

    products_html  = make_list(intel.get("products_discussed", []))
    pains_html     = make_list(intel.get("pain_points", []))
    questions_html = make_list(intel.get("open_questions", []))

    # --- quotes ---
    quotes_html = ""
    for q in intel.get("key_quotes", []):
        quotes_html += f'<blockquote class="gong-quote">"{q}"</blockquote>\n'

    # --- call history table ---
    call_rows = ""
    for call in calls:
        meta     = call.get("metaData", {})
        date     = meta.get("started", "")[:10]
        title    = meta.get("title", "Untitled")
        duration = round(meta.get("duration", 0) / 60)
        call_rows += f"<tr><td>{date}</td><td>{title}</td><td>{duration} min</td></tr>\n"

    quotes_block = f"""
    <div class="gong-quotes-block">
      <h4>Key Quotes — Prospect Voice</h4>
      {quotes_html}
    </div>""" if quotes_html else ""

    return f"""
{GONG_CSS}
<div class="gong-intel">
  <div class="gong-header-bar">
    <span class="gong-logo">GONG</span>
    <h2>Call Intelligence — {company_name}</h2>
  </div>
  <div class="gong-body">
    <div class="gong-meta">{meta_html}</div>

    <div class="gong-summary-block">{intel.get("summary", "")}</div>

    <div class="gong-focus-block">
      <span class="focus-label">🎯 Recommended Focus</span>
      <span>{intel.get("recommended_focus", "")}</span>
    </div>

    <div class="gong-three-col">
      <div class="gong-col">
        <h4>Products &amp; Features Discussed</h4>
        <ul>{products_html}</ul>
      </div>
      <div class="gong-col">
        <h4>Stated Pain Points</h4>
        <ul>{pains_html}</ul>
      </div>
      <div class="gong-col">
        <h4>Open Questions</h4>
        <ul>{questions_html}</ul>
      </div>
    </div>

    {quotes_block}

    <table class="gong-calls-table">
      <thead>
        <tr><th>Date</th><th>Call Title</th><th>Duration</th></tr>
      </thead>
      <tbody>
        {call_rows}
      </tbody>
    </table>
  </div>
</div>
"""


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pull Gong call intelligence for a company")
    parser.add_argument("--domain",  required=True,  help="Company email domain (e.g. abiworld.com)")
    parser.add_argument("--name",    required=True,  help="Company display name (e.g. 'AB-InBev')")
    parser.add_argument("--days",    type=int, default=90, help="Days back to search (default: 90)")
    parser.add_argument("--output",  choices=["json", "html", "both"], default="both",
                        help="Output format (default: both)")
    parser.add_argument("--debug",   action="store_true",
                        help="Print all calls and participant emails before filtering")
    args = parser.parse_args()

    # 1. Find calls
    calls = find_calls_for_domain(args.domain, args.days, debug=args.debug)
    if not calls:
        result = {"status": "no_calls_found", "domain": args.domain}
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # 2. Pull transcripts and attach to call objects
    call_ids   = [c["metaData"]["id"] for c in calls if "metaData" in c]
    transcripts = get_transcripts(call_ids)
    for call in calls:
        cid = call.get("metaData", {}).get("id", "")
        call["_transcript"] = transcripts.get(cid, "")

    # 3. Summarize
    intel = summarize_with_claude(args.name, calls)
    if not intel:
        print("[Error] Could not generate summary. Check API keys.", file=sys.stderr)
        sys.exit(1)

    # 4. Output
    if args.output in ("json", "both"):
        print(json.dumps(intel, indent=2))

    if args.output in ("html", "both"):
        html = render_html_section(args.name, intel, calls)
        print(html)


if __name__ == "__main__":
    main()