# src/gov_spending/demo.py
"""Quick single-agency, single-quarter pull to validate the pipeline works end to end."""
from gov_spending.download_usaspending import run

def main():
    run("National Science Foundation", "2023-07-01", "2023-09-30")

if __name__ == "__main__":
    main()