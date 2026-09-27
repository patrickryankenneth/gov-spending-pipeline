"""
USAspending.gov bulk award download.
API contract: https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/bulk_download/awards.md
"""
import requests
import time
import sys
from pathlib import Path

BASE_URL = "https://api.usaspending.gov/api/v2/bulk_download/awards/"
PACKAGE_ROOT = Path(__file__).resolve().parent          # src/gov_spending/
PROJECT_ROOT = PACKAGE_ROOT.parent.parent                # repo root
DATA_DIR = PROJECT_ROOT / "data" / "raw"

# Award type groups - split these into separate requests, don't combine
CONTRACT_TYPES = ["A", "B", "C", "D"]
IDV_TYPES = ["IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", "IDV_B_C", "IDV_C", "IDV_D", "IDV_E"]


def request_download(agency_name, toptier_name, start_date, end_date, award_types=CONTRACT_TYPES):
    payload = {
        "filters": {
            "prime_award_types": award_types,
            "date_type": "action_date",
            "date_range": {"start_date": start_date, "end_date": end_date},
            "agencies": [
                {"type": "funding", "tier": "toptier", "name": toptier_name}
            ]
        },
        "file_format": "csv"
    }
    print(f"Requesting download for {toptier_name}, {start_date} to {end_date} "
          f"({len(award_types)} award types)...")
    resp = requests.post(BASE_URL, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def poll_status(status_url, poll_interval=20, max_wait_seconds=1800, stall_after_seconds=None):
    """
    Poll until finished/failed.
    - max_wait_seconds: hard cap, raises TimeoutError if exceeded. Raised to
      1800s (30 min) — DoD-scale agencies have shown seconds_elapsed > 1000s
      on the server side before generation even finishes.
    - stall_after_seconds: DISABLED by default. USAspending's status endpoint
      returns total_rows=0 for the entire "running" phase and only reports
      the real count once status flips to "finished" -- there is no partial
      row-count signal to watch, so a rows-not-changing check can't
      distinguish "stuck" from "still working." Pass an explicit value only
      if you separately confirm the API starts reporting partial rows.
    """
    start = time.monotonic()

    while True:
        elapsed = time.monotonic() - start
        if elapsed > max_wait_seconds:
            raise TimeoutError(f"Download did not finish within {max_wait_seconds}s")

        resp = requests.get(status_url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        state = data.get("status")
        rows = data.get("total_rows")
        size = data.get("total_size")
        server_elapsed = data.get("seconds_elapsed")
        print(f"  [{elapsed:5.0f}s, server:{server_elapsed}] status: {state} ({rows or '?'} rows, {size or '?'} bytes)")

        if state == "finished":
            return data
        if state == "failed":
            raise RuntimeError(f"Download generation failed: {data}")

        if stall_after_seconds is not None:
            # only meaningful if you've confirmed partial row reporting for this endpoint
            pass

        time.sleep(poll_interval)

def download_file(file_url, dest_path, chunk_size=1 << 20):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(file_url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                f.write(chunk)
    print(f"Saved to {dest_path}")


def run(toptier_name, start_date, end_date, award_types=CONTRACT_TYPES, agency_name=None):
    result = request_download(agency_name or toptier_name, toptier_name, start_date, end_date, award_types)
    try:
        final = poll_status(result["status_url"])
    except TimeoutError as e:
        print(f"  -> giving up: {e}", file=sys.stderr)
        return None
    dest = DATA_DIR / result["file_name"]
    download_file(result["file_url"], dest)
    return dest


if __name__ == "__main__":
    # Contracts only first — fast and reliable
    run("National Science Foundation", "2023-07-01", "2023-09-30")

    # IDVs separately, since they're the slow/stall-prone ones
    # run("National Science Foundation", "2023-07-01", "2023-09-30", award_types=IDV_TYPES)
