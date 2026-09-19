"""Seed N retail website bookings — quote → checkout → payment success (local dev).

Simulates the website flow: anonymous quote, customer sign-in, payment, order booked.
Uses mock_complete_checkout (service layer) so Stripe webhook is not required locally.

Usage:
    cd apps/api && PYTHONPATH=src uv run python scripts/seed_website_retail_batch.py
    cd apps/api && PYTHONPATH=src uv run python scripts/seed_website_retail_batch.py --count 15
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))

from porterchain_api.booking_engine.booking_service import BookingService
from porterchain_api.booking_engine.confirmation_service import BookingConfirmationService
from porterchain_api.booking_engine.customer_service import CustomerService
from porterchain_api.booking_engine.payment_service import PaymentService
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.config import get_settings
from porterchain_api.db import SessionLocal, init_db
from porterchain_api.domain.states import PaymentStatus
from porterchain_api.booking_models import Customer, Order, Payment, Quote
from porterchain_api.schemas import AddressInput, CreateQuoteRequest, WebsitePricingSnapshot

MARKER = "website-retail-batch-v1"

ROUTES: list[tuple[str, float, float, str, float, float]] = [
    ("100 King St W, Toronto ON M5X 1A9", 43.6488, -79.3817, "200 Bay St, Toronto ON M5J 2J2", 43.6476, -79.3797),
    ("550 Dundas St W, Toronto ON M5T 1H4", 43.6510, -79.4042, "945 Lakeshore Blvd E, Toronto ON M4M 1A4", 43.6550, -79.3400),
    ("875 Don Mills Rd, North York ON M3C 1V9", 43.7250, -79.3460, "25 The West Mall, Etobicoke ON M9C 1B8", 43.6230, -79.5580),
    ("1185 Finch Ave W, North York ON M3J 2G5", 43.7677, -79.5010, "1450 Derry Rd E, Mississauga ON L5T 2B8", 43.6470, -79.6500),
    ("2450 Dundas St E, Mississauga ON L4X 1M3", 43.6129, -79.5780, "50 Bramgate Dr, Brampton ON L6T 5E8", 43.7315, -79.7082),
    ("1 Yonge St, Toronto ON M5E 1W7", 43.6426, -79.3742, "77 Bloor St W, Toronto ON M5S 1M2", 43.6677, -79.3948),
    ("3401 Dufferin St, North York ON M6A 2T9", 43.7253, -79.4512, "1900 Eglinton Ave E, Scarborough ON M1L 2L9", 43.7273, -79.2925),
    ("609 Kipling Ave, Etobicoke ON M8Z 5G9", 43.6360, -79.5340, "300 Borough Dr, Scarborough ON M1P 4P5", 43.7750, -79.2570),
    ("5100 Erin Mills Pkwy, Mississauga ON L5M 4Z2", 43.5480, -79.7130, "100 City Centre Dr, Mississauga ON L5B 2C9", 43.5930, -79.6420),
    ("Toronto Pearson Airport, Mississauga ON L5P 1B2", 43.6777, -79.6248, "Union Station, Toronto ON M5J 1E6", 43.6454, -79.3806),
    ("2200 Eglinton Ave W, Mississauga ON L5M 2E3", 43.5530, -79.6860, "4800 Yonge St, North York ON M2N 5N9", 43.7670, -79.4130),
    ("2000 Credit Valley Rd, Mississauga ON L5M 4N4", 43.5690, -79.6980, "1400 Dupont St, Toronto ON M6H 2B2", 43.6650, -79.4400),
    ("1027 Yonge St, Toronto ON M4W 2K9", 43.6750, -79.3890, "2300 Keele St, North York ON M6M 3Z9", 43.7070, -79.4780),
    ("1600 Bathurst St, Toronto ON M5P 3H8", 43.6890, -79.4150, "3030 Lawrence Ave E, Scarborough ON M1P 2T7", 43.7510, -79.2760),
    ("181 Bay St, Toronto ON M5J 2T3", 43.6460, -79.3780, "945 Wilson Ave, North York ON M3K 1E8", 43.7290, -79.4490),
]


def _website_pricing(distance_km: float = 8.0) -> WebsitePricingSnapshot:
    return WebsitePricingSnapshot(
        customer_price_cad=42.0 + distance_km,
        driver_payout_cad=28.0 + distance_km * 0.6,
        platform_margin_cad=14.0 + distance_km * 0.4,
        distance_km=distance_km,
        duration_minutes=20.0 + distance_km,
        engine_vehicle_id="cargo_van",
        breakdown={"base": 12.0, "distance": 30.0 + distance_km},
    )


def _addr(formatted: str, lat: float, lng: float) -> AddressInput:
    return AddressInput(formatted=formatted, lat=lat, lng=lng)


def create_website_booking(
    db,
    settings,
    *,
    index: int,
    route: tuple[str, float, float, str, float, float],
) -> tuple[Customer, Order]:
    pu_fmt, pu_lat, pu_lng, dr_fmt, dr_lat, dr_lng = route
    label = f"web-{index:02d}"
    email = f"website.customer{index:02d}@test.porterchain.com"
    phone = f"+1 416-555-{1000 + index:04d}"
    clerk_id = f"website_test_user_{index:02d}"
    session_id = f"website-session-{label}"

    customers = CustomerService()
    quotes = QuoteService()
    bookings = BookingService()
    payments = PaymentService()
    confirm = BookingConfirmationService()

    scheduled = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(hours=2 + index)

    quote = quotes.create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=session_id,
            pickup=_addr(pu_fmt, pu_lat, pu_lng),
            dropoff=_addr(dr_fmt, dr_lat, dr_lng),
            vehicle_class="cargo_van",
            package_type="looseParcel",
            weight_kg=5.0 + index,
            scheduled_at=scheduled,
            schedule_mode="scheduled",
            website_pricing=_website_pricing(6.0 + index * 0.5),
        ),
        ip_address="127.0.0.1",
    )

    try:
        quote, customer, _checkout = bookings.start_booking(
            db,
            settings,
            quote_id=quote.id,
            email=email,
            phone=phone,
            clerk_user_id=clerk_id,
            anonymous_session_id=session_id,
            consent={
                "terms_accepted": True,
                "privacy_accepted": True,
                "dangerous_goods_confirmed": True,
                "consent_at": datetime.now(UTC).isoformat(),
            },
        )
    except Exception:
        customer = customers.upsert(
            db,
            clerk_user_id=clerk_id,
            email=email,
            phone=phone,
            visitor_session_id=session_id,
        )
        quote.customer_id = customer.id
        quote.email = email
        quote.phone = phone
        db.commit()
        db.refresh(quote)
        payments.start_payment(db, settings, quote, customer)

    order = confirm.mock_complete_checkout(db, settings, quote.id)
    order.internal_reference = f"{MARKER}-{label}"
    order.special_instructions = f"Website test booking #{index} — {email}"

    payment = db.query(Payment).filter(Payment.quote_id == quote.id).order_by(Payment.created_at.desc()).first()
    if payment and payment.status != PaymentStatus.SUCCEEDED.value:
        payments.mark_succeeded(db, payment, stripe_payment_intent_id=f"pi_test_{label}")

    db.commit()
    db.refresh(customer)
    db.refresh(order)
    return customer, order


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed website retail bookings with successful payments")
    parser.add_argument("--count", type=int, default=15, help="Number of bookings (max 15 routes defined)")
    args = parser.parse_args()
    count = min(max(args.count, 1), len(ROUTES))

    init_db()
    settings = get_settings()
    db = SessionLocal()

    existing = (
        db.query(Order)
        .filter(Order.internal_reference.like(f"{MARKER}-%"))
        .count()
    )
    if existing >= count:
        print(f"Already have {existing} {MARKER} orders — skipping.")
        orders = db.query(Order).filter(Order.internal_reference.like(f"{MARKER}-%")).order_by(Order.created_at).all()
        for o in orders[:count]:
            c = db.get(Customer, o.customer_id) if o.customer_id else None
            print(f"  {o.order_number} | {c.email if c else '?'} | {o.state} | {o.tracking_number}")
        db.close()
        return

    created: list[tuple[Customer, Order]] = []
    for i in range(1, count + 1):
        if db.query(Order).filter(Order.internal_reference == f"{MARKER}-web-{i:02d}").first():
            continue
        customer, order = create_website_booking(db, settings, index=i, route=ROUTES[i - 1])
        created.append((customer, order))
        print(f"OK {i}/{count} | {customer.email} | {order.order_number} | {order.tracking_number} | {order.state}")

    print(f"\nCreated {len(created)} website retail orders ({MARKER}).")
    print("View on website track pages or admin Orders list (order_source=retail).")
    db.close()


if __name__ == "__main__":
    main()
