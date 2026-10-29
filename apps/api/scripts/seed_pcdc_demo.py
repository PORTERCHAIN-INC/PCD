"""Seed the PCDC Shopify reviewer demo (doc 74 §2 step 6, G20 A-SHR-06).

One demo organisation linked to ``pcdc-demo.myshopify.com`` plus 3 sandbox orders
(``is_sandbox=True``: never dispatched, never invoiced). Idempotent on the shop domain.

Refuses to run against anything but a local throwaway database (default: the
scripts/test-infra.sh Postgres on 127.0.0.1:55432). Never point it at the live 5432.

    DATABASE_URL=postgresql+psycopg://porterchain:porterchain@127.0.0.1:55432/porterchain_test \
      .venv/bin/python scripts/seed_pcdc_demo.py
"""
from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))

PCDC_SHOP = "pcdc-demo.myshopify.com"
PCDC_MARKER = "pcdc-review-demo"
_ALLOWED_PORTS = {int(p) for p in os.environ.get("PCD_SEED_ALLOWED_PORTS", "55432").split(",") if p.strip()}
_LIVE_PORTS = {5432}


def guard(url: str) -> None:
    parts = urlsplit(url)
    if parts.hostname not in {"127.0.0.1", "localhost", "::1"} or parts.port in _LIVE_PORTS or parts.port not in _ALLOWED_PORTS:
        raise SystemExit(f"refusing to seed {parts.hostname}:{parts.port}: only local throwaway DBs on {sorted(_ALLOWED_PORTS)}")


DEMO_ORDERS = [
    ("1 Yonge St, Toronto ON M5E 1E5", 43.6426, -79.3755, "M5E 1E5"),
    ("290 Bremner Blvd, Toronto ON M5V 3L9", 43.6426, -79.3871, "M5V 3L9"),
    ("100 City Centre Dr, Mississauga ON L5B 2C9", 43.5931, -79.6424, "L5B 2C9"),
]


def seed(db) -> dict:
    from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
    from porterchain_api.booking_models import Order
    from porterchain_api.domain.states import OrderState
    from porterchain_api.merchant_models import Merchant, ShopifyShop

    row = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == PCDC_SHOP).first()
    if row is None:
        m = Merchant(company_name="PCDC Demo Store", email="review.shopify@example.test",
                     profile={"source": "shopify_install", "shopify_shop_domain": PCDC_SHOP, "demo": True})
        db.add(m)
        db.flush()
        row = ShopifyShop(merchant_id=m.id, shop_domain=PCDC_SHOP, auto_dispatch=False,
                          installed_at=datetime.now(UTC), scopes="read_orders,write_shipping")
        db.add(row)
        db.flush()
    existing = db.query(Order).filter(Order.merchant_id == row.merchant_id, Order.internal_reference == PCDC_MARKER).count()
    pickup = {"formatted": "100 King St W, Toronto ON M5X 1A9", "lat": 43.6487, "lng": -79.3817, "postal": "M5X 1A9"}
    for formatted, lat, lng, postal in DEMO_ORDERS[existing:]:
        db.add(Order(order_number=generate_order_number(), tracking_number=generate_tracking_number(),
                     state=OrderState.BOOKED.value, merchant_id=row.merchant_id, amount_cents=0,
                     pickup=pickup, dropoff={"formatted": formatted, "lat": lat, "lng": lng, "postal": postal},
                     scheduled_at=datetime.now(UTC) + timedelta(days=1), internal_reference=PCDC_MARKER,
                     special_instructions="Demo order for Shopify review. Never dispatched.", is_sandbox=True))
    db.commit()
    n = db.query(Order).filter(Order.merchant_id == row.merchant_id, Order.internal_reference == PCDC_MARKER).count()
    return {"shop": PCDC_SHOP, "merchant_id": row.merchant_id, "demo_orders": n}


def main() -> None:
    guard(os.environ.get("DATABASE_URL", ""))
    from porterchain_api.db import SessionLocal, init_db

    init_db()
    with SessionLocal() as db:
        print(seed(db))


if __name__ == "__main__":
    main()
