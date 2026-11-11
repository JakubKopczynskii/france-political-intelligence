"""
One-off script: import CAC40 revenue geography from CSV into the database.
Source data is derived from published company annual reports (2023).
Data is approximate — companies report geographic revenue at different granularities.

Usage:
    cd /Users/kuba/03_DEVELOPMENT/france-political-intelligence
    python3 backend/scripts/import_revenue.py
"""
import csv
import os
import sys
from datetime import datetime

# Add backend to path so we can import models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import SessionLocal
from models import Company

CSV_PATH = os.path.join(
    os.path.dirname(__file__), "../../data/cac40_revenue_geography.csv"
)

DATA_QUALITY_NOTE = (
    "Revenue geography sourced from published annual reports (2023). "
    "Figures are approximate: companies report geographic segments at varying granularities. "
    "French revenue includes Metropolitan France only unless otherwise stated. "
    "European revenue includes EU + EEA + UK unless company reports differently. "
    "Not verified against Bloomberg/Factset. Treat as indicative."
)


def run():
    db = SessionLocal()
    updated = 0
    not_found = []

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row["ticker"].strip()
            company = db.query(Company).filter(Company.ticker == ticker).first()
            if not company:
                not_found.append(ticker)
                continue

            fr = row.get("french_revenue_pct", "").strip()
            eu = row.get("european_revenue_pct", "").strip()
            gl = row.get("global_revenue_pct", "").strip()

            company.french_revenue_pct = float(fr) if fr else None
            company.european_revenue_pct = float(eu) if eu else None
            company.global_revenue_pct = float(gl) if gl else None
            company.revenue_source = row.get("source", "Annual Report 2023")
            date_str = row.get("data_as_of", "2023-12-31").strip()
            try:
                company.data_as_of = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                company.data_as_of = None
            company.is_synthetic_exposure = False
            company.data_quality_note = DATA_QUALITY_NOTE
            updated += 1

    db.commit()
    db.close()
    print(f"✓ Updated {updated} companies.")
    if not_found:
        print(f"  Tickers not found in DB: {not_found}")


if __name__ == "__main__":
    run()
