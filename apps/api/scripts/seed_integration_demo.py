"""Local integration demo data on top of seed_local_dev (idempotent-ish: skips if marker lead exists).

Leads, a Shopify-connected merchant, more orders of every shape, cycle invoices with PC codes +
Interac e-Transfers (matched / needs review), notification delivery log, partners, exceptions.
Local only. No external calls.
"""
from __future__ import annotations

import importlib.util
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))
spec = importlib.util.spec_from_file_location("sld", API_ROOT / "scripts/seed_local_dev.py")
sld = importlib.util.module_from_spec(spec); spec.loader.exec_module(sld)  # type: ignore[union-attr]

from porterchain_api.billing_engine.models import InteracTransfer  # noqa: E402
from porterchain_api.booking_models import Invoice, Order, OrderException  # noqa: E402
from porterchain_api.config import get_settings  # noqa: E402
from porterchain_api.crm_models import CrmLead  # noqa: E402
from porterchain_api.db import SessionLocal, init_db  # noqa: E402
from porterchain_api.dispatch_engine.models import LogisticsPartner  # noqa: E402
from porterchain_api.merchant_models import Merchant, MerchantUser, ShopifyShop  # noqa: E402
from porterchain_api.notification_engine.models import NotificationDeliveryLog  # noqa: E402

AI = sld.AddressInput
ADDR = [
    AI(formatted="1 Yonge St, Toronto ON M5E 1E5", lat=43.6426, lng=-79.3755, postal="M5E 1E5"),
    AI(formatted="290 Bremner Blvd, Toronto ON M5V 3L9", lat=43.6426, lng=-79.3871, postal="M5V 3L9"),
    AI(formatted="100 City Centre Dr, Mississauga ON L5B 2C9", lat=43.5931, lng=-79.6424, postal="L5B 2C9"),
    AI(formatted="1 Bass Pro Mills Dr, Vaughan ON L4K 5W4", lat=43.8255, lng=-79.5385, postal="L4K 5W4"),
    AI(formatted="25 Peel Centre Dr, Brampton ON L6T 3R5", lat=43.7176, lng=-79.7224, postal="L6T 3R5"),
    AI(formatted="5000 Hwy 7, Markham ON L3R 4M9", lat=43.8687, lng=-79.2885, postal="L3R 4M9"),
]
now = datetime.now(UTC)


