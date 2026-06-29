"""Import vendors.csv (repo root) as CRM leads.

Maps vendor records to logistics merchant-acquisition leads with a structured
address. Idempotent: existing leads (matched by company name) are skipped.

Usage:
    cd apps/api && PYTHONPATH=src python scripts/import_vendors.py [path/to/vendors.csv]
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from porterchain_api.admin_engine.crm_sales_service import CrmSalesService, province_from_postal
from porterchain_api.crm_models import CrmLead
from porterchain_api.db import SessionLocal, init_db

DEFAULT_CSV = Path(__file__).resolve().parents[3] / "vendors.csv"
SOURCE = "vendor_import"
BATCH = 500


def build_address(row: dict[str, str]) -> dict[str, str]:
    address: dict[str, str] = {}
    if (street := (row.get("address") or "").strip()):
        address["street"] = street
    if (city := (row.get("city") or "").strip()):
        address["city"] = city.title()
    postal = (row.get("postal_code") or "").strip()
    if postal:
        address["postal_code"] = postal
    if (province := province_from_postal(postal)):
        address["province"] = province
    if address:
        address["country"] = "Canada"
    return address


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    init_db()
    db = SessionLocal()
    svc = CrmSalesService()
    try:
        existing = {
            name.lower()
            for (name,) in db.query(CrmLead.company_name).all()
            if name
        }
        seen_in_file: set[str] = set()

        imported = 0
        skipped = 0
        blank = 0
        pending: list[CrmLead] = []

        with csv_path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = (row.get("vendor_name") or "").strip()
                if not name:
                    blank += 1
                    continue
                key = name.lower()
                if key in existing or key in seen_in_file:
                    skipped += 1
                    continue
                seen_in_file.add(key)

                address = build_address(row)
                lead = CrmLead(
                    company_name=name,
                    source=SOURCE,
                    status="new",
                    priority="medium",
                    phone=(row.get("phone") or "").strip() or None,
                    address=address,
                    service_area=address.get("city"),
                    tags=["vendor_import"],
                )
                lead.lead_score = svc.score_lead(lead)
                pending.append(lead)
                imported += 1

                if len(pending) >= BATCH:
                    db.bulk_save_objects(pending)
                    db.commit()
                    pending.clear()
                    print(f"  …committed {imported} leads")

        if pending:
            db.bulk_save_objects(pending)
            db.commit()

        total = db.query(CrmLead).count()
        print("Vendor import complete:")
        print(f"  imported : {imported}")
        print(f"  skipped  : {skipped} (duplicate company names)")
        print(f"  blank    : {blank} (no vendor name)")
        print(f"  total leads in CRM: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
