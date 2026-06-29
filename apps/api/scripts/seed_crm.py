"""Seed demo data for the Porterchain Merchant CRM.

Idempotent: re-running will not duplicate the demo dataset.

Usage:
    cd apps/api && PYTHONPATH=src python scripts/seed_crm.py
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser
from porterchain_api.crm_models import CrmCompany
from porterchain_api.db import SessionLocal, init_db
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.crm_states import DealStage

SEED_MARKER = "Maple Leaf Distributors Inc."

REPS = [
    ("ava@porterchain.com", "Ava Thompson", AdminRole.SALES),
    ("liam@porterchain.com", "Liam Patel", AdminRole.SALES),
    ("noah@porterchain.com", "Noah Chen", AdminRole.SALES_MANAGER),
]

COMPANIES = [
    {
        "legal_name": "Maple Leaf Distributors Inc.",
        "operating_name": "Maple Leaf Distribution",
        "industry": "Wholesale & Distribution",
        "business_type": "Corporation",
        "website": "https://mapleleafdist.ca",
        "phone": "+1 416-555-0142",
        "email": "logistics@mapleleafdist.ca",
        "service_area": "Greater Toronto Area",
        "current_logistics_provider": "Purolator",
        "preferred_vehicle": "cargo_van",
        "estimated_deliveries_per_month": 1200,
        "estimated_monthly_revenue_cents": 4_800_000,
        "merchant_status": "negotiating",
        "tags": ["high-value", "gta"],
    },
    {
        "legal_name": "Northern Medical Supplies Ltd.",
        "operating_name": "Northern MedSupply",
        "industry": "Healthcare & Medical",
        "website": "https://northernmed.ca",
        "phone": "+1 905-555-0199",
        "email": "ops@northernmed.ca",
        "service_area": "Ontario",
        "current_logistics_provider": "FedEx",
        "preferred_vehicle": "refrigerated_van",
        "estimated_deliveries_per_month": 350,
        "estimated_monthly_revenue_cents": 2_100_000,
        "merchant_status": "prospect",
        "tags": ["compliance", "cold-chain"],
    },
    {
        "legal_name": "GTA Construction Materials Corp.",
        "operating_name": "GTA BuildMat",
        "industry": "Construction",
        "website": "https://gtabuildmat.ca",
        "phone": "+1 647-555-0177",
        "email": "dispatch@gtabuildmat.ca",
        "service_area": "Toronto, Mississauga, Brampton",
        "preferred_vehicle": "flatbed",
        "estimated_deliveries_per_month": 600,
        "estimated_monthly_revenue_cents": 3_300_000,
        "merchant_status": "prospect",
        "tags": ["heavy-freight"],
    },
    {
        "legal_name": "Riverside Coffee Roasters",
        "operating_name": "Riverside Coffee",
        "industry": "Food & Beverage",
        "website": "https://riversidecoffee.ca",
        "email": "hello@riversidecoffee.ca",
        "service_area": "Downtown Toronto",
        "preferred_vehicle": "cargo_bike",
        "estimated_deliveries_per_month": 90,
        "estimated_monthly_revenue_cents": 450_000,
        "merchant_status": "lead",
        "tags": ["smb"],
    },
]

LEADS = [
    {
        "company_name": "Westside Auto Parts",
        "industry": "Automotive",
        "email": "purchasing@westsideauto.ca",
        "phone": "+1 416-555-0220",
        "primary_contact_name": "Marcus Reid",
        "source": "website",
        "priority": "high",
        "estimated_deliveries_per_month": 480,
        "estimated_revenue_cents": 2_600_000,
        "service_area": "GTA West",
        "current_logistics_provider": "Canada Post",
    },
    {
        "company_name": "Bloom & Petal Florists",
        "industry": "Retail",
        "email": "orders@bloompetal.ca",
        "primary_contact_name": "Sofia Martins",
        "source": "referral",
        "priority": "medium",
        "estimated_deliveries_per_month": 120,
        "estimated_revenue_cents": 600_000,
        "service_area": "Toronto Core",
    },
    {
        "company_name": "Apex Electronics Wholesale",
        "industry": "Electronics",
        "email": "logistics@apexelec.ca",
        "phone": "+1 905-555-0333",
        "primary_contact_name": "David Kim",
        "source": "for_business",
        "priority": "urgent",
        "estimated_deliveries_per_month": 900,
        "estimated_revenue_cents": 4_100_000,
        "service_area": "Ontario",
        "current_logistics_provider": "UPS",
    },
]


def ensure_reps(db) -> list[AdminUser]:
    users = []
    for email, name, role in REPS:
        user = db.query(AdminUser).filter(AdminUser.email == email).first()
        if not user:
            user = AdminUser(clerk_user_id=f"seed:{email}", email=email, name=name, role=role.value)
            db.add(user)
            db.commit()
            db.refresh(user)
        users.append(user)
    return users


def main() -> None:
    init_db()
    db = SessionLocal()
    svc = CrmSalesService()
    try:
        if db.query(CrmCompany).filter(CrmCompany.legal_name == SEED_MARKER).first():
            print("CRM demo data already present — skipping.")
            return

        reps = ensure_reps(db)
        ctx = AdminContext(user=reps[0], role=AdminRole.SALES_MANAGER)

        companies = []
        for i, payload in enumerate(COMPANIES):
            payload = {**payload, "owner_id": reps[i % len(reps)].id}
            company = svc.create_company(db, ctx, payload)
            companies.append(company)

        # Contacts for the first two companies.
        svc.create_contact(db, ctx, {
            "company_id": companies[0].id, "first_name": "Emily", "last_name": "Nguyen",
            "designation": "Head of Logistics", "department": "Operations",
            "email": "emily@mapleleafdist.ca", "phone": "+1 416-555-0143",
            "roles": ["decision_maker", "operations_manager"], "is_primary": True,
        })
        svc.create_contact(db, ctx, {
            "company_id": companies[0].id, "first_name": "Raj", "last_name": "Singh",
            "designation": "Accounts Payable", "email": "ap@mapleleafdist.ca",
            "roles": ["accounts_payable"],
        })
        svc.create_contact(db, ctx, {
            "company_id": companies[1].id, "first_name": "Hannah", "last_name": "Cole",
            "designation": "Warehouse Manager", "email": "warehouse@northernmed.ca",
            "roles": ["warehouse_manager", "primary_contact"], "is_primary": True,
        })

        # Deals across the pipeline.
        stage_plan = [
            (companies[0], DealStage.NEGOTIATION, 4_800_000, 75),
            (companies[1], DealStage.QUOTE_SENT, 2_100_000, 60),
            (companies[2], DealStage.MEETING_SCHEDULED, 3_300_000, 40),
            (companies[3], DealStage.PROSPECTING, 450_000, 10),
        ]
        deals = []
        for i, (company, stage, revenue, prob) in enumerate(stage_plan):
            deal = svc.create_deal(db, ctx, {
                "name": f"{company.operating_name} — Merchant Program",
                "company_id": company.id,
                "stage": stage.value,
                "probability": prob,
                "expected_revenue_cents": revenue,
                "expected_close_date": (datetime.now(UTC) + timedelta(days=20 + i * 10)).date(),
                "owner_id": company.owner_id,
            })
            deals.append(deal)

        # A won deal this month to populate conversion metrics.
        won = svc.create_deal(db, ctx, {
            "name": "Riverside Coffee — Pilot",
            "company_id": companies[3].id,
            "stage": DealStage.PROSPECTING.value,
            "expected_revenue_cents": 450_000,
            "owner_id": reps[2].id,
        })
        svc.move_deal(db, ctx, won.id, DealStage.WON.value, 0)

        # Quotation on the negotiation deal + convert to contract.
        quote = svc.create_quotation(db, ctx, {
            "deal_id": deals[0].id,
            "company_id": companies[0].id,
            "line_items": [
                {"label": "Same-day cargo van (per delivery)", "quantity": 1200, "unit_price_cents": 1800},
                {"label": "Dedicated account management (monthly)", "quantity": 1, "unit_price_cents": 50000},
            ],
            "tax_cents": 280_000,
            "notes": "Volume pricing for 1,200 deliveries/month across the GTA.",
        })
        svc.update_quotation_status(db, ctx, quote.id, "sent")

        # Contracts.
        svc.create_contract(db, ctx, {
            "company_id": companies[1].id,
            "deal_id": deals[1].id,
            "net_terms": "NET_30",
            "value_cents": 2_100_000,
            "sla": {"on_time_target_percent": 98, "support": "24/7"},
            "service_areas": ["Ontario"],
            "vehicles": ["refrigerated_van"],
            "effective_from": datetime.now(UTC).date(),
            "expiry_date": (datetime.now(UTC) + timedelta(days=365)).date(),
        })

        # Leads.
        for i, payload in enumerate(LEADS):
            svc.create_lead(db, ctx, {**payload, "assigned_to": reps[i % len(reps)].id})

        # Tasks: a follow-up due today, an overdue one, and a meeting.
        now = datetime.now(UTC)
        svc.create_task(db, ctx, {
            "title": "Follow up on Maple Leaf volume pricing",
            "task_type": "follow_up", "priority": "high",
            "entity_type": "deal", "entity_id": deals[0].id, "company_id": companies[0].id,
            "deal_id": deals[0].id, "assigned_to": reps[0].id,
            "due_at": now.replace(hour=15, minute=0),
        })
        svc.create_task(db, ctx, {
            "title": "Send NDA to Northern MedSupply",
            "task_type": "document", "priority": "medium",
            "entity_type": "company", "entity_id": companies[1].id, "company_id": companies[1].id,
            "assigned_to": reps[1].id,
            "due_at": now - timedelta(days=2),
        })
        svc.create_task(db, ctx, {
            "title": "Discovery call with GTA BuildMat",
            "task_type": "meeting", "priority": "high",
            "entity_type": "deal", "entity_id": deals[2].id, "company_id": companies[2].id,
            "deal_id": deals[2].id, "assigned_to": reps[2].id,
            "due_at": now.replace(hour=11, minute=0),
        })

        print("Seeded CRM demo data:")
        print(f"  companies : {len(companies)}")
        print(f"  deals     : {len(deals) + 1}")
        print(f"  leads     : {len(LEADS)}")
        print(f"  reps      : {len(reps)}")
        dash = svc.dashboard(db)
        print(f"  pipeline value: ${dash['pipeline_value_cents'] / 100:,.2f}")
        print(f"  forecast      : ${dash['monthly_revenue_forecast_cents'] / 100:,.2f}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
