"""Mirror leads into the Companies module.

Creates a CrmCompany for every lead that isn't linked to one yet (and links the
lead to it). Leads are NOT marked converted and NO deals are created — this just
makes the vendor accounts visible under Companies. Idempotent.

Usage:
    cd apps/api && PYTHONPATH=src python scripts/backfill_lead_companies.py
"""

from __future__ import annotations

from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
from porterchain_api.crm_models import CrmCompany
from porterchain_api.db import SessionLocal, init_db


def main() -> None:
    init_db()
    db = SessionLocal()
    svc = CrmSalesService()
    try:
        result = svc.backfill_companies_from_leads(db)
        total = db.query(CrmCompany).count()
        print("Backfill complete:")
        print(f"  companies created : {result['companies_created']}")
        print(f"  leads linked      : {result['leads_linked']}")
        print(f"  total companies   : {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