def main() -> None:
    init_db()
    settings = get_settings()
    random.seed(7)
    with SessionLocal() as db:
        if db.query(CrmLead).filter(CrmLead.company_name == "Maple Bakery Co.").first():
            print("integration demo already seeded"); return
        merchant = db.query(Merchant).first(); muser = db.query(MerchantUser).first()
        # Leads across the 5 stages
        for i, (co, st, src, pri) in enumerate([
            ("Maple Bakery Co.", "new", "website", "high"), ("Northside Pharmacy", "new", "contact_form", "high"),
            ("GTA Florist", "replied", "email", "medium"), ("Lakeshore Furniture", "quoted", "website", "high"),
            ("Bloor Books", "quoted", "calculator", "medium"), ("Danforth Deli", "won", "referral", "medium"),
            ("Queen West Apparel", "lost", "website", "low"), ("Etobicoke Auto Parts", "new", "shopify_app", "medium"),
            ("Scarborough Lab Services", "replied", "phone", "high"), ("Retail: Priya S.", "new", "booking_draft", "medium"),
        ]):
            db.add(CrmLead(company_name=co, status=st, source=src, priority=pri, address={"city": "Toronto"},
                           email=f"lead{i}@example.test", primary_contact_name=f"Contact {i}", phone="+1 416-555-01%02d" % i,
                           tags=["demo"], lead_score=random.randint(30, 95), custom_fields={},
                           awaiting_reply=st == "new", last_inbound_at=now - timedelta(minutes=7 * (i + 1)),
                           estimated_deliveries_per_month=random.choice([20, 60, 150, 400]),
                           lost_reason="price" if st == "lost" else None))
        # Shopify connections: one healthy, one needing attention
        db.add(ShopifyShop(merchant_id=merchant.id, shop_domain="dev-merchant-demo.myshopify.com", token_status="active",
                           scopes="read_orders,write_fulfillments,read_shipping,write_shipping", installed_at=now - timedelta(days=20),
                           last_webhook_at=now - timedelta(minutes=12), carrier_service_gid="gid://shopify/CarrierService/1"))
        m2 = Merchant(company_name="Lakeshore Furniture (Shopify)", email="ops@lakeshore.example.test", status=merchant.status)
        for col in ("pricing_model", "payment_terms"):
            if hasattr(merchant, col) and getattr(merchant, col) is not None:
                setattr(m2, col, getattr(merchant, col))
        db.add(m2); db.flush()
        db.add(ShopifyShop(merchant_id=m2.id, shop_domain="lakeshore-furniture.myshopify.com", token_status="expired",
                           scopes="read_orders", installed_at=now - timedelta(days=60), last_webhook_at=now - timedelta(days=4)))
        db.commit()
        # More orders of every shape
        orders = []
        for i in range(6):
            orders.append(sld.create_merchant_order(db, settings, merchant, muser, label=f"int-m{i}"))
        for i in range(4):
            _, o = sld.create_retail_order(db, settings, label=f"int-r{i}", pickup=ADDR[i], dropoff=ADDR[(i + 2) % 6])
            orders.append(o)
        db.commit()
        drv = db.query(sld.Driver).first() if hasattr(sld, "Driver") else None
        try:
            sld.create_order_variants(db, orders, drv.id if drv else None); db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback(); print("order variants skipped:", type(exc).__name__, exc)
        for o in orders[:3]:
            db.add(OrderException(order_id=o.id, type=random.choice(["late", "failed_delivery", "damaged"]), status="open",
                                  reported_by_type="driver", evidence={"note": "demo"}))
        # Cycle invoices with PC codes + e-Transfers
        invs = []
        for n, (amt, days_due, status) in enumerate([(48250, -12, "sent"), (31900, 5, "sent"), (12500, -40, "sent"), (22000, -3, "paid")]):
            inv = Invoice(invoice_number=f"INV-INT-{1001+n}", merchant_id=merchant.id if n != 2 else m2.id, amount_cents=amt,
                          tax_cents=int(amt * 0.13), fees_cents=0, currency="cad", status=status, billing_kind="cycle",
                          issued_at=now - timedelta(days=30), due_at=now + timedelta(days=days_due),
                          billing_period_start=now - timedelta(days=45), billing_period_end=now - timedelta(days=15),
                          payment_reference=f"PC-INT{n+1:02d}", tax_province="ON",
                          paid_at=now - timedelta(days=2) if status == "paid" else None,
                          amount_paid_cents=int(amt * 1.13) if status == "paid" else 0)
            db.add(inv); invs.append(inv)
        db.flush()
        db.add(InteracTransfer(message_id="demo-etr-1", amount_cents=int(22000 * 1.13), sender_name="Dev Merchant Co.",
                               memo="PC-INT04", invoice_id=invs[3].id, merchant_id=merchant.id, match_method="reference",
                               match_note="exact", status="matched", auth_ok=True, received_at=now - timedelta(days=2)))
        db.add(InteracTransfer(message_id="demo-etr-2", amount_cents=20000, sender_name="Dev Merchant Co.", memo="part payment",
                               merchant_id=merchant.id, match_note="unmatched", status="needs_review", auth_ok=True,
                               received_at=now - timedelta(hours=5)))
        db.add(InteracTransfer(message_id="demo-etr-3", amount_cents=14125, sender_name="Lakeshore Furniture", memo="PC-INT03",
                               invoice_id=invs[2].id, merchant_id=m2.id, match_method="reference", match_note="exact",
                               status="needs_review", auth_ok=True, received_at=now - timedelta(hours=1)))
        # Partners
        for name, kind, fsa in [("Purolator Freight (demo)", "ltl", ["K", "L"]), ("Day & Ross FTL (demo)", "ftl", ["L", "M", "N"]),
                                ("Ottawa 3PL Hub (demo)", "3pl", ["K"])]:
            db.add(LogisticsPartner(name=name, kind=kind, fsa_coverage=fsa, rate_per_kg_cents=45, min_charge_cents=4500,
                                    contact_email=f"ops@{kind}.example.test"))
        # Notification delivery log
        for i in range(24):
            st = random.choices(["sent", "delivered", "opened", "failed", "bounced"], [3, 5, 3, 1, 1])[0]
            db.add(NotificationDeliveryLog(channel="email", template=random.choice(
                ["order_confirmed", "out_for_delivery", "delivered", "delivery_failed", "merchant.invoice_generated", "eta_update"]),
                recipient=f"receiver{i}@example.test", status=st, error="550 mailbox unavailable" if st in ("failed", "bounced") else None,
                context={"demo": True}, created_at=now - timedelta(minutes=37 * i)))
        db.commit()
        print("integration demo seed complete:", len(orders), "orders, 10 leads, 4 cycle invoices, 3 e-Transfers, 3 partners, 24 email logs")


if __name__ == "__main__":
    main()
