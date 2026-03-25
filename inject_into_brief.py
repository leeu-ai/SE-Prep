#!/usr/bin/env python3
"""
inject_into_brief.py — Inject Gong intelligence into a demo brief HTML file
=============================================================================
Reads Gong intel (JSON from gong_intel.py) and inserts it as a section
into an existing demo brief HTML file, right after the executive summary.

USAGE:
  # Step 1: generate the intel (saves to gong_output.json)
  python gong_intel.py --domain abiworld.com --name "AB-InBev" --output json > gong_output.json

  # Step 2: inject into brief
  python inject_into_brief.py --brief AB-InBev_Demo_Brief.html --gong gong_output.json --company "AB-InBev"

  # OR — one-liner pipeline:
  python gong_intel.py --domain abiworld.com --name "AB-InBev" --output json | \
    python inject_into_brief.py --brief AB-InBev_Demo_Brief.html --company "AB-InBev" --stdin

OUTPUT:
  Overwrites the brief file in-place (keeps a .backup copy automatically).
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime


# ── IMPORT THE RENDERER FROM gong_intel ──────────────────────────────────────
# We reuse the same HTML renderer so the style is always in sync.
sys.path.insert(0, os.path.dirname(__file__))
from gong_intel import render_html_section, find_calls_for_domain   # noqa: E402


# ── INJECTION LOGIC ───────────────────────────────────────────────────────────

# The injector looks for this marker inside the brief HTML.
# If found, it inserts the Gong section right after it.
# If not found, it inserts before </body>.
INJECT_AFTER_MARKER  = "<!-- GONG_INJECT_AFTER -->"
GONG_SECTION_OPEN    = "<!-- GONG_SECTION_START -->"
GONG_SECTION_CLOSE   = "<!-- GONG_SECTION_END -->"


def inject_or_replace(html: str, gong_html: str) -> str:
    """
    Insert (or replace) the Gong section in the brief HTML string.
    - If a previous Gong section exists, it is replaced.
    - If the INJECT_AFTER_MARKER exists, insert after it.
    - Otherwise, insert before </body>.
    """
    wrapped = f"\n{GONG_SECTION_OPEN}\n{gong_html}\n{GONG_SECTION_CLOSE}\n"

    # Case 1: replace existing Gong section
    if GONG_SECTION_OPEN in html and GONG_SECTION_CLOSE in html:
        start = html.index(GONG_SECTION_OPEN)
        end   = html.index(GONG_SECTION_CLOSE) + len(GONG_SECTION_CLOSE)
        print("[Inject] Replacing existing Gong section in brief.", file=sys.stderr)
        return html[:start] + wrapped + html[end:]

    # Case 2: inject after explicit marker
    if INJECT_AFTER_MARKER in html:
        print(f"[Inject] Inserting after marker: {INJECT_AFTER_MARKER}", file=sys.stderr)
        return html.replace(INJECT_AFTER_MARKER, INJECT_AFTER_MARKER + wrapped, 1)

    # Case 3: insert before </body>
    if "</body>" in html.lower():
        idx = html.lower().index("</body>")
        print("[Inject] Inserting before </body>.", file=sys.stderr)
        return html[:idx] + wrapped + html[idx:]

    # Fallback: append
    print("[Inject] Appending to end of file.", file=sys.stderr)
    return html + wrapped


def backup_file(path: str) -> str:
    """Create a timestamped backup before modifying."""
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup  = f"{path}.{ts}.backup"
    shutil.copy2(path, backup)
    print(f"[Inject] Backup saved: {backup}", file=sys.stderr)
    return backup


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Inject Gong intel HTML into a demo brief file"
    )
    parser.add_argument("--brief",   required=True,  help="Path to the demo brief HTML file")
    parser.add_argument("--company", required=True,  help="Company display name (for HTML heading)")
    parser.add_argument("--gong",    default=None,   help="Path to gong_intel.py JSON output file")
    parser.add_argument("--stdin",   action="store_true",
                        help="Read Gong JSON from stdin instead of a file")
    parser.add_argument("--domain",  default=None,
                        help="If provided, re-run Gong lookup on the fly (needs env vars set)")
    parser.add_argument("--days",    type=int, default=90)
    args = parser.parse_args()

    # ── 1. Load Gong intel ──────────────────────────────────────────────────
    intel = None
    calls = []

    if args.stdin:
        print("[Inject] Reading Gong JSON from stdin...", file=sys.stderr)
        raw   = sys.stdin.read()
        intel = json.loads(raw)

    elif args.gong:
        print(f"[Inject] Loading Gong JSON from {args.gong}...", file=sys.stderr)
        with open(args.gong) as f:
            intel = json.load(f)

    elif args.domain:
        print(f"[Inject] Running live Gong lookup for {args.domain}...", file=sys.stderr)
        from gong_intel import find_calls_for_domain, get_transcripts, summarize_with_claude
        calls = find_calls_for_domain(args.domain, args.days)
        if not calls:
            print(f"[Inject] No Gong calls found for {args.domain}. Brief unchanged.", file=sys.stderr)
            sys.exit(0)
        call_ids    = [c["metaData"]["id"] for c in calls if "metaData" in c]
        transcripts = get_transcripts(call_ids)
        for call in calls:
            call["_transcript"] = transcripts.get(call.get("metaData", {}).get("id", ""), "")
        intel = summarize_with_claude(args.company, calls)

    if not intel:
        print("[Inject] No intel to inject. Exiting.", file=sys.stderr)
        sys.exit(1)

    # ── 2. Render HTML section ──────────────────────────────────────────────
    gong_html = render_html_section(args.company, intel, calls)

    # ── 3. Load brief, inject, save ─────────────────────────────────────────
    if not os.path.exists(args.brief):
        print(f"[Inject] Brief file not found: {args.brief}", file=sys.stderr)
        sys.exit(1)

    with open(args.brief, "r", encoding="utf-8") as f:
        original_html = f.read()

    backup_file(args.brief)
    updated_html = inject_or_replace(original_html, gong_html)

    with open(args.brief, "w", encoding="utf-8") as f:
        f.write(updated_html)

    print(f"[Inject] ✅ Done. Gong section injected into: {args.brief}", file=sys.stderr)


if __name__ == "__main__":
    main()
