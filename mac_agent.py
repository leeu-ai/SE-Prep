#!/usr/bin/env python3
"""
mac_agent.py — SE Morning Prep Mac-side agent
==============================================
Triggered by launchd (WatchPaths) the moment a job file appears in jobs/.
Runs morning_prep.py natively on your Mac for each meeting in the job file,
then writes results to results/ for the Cowork notify task to pick up.

No setup needed — just install the launchd plist and this runs automatically.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TOOLS_DIR   = Path(__file__).parent
JOBS_DIR    = TOOLS_DIR / "jobs"
RESULTS_DIR = TOOLS_DIR / "results"

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_morning_prep(meeting: dict) -> dict:
    """Run morning_prep.py for one meeting. Returns result dict."""
    company   = meeting["company_name"]
    domain    = meeting["domain"]
    attendees = meeting.get("attendees", "")

    log(f"Starting prep for: {company} ({domain})")

    cmd = [
        sys.executable,
        str(TOOLS_DIR / "morning_prep.py"),
        "--domain",    domain,
        "--name",      company,
        "--attendees", attendees,
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(TOOLS_DIR),
        timeout=600,       # 10 min max per company
        input="n\n",       # auto-answer "n" to the interactive site creation prompt
    )

    # Extract brief file path from stdout
    brief_file = None
    for line in proc.stdout.splitlines():
        if "[Done] Brief saved to:" in line:
            brief_file = line.split(":", 1)[1].strip()

    # Derive site request path
    slug = re.sub(r"[^a-z0-9]+", "_", company.lower()).strip("_")
    site_req = TOOLS_DIR / f"{slug}_site_request.json"

    success = brief_file is not None and Path(brief_file).exists()
    log(f"{'✅' if success else '❌'} {company}: brief={'saved' if success else 'FAILED'}")
    if proc.stderr:
        log(f"stderr tail: {proc.stderr[-500:]}")

    return {
        "company_name":       company,
        "domain":             domain,
        "attendees":          attendees,
        "meeting_time":       meeting.get("meeting_time", ""),
        "brief_file":         brief_file,
        "site_request_file":  str(site_req) if site_req.exists() else None,
        "success":            success,
        "error":              proc.stderr[-1000:] if not success else "",
    }


def process_jobs():
    JOBS_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)

    job_files = sorted(JOBS_DIR.glob("*.json"))
    if not job_files:
        log("No job files found — nothing to do.")
        return

    for job_file in job_files:
        log(f"Processing job file: {job_file.name}")
        try:
            with open(job_file) as f:
                job = json.load(f)
        except Exception as e:
            log(f"Could not read job file: {e}")
            continue

        meetings = job.get("meetings", [])
        log(f"Found {len(meetings)} meeting(s) to prep.")

        results = []
        for meeting in meetings:
            try:
                result = run_morning_prep(meeting)
            except subprocess.TimeoutExpired:
                log(f"Timeout for {meeting.get('company_name')}")
                result = {**meeting, "success": False, "error": "Timed out after 10 min"}
            except Exception as e:
                log(f"Error for {meeting.get('company_name')}: {e}")
                result = {**meeting, "success": False, "error": str(e)}
            results.append(result)

        # Write results file (same name as job file, in results/)
        results_file = RESULTS_DIR / job_file.name
        payload = {
            "results":      results,
            "processed_at": datetime.now().isoformat(),
            "job_file":     str(job_file),
        }
        with open(results_file, "w") as f:
            json.dump(payload, f, indent=2)
        log(f"Results written to: {results_file}")

        # Remove the job file so it isn't processed again
        job_file.unlink()
        log(f"Job file removed: {job_file.name}")

    log("All jobs processed.")


if __name__ == "__main__":
    process_jobs()
