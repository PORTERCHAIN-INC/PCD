"""Seed dummy data across all Porterchain admin modules for local testing.

Idempotent — safe to re-run (skips when seed marker order exists).

Usage:
    cd apps/api && PYTHONPATH=src python scripts/seed_local_dev.py
    pnpm db:seed
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))


def _load_script(name: str):
    path = API_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_seed_portal = _load_script("seed_dev_portal_users")
DEV_ORG = _seed_portal.DEV_ORG
from porterchain_api.admin_engine.claims_service import AdminClaimsService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_engine.support_service import AdminSupportService
from porterchain_api.admin_models import AdminUser, PricingTariff
from porterchain_api.auth.merchant import MerchantContext
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_engine.confirmation_service import BookingConfirmationService
from porterchain_api.booking_engine.customer_service import CustomerService
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.booking_engine.payment_service import PaymentService
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.config import get_settings
from porterchain_api.db import SessionLocal, init_db
from porterchain_api.domain.admin_states import AdminRole, DriverStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.driver_models import DriverBonus, DriverLocationPing, DriverWalletTransaction
from porterchain_api.platform.retired_sync import RetryQueue
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.rbac import MerchantRole
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.booking_models import Customer, Lead, Order, Payment
from porterchain_api.notification_engine.engine import NotificationEngine
from porterchain_api.schemas import AddressInput, CreateQuoteRequest, WebsitePricingSnapshot
from porterchain_api.schemas_merchant import AddressInput as MerchantAddressInput
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest

SEED_MARKER = "seed-local-dev-v1"
SEED_ADMIN_EMAIL = "seed-admin@porterchain.com"
# Real Platform Clerk founder — kept as super_admin in local/prod data.
FOUNDER_SUPER_ADMIN_EMAIL = "porterchaininc@gmail.com"

PICKUP = AddressInput(formatted="123 King St W, Toronto ON M5H 3T9", lat=43.6488, lng=-79.3817, postal="M5H 3T9")
DROPOFF = AddressInput(formatted="456 Queen St W, Toronto ON M5V 2B1", lat=43.6479, lng=-79.3957, postal="M5V 2B1")
PICKUP2 = AddressInput(formatted="100 Bay St, Toronto ON M5J 2S1", lat=43.6481, lng=-79.3795, postal="M5J 2S1")
DROPOFF2 = AddressInput(formatted="200 Spadina Ave, Toronto ON M5T 2C2", lat=43.6501, lng=-79.3962, postal="M5T 2C2")


def _now() -> datetime:
    return datetime.now(UTC)


def seed_complete(db) -> bool:
    return (
        db.query(BookingDraft).filter(BookingDraft.session_id == "seed-draft-session").first()
        is not None
    )


def ensure_admin(db) -> AdminUser:
    user = db.query(AdminUser).filter(AdminUser.email == SEED_ADMIN_EMAIL).first()
    if not user:
        user = AdminUser(
            clerk_user_id=f"seed:{SEED_ADMIN_EMAIL}",
            email=SEED_ADMIN_EMAIL,
            name="Seed Super Admin",
            role=AdminRole.SUPER_ADMIN.value,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    # Staff IdP subject staff:{id} + SpiceDB — required for real magic-link login.
    try:
        from porterchain_api.admin_engine.staff_idp_service import ensure_staff_identity

        ensure_staff_identity(db, user)
        db.refresh(user)
    except Exception as exc:  # noqa: BLE001
        print(f"  warn: staff identity for seed-admin failed: {exc}")
    return user


def ensure_founder_super_admin(db) -> AdminUser | None:
    """Idempotent: porterchaininc@gmail.com is always active super_admin when present."""
    from porterchain_api.authz.tuples import TupleWriter
    from porterchain_api.user_models import PorterchainUser

    email = FOUNDER_SUPER_ADMIN_EMAIL
    pc = db.query(PorterchainUser).filter(PorterchainUser.email.ilike(email)).first()
    admin = db.query(AdminUser).filter(AdminUser.email.ilike(email)).first()
    if not admin and not pc:
        return None
    if not admin:
        admin = AdminUser(
            clerk_user_id=pc.clerk_user_id if pc else f"pending:{email}",
            email=email,
            name="PorterChain Founder",
            role=AdminRole.SUPER_ADMIN.value,
            is_active=True,
            porterchain_user_id=pc.id if pc else None,
        )
        db.add(admin)
    else:
        admin.role = AdminRole.SUPER_ADMIN.value
        admin.is_active = True
        if pc:
            admin.porterchain_user_id = pc.id
            if pc.clerk_user_id:
                admin.clerk_user_id = pc.clerk_user_id
    if pc and pc.status != "active":
        pc.status = "active"
    db.commit()
    db.refresh(admin)
    try:
        from porterchain_api.admin_engine.staff_idp_service import ensure_staff_identity

        ensure_staff_identity(db, admin)
        db.refresh(admin)
    except Exception as exc:  # noqa: BLE001
        print(f"  warn: staff identity for founder failed: {exc}")
    if pc:
        try:
            TupleWriter().sync_user_from_profiles(db, pc)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            print(f"  warn: SpiceDB sync for founder failed: {exc}")
    return admin


def ensure_pricing_tariff(db) -> None:
    """Seed optional retail catalog tariffs only.

    Do not seed global `tariff_type=merchant` rows — unscoped merchant tariffs
    used to steal FSA/GTA bases on every merchant quote. Merchant deals use
    `pricing_fsa_rates`, `pricing_config.gta_rate`, or merchant-scoped tariffs.
    """
    if db.query(PricingTariff).filter(PricingTariff.is_active.is_(True)).first():
        return
    db.add(
        PricingTariff(
            name="GTA Standard Cargo Van",
            tariff_type="retail",
            vehicle_class="cargo_van",
            zone="gta",
            base_cents=1200,
            per_km_cents=95,
            fuel_surcharge_percent=5.0,
            is_active=True,
            config={"seed": True},
        )
    )
    db.commit()


def _website_pricing() -> WebsitePricingSnapshot:
    return WebsitePricingSnapshot(
        customer_price_cad=45.0,
        driver_payout_cad=32.0,
        platform_margin_cad=13.0,
        distance_km=5.2,
        duration_minutes=18.0,
        engine_vehicle_id="cargo_van",
        breakdown={"base": 12.0, "distance": 33.0},
    )


def create_retail_order(db, settings, *, label: str, pickup: AddressInput, dropoff: AddressInput) -> tuple[Customer, Order]:
    customers = CustomerService()
    quotes = QuoteService()
    payments = PaymentService()
    confirm = BookingConfirmationService()

    customer = customers.upsert(
        db,
        clerk_user_id=f"seed:customer:{label}",
        email=f"{label}@seed.porterchain.com",
        phone="+1 416-555-0144",
        visitor_session_id=f"seed-session-{label}",
    )
    quote = quotes.create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=f"seed-session-{label}",
            pickup=pickup,
            dropoff=dropoff,
            vehicle_class="cargo_van",
            # Whole-vehicle booking: a parcels-mode quote without parcels fails with
            # parcels_required at checkout.
            booking_mode="vehicle",
            package_type="looseParcel",
            scheduled_at=_now() + timedelta(hours=3),
            website_pricing=_website_pricing(),
        ),
    )
    quote.customer_id = customer.id
    db.commit()
    db.refresh(quote)

    payments.start_payment(db, settings, quote, customer)
    order = confirm.mock_complete_checkout(db, settings, quote.id)
    order.internal_reference = SEED_MARKER
    order.special_instructions = f"Seed order — {label}"
    db.commit()
    db.refresh(order)
    return customer, order


def create_merchant_order(db, settings, merchant: Merchant, user: MerchantUser, *, label: str) -> Order:
    ctx = MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)
    body = MerchantBookDeliveryRequest(
        pickup=MerchantAddressInput(**PICKUP2.model_dump()),
        dropoff=MerchantAddressInput(**DROPOFF2.model_dump()),
        vehicle_class="cargo_van",
        scheduled_at=_now() + timedelta(hours=4),
        internal_reference=f"{SEED_MARKER}-{label}",
        special_instructions=f"Merchant seed — {label}",
    )
    try:
        order = MerchantBookingService().create_shipment(db, settings, ctx, body)
        order.internal_reference = SEED_MARKER
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        order = Order(
            order_number=generate_order_number(),
            tracking_number=generate_tracking_number(),
            state=OrderState.BOOKED.value,
            merchant_id=merchant.id,
            amount_cents=5200,
            pickup=PICKUP2.model_dump(),
            dropoff=DROPOFF2.model_dump(),
            scheduled_at=_now() + timedelta(hours=4),
            internal_reference=SEED_MARKER,
            special_instructions=f"Merchant seed fallback — {label}",
            is_sandbox=False,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order


def cleanup_partial_seed_orders(db) -> int:
    """Remove incomplete seed orders so a failed run can be retried."""
    from sqlalchemy import text

    order_ids = [row[0] for row in db.query(Order.id).filter(Order.internal_reference == SEED_MARKER).all()]
    if not order_ids:
        return 0
    for table in (
        "billing_ledger_entries",
        "fleetbase_sync_jobs",
        "claims",
        "order_events",
        "payments",
        "invoices",
        "bookings",
        "support_tickets",
    ):
        db.execute(text(f"DELETE FROM {table} WHERE order_id = ANY(:ids)"), {"ids": order_ids})
    db.execute(
        text("DELETE FROM domain_events WHERE aggregate_type = 'order' AND aggregate_id = ANY(:ids)"),
        {"ids": order_ids},
    )
    quote_ids = [
        row[0]
        for row in db.execute(
            text("SELECT quote_id FROM orders WHERE id = ANY(:ids) AND quote_id IS NOT NULL"),
            {"ids": order_ids},
        )
    ]
    db.query(Order).filter(Order.internal_reference == SEED_MARKER).delete(synchronize_session=False)
    if quote_ids:
        db.execute(
            text("UPDATE booking_drafts SET quote_id = NULL WHERE quote_id = ANY(:ids)"),
            {"ids": quote_ids},
        )
        db.execute(text("DELETE FROM quotes WHERE id = ANY(:ids)"), {"ids": quote_ids})
    db.query(Customer).filter(Customer.email.like("%@seed.porterchain.com")).delete(synchronize_session=False)
    db.commit()
    return len(order_ids)


def _advance_order(db, order: Order, to_state: OrderState, event_type: str) -> None:
    if OrderState(order.state) == to_state:
        return
    transition_order_state(db, order, to_state, event_type=event_type, payload={"seed": True})
    db.refresh(order)


def create_order_variants(db, orders: list[Order], driver_id: str | None) -> None:
    if len(orders) >= 2:
        _advance_order(db, orders[1], OrderState.DISPATCH_READY, "order.dispatch_ready")

    if driver_id and len(orders) >= 3:
        orders[2].assigned_driver_id = driver_id
        db.commit()
        db.refresh(orders[2])
        for state in (
            OrderState.DISPATCH_READY,
            OrderState.DRIVER_ASSIGNED,
            OrderState.DRIVER_ACCEPTED,
            OrderState.DRIVER_EN_ROUTE,
            OrderState.AT_PICKUP,
            OrderState.PICKED_UP,
            OrderState.IN_TRANSIT,
        ):
            _advance_order(db, orders[2], state, f"order.{state.value}")

    if len(orders) >= 4:
        _advance_order(db, orders[3], OrderState.DISPATCH_READY, "order.dispatch_ready")
        _advance_order(db, orders[3], OrderState.DRIVER_ASSIGNED, "order.driver_assigned")
        if driver_id:
            orders[3].assigned_driver_id = driver_id
            db.commit()
            db.refresh(orders[3])
        for state in (
            OrderState.DRIVER_ACCEPTED,
            OrderState.DRIVER_EN_ROUTE,
            OrderState.AT_PICKUP,
            OrderState.PICKED_UP,
            OrderState.IN_TRANSIT,
            OrderState.AT_DESTINATION,
            OrderState.DELIVERED,
        ):
            _advance_order(db, orders[3], state, f"order.{state.value}")

    db.commit()


def seed_ops_data(
    db,
    ctx: AdminContext,
    *,
    customer: Customer,
    merchant: Merchant,
    orders: list[Order],
    drivers: list,
) -> None:
    claims = AdminClaimsService()
    support = AdminSupportService()
    notify = NotificationEngine()

    if orders:
        claims.open_claim(
            db,
            ctx,
            order_id=orders[0].id,
            claim_type="damaged_parcel",
            description="Corner crushed — seed claim for admin review",
            priority="high",
        )
        support.create_ticket(
            db,
            ctx,
            subject="Where is my delivery?",
            description="Customer asking for ETA on seed order",
            priority="normal",
            category="delivery_status",
            order_id=orders[0].id,
            customer_id=customer.id,
        )
        support.create_ticket(
            db,
            ctx,
            subject="Merchant billing question",
            description="NET_30 invoice timing for seed merchant",
            priority="low",
            category="billing",
            merchant_id=merchant.id,
        )
        RetryQueue.enqueue(
            db,
            direction="outbound",
            kind="order",
            order_id=orders[0].id,
            payload={"order_id": orders[0].id, "seed": True},
            idempotency_key=f"seed:sync:{orders[0].id}",
        )
        notify.dispatch(
            db,
            event_type=None,
            template_key="order_booked",
            channel="in_app",
            recipient_type="customer",
            recipient_id=customer.id,
            context={
                "order_number": orders[0].order_number,
                "tracking_number": orders[0].tracking_number,
            },
        )
        payment = db.query(Payment).filter(Payment.order_id == orders[0].id).first()
        db.add(
            BillingLedgerEntry(
                kind="payment_settled",
                payment_id=payment.id if payment else None,
                order_id=orders[0].id,
                merchant_id=merchant.id,
                amount_cents=orders[0].amount_cents,
                metadata_json={"seed": True},
            )
        )

    if drivers:
        driver = drivers[0]
        db.add(
            DriverLocationPing(
                driver_id=driver.id,
                lat=43.65,
                lng=-79.38,
                accuracy_m=8.0,
                speed_mps=8.9,
                heading=180.0,
            )
        )
        db.add(
            DriverWalletTransaction(
                driver_id=driver.id,
                tx_type="delivery_payout",
                amount_cents=3200,
                balance_after_cents=driver.wallet_balance_cents,
                description="Seed payout",
            )
        )
        db.add(
            DriverBonus(
                driver_id=driver.id,
                title="On-time streak bonus",
                amount_cents=1500,
                status="available",
                criteria={"deliveries": 10},
            )
        )

    if not db.query(BookingDraft).filter(BookingDraft.session_id == "seed-draft-session").first():
        db.add(
            BookingDraft(
                session_id="seed-draft-session",
                state="DRAFT",
                current_step="details",
                expires_at=_now() + timedelta(hours=24),
                pickup=PICKUP.model_dump(),
                dropoff=DROPOFF.model_dump(),
                vehicle_class="cargo_van",
            )
        )

    if not db.query(Lead).filter(Lead.email == "website-lead@seed.porterchain.com").first():
        db.add(
            Lead(
                source="website_booking",
                email="website-lead@seed.porterchain.com",
                phone="+1 416-555-0888",
            )
        )

    db.commit()


def main() -> None:
    init_db()
    settings = get_settings()
    db = SessionLocal()
    try:
        if seed_complete(db):
            print("Local dev seed data already present — skipping.")
            print("  Marker: BookingDraft 'seed-draft-session'")
            founder = ensure_founder_super_admin(db)
            if founder:
                print(f"  Founder super_admin ensured: {founder.email}")
            return

        print("Seeding Porterchain local dev data...")
        ensure_pricing_tariff(db)

        seed_portal_main = _seed_portal.main

        print("  → Merchant + driver portal accounts")
        seed_portal_main()

        admin = ensure_admin(db)
        founder = ensure_founder_super_admin(db)
        ctx = AdminContext(user=admin, role=AdminRole.SUPER_ADMIN)

        merchant = db.query(Merchant).filter(Merchant.clerk_org_id == DEV_ORG).first()
        if not merchant:
            raise RuntimeError("Dev merchant missing after portal seed")
        merchant_user = db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant.id).first()
        from porterchain_api.admin_models import Driver

        drivers = db.query(Driver).filter(Driver.status == DriverStatus.APPROVED.value).limit(3).all()

        print("  → Retail + merchant orders")
        removed = cleanup_partial_seed_orders(db)
        if removed:
            print(f"    (cleaned {removed} partial seed orders)")
        customer, retail1 = create_retail_order(db, settings, label="retail-1", pickup=PICKUP, dropoff=DROPOFF)
        _, retail2 = create_retail_order(db, settings, label="retail-2", pickup=PICKUP2, dropoff=DROPOFF2)
        merch1 = create_merchant_order(db, settings, merchant, merchant_user, label="m-1")
        merch2 = create_merchant_order(db, settings, merchant, merchant_user, label="m-2")
        orders = [retail1, retail2, merch1, merch2]
        driver_id = drivers[0].id if drivers else None
        create_order_variants(db, orders, driver_id)

        print("  → Claims, support, routes, notifications, fleetbase sync")
        seed_ops_data(db, ctx, customer=customer, merchant=merchant, orders=orders, drivers=drivers)

        print()
        print("=== Local dev seed complete ===")
        print(f"  Admin staff : {admin.email} (role: super_admin)")
        if founder:
            print(f"  Founder     : {founder.email} (role: super_admin)")
        print(f"  Merchant    : {merchant.company_name} ({merchant.email})")
        print(f"  Orders      : {len(orders)}")
        print(f"  Drivers     : {len(drivers)}")
        print()
        print("Open admin:  http://localhost:3002/dashboard")
        print("Merchant:    http://localhost:3001")
        print("Website:     http://localhost:3000")
        print("API docs:    http://localhost:8001/docs")
    finally:
        db.close()


if __name__ == "__main__":
    main()
