"""
Bulk USAspending download: loops over toptier agencies x year-quarters.
Resumable (skips files already on disk) and rate-limited to be polite to the API.

Run: gov-spending-bulk
(after `pip install -e .` from the repo root)
"""
import json
import time
from pathlib import Path

import requests

from .download_usaspending import request_download, poll_status, download_file, DATA_DIR, CONTRACT_TYPES
from .rank_agencies import get_top_agencies

AGENCIES_URL = "https://api.usaspending.gov/api/v2/references/toptier_agencies/"
MANIFEST_PATH = DATA_DIR / "_manifest.json"

# Politeness delay between *new* download requests (not polls -- poll_status
# already paces itself). USAspending doesn't publish a hard rate limit, but
# hammering the generator endpoint back-to-back for 100+ agencies is a good
# way to get throttled or start seeing stalled generations.
REQUEST_DELAY_SECONDS = 5


def get_toptier_agencies():
    resp = requests.get(AGENCIES_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # response is {"results": [...]}
    return data["results"]


def year_quarters(start_year, end_year):
    """Yield (start_date, end_date) strings for each quarter in range, inclusive."""
    quarters = [
        ("01-01", "03-31"),
        ("04-01", "06-30"),
        ("07-01", "09-30"),
        ("10-01", "12-31"),
    ]
    for year in range(start_year, end_year + 1):
        for q_start, q_end in quarters:
            yield f"{year}-{q_start}", f"{year}-{q_end}"


def load_manifest():
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest):
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def run_bulk(start_year, end_year, agency_filter=None, limit_agencies=None):
    """
    agency_filter: optional callable(agency_dict) -> bool to skip agencies
                   (e.g. lambda a: a["toptier_code"] in {"012","075"} for a
                   curated subset instead of all ~100+).
    limit_agencies: optional int cap, useful for a first test run.
    """
    manifest = load_manifest()
    agencies = get_toptier_agencies()
    if agency_filter:
        agencies = [a for a in agencies if agency_filter(a)]
    if limit_agencies:
        agencies = agencies[:limit_agencies]

    print(f"Bulk run: {len(agencies)} agencies x {end_year - start_year + 1} years "
          f"x 4 quarters = {len(agencies) * (end_year - start_year + 1) * 4} potential downloads")

    for agency in agencies:
        toptier_name = agency["agency_name"]
        for start_date, end_date in year_quarters(start_year, end_year):
            key = f"{toptier_name}|{start_date}|{end_date}"
            if key in manifest and manifest[key].get("status") == "ok":
                print(f"skip (already done): {key}")
                continue

            try:
                result = request_download(toptier_name, toptier_name, start_date, end_date, CONTRACT_TYPES)
                final = poll_status(result["status_url"])
                dest = DATA_DIR / result["file_name"]
                download_file(result["file_url"], dest)
                manifest[key] = {
                    "status": "ok",
                    "file": dest.name,
                    "rows": final.get("total_rows"),
                }
            except Exception as e:
                print(f"  FAILED {key}: {e}")
                manifest[key] = {"status": "failed", "error": str(e)}

            save_manifest(manifest)  # save after every attempt, so a crash doesn't lose progress
            time.sleep(REQUEST_DELAY_SECONDS)

    print("Done. See manifest at", MANIFEST_PATH)


def main():
    # Target the top N agencies by budget authority instead of walking the
    # list alphabetically -- avoids burning requests on near-dormant boards
    # and commissions with 0-14 rows/quarter.
    top = get_top_agencies(n=20)
    top_names = {a["agency_name"] for a in top}

    # Start with one year on the top 20 to sanity-check volume/timing first:
    run_bulk(start_year=2023, end_year=2023,
             agency_filter=lambda a: a["agency_name"] in top_names)

    # Once that looks right, widen the year range for the real pull, e.g.:
    # run_bulk(start_year=2019, end_year=2024,
    #          agency_filter=lambda a: a["agency_name"] in top_names)


if __name__ == "__main__":
    main()
