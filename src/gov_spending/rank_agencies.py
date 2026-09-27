"""
Rank toptier agencies by total obligations so bulk_download.py can target
high-spend agencies instead of walking the list alphabetically.

Usage:
    python3 rank_agencies.py            # prints top 20 by spend
    python3 rank_agencies.py --n 15     # prints top 15

Then wire the result into bulk_download.py, e.g.:

    from rank_agencies import get_top_agencies
    top_names = get_top_agencies(n=15)
    run_bulk(start_year=2023, end_year=2023,
             agency_filter=lambda a: a["agency_name"] in top_names)
"""
import argparse
import requests

AGENCIES_URL = "https://api.usaspending.gov/api/v2/references/toptier_agencies/"


def get_top_agencies(n=20):
    """
    Returns list of agency_name strings, sorted descending by budget_authority_amount.
    The toptier_agencies endpoint already includes a rough current-year
    budgetary figure per agency, which is a reasonable proxy for spend volume
    without needing a separate call per agency.
    """
    resp = requests.get(AGENCIES_URL, timeout=30)
    resp.raise_for_status()
    agencies = resp.json()["results"]

    # field name has varied across API versions; try the common ones
    def amount(a):
        for key in ("budget_authority_amount", "obligated_amount", "current_total_budget_authority_amount"):
            if key in a and a[key] is not None:
                return float(a[key])
        return 0.0

    ranked = sorted(agencies, key=amount, reverse=True)
    return ranked[:n]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20)
    args = parser.parse_args()

    top = get_top_agencies(args.n)
    for i, a in enumerate(top, 1):
        print(f"{i:2}. {a['agency_name']}")
