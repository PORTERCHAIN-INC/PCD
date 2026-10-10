"""BD — one outstanding number: admin 360 = merchant Billing = collections."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from porterchain_api.admin_engine.finance_service import AdminFinanceService
from porterchain_api.admin_engine.merchant360_service import Merchant360Service
from porterchain_api.billing_engine.ar import merchant_ar
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.booking_models import Invoice, Order

UNINVOICED_CENTS = 22_500
INVOICED_CENTS = 40_000
INVOICE_FEES_CENTS = 1_500
CREDIT_CENTS = 5_000


def _ctx(db, merchant: Merchant) -> MerchantContext:
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"user_ar_{uuid.uuid4().hex[:10]}",
        email=f"ar_{uuid.uuid4().hex[:8]}@ar.test",
        role=MerchantRole.OWNER.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def _order(db, merchant: Merchant, *, cents: int, state: str) -> Order:
    order = Order(
        merchant_id=merchant.id,
        state=state,
        amount_cents=cents,
        currency="cad",
        payment_terms="NET_30",
        order_number=f"AR-{uuid.uuid4().hex[:8].upper()}",
        tracking_number=f"TRK{uuid.uuid4().hex[:10].upper()}",
        pickup={"formatted": "100 King St W, Toronto"},
        dropoff={"formatted": "200 Bay St, Toronto"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def _books(db) -> tuple[Merchant, MerchantContext]:
    """A merchant with one open invoice, one uninvoiced delivery, and one credit note."""
    merchant = Merchant(
        status=MerchantStatus.ACTIVE.value,
        company_name="AR Parity Co",
        email=f"ar_{uuid.uuid4().hex[:10]}@parity.test",
        payment_terms="NET_30",
        billing_cycle="MONTHLY",
    )
    db.add(merchant)
    db.flush()

    invoiced_order = _order(db, merchant, cents=INVOICED_CENTS, state=OrderState.INVOICED.value)
    db.add(
        Invoice(
            invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
            order_id=invoiced_order.id,
            merchant_id=merchant.id,
            amount_cents=INVOICED_CENTS,
            tax_cents=0,
            fees_cents=INVOICE_FEES_CENTS,
            currency="cad",
            due_at=datetime.now(UTC) + timedelta(days=20),
        )
    )

    _order(db, merchant, cents=UNINVOICED_CENTS, state=OrderState.DELIVERED.value)
    # Cancelled work is never billable, so it must not land in AR.
    _order(db, merchant, cents=99_900, state=OrderState.CANCELLED.value)

    db.add(
        BillingLedgerEntry(
            kind="credit_note",
            merchant_id=merchant.id,
            order_id=invoiced_order.id,
            amount_cents=CREDIT_CENTS,
            currency="cad",
            status="issued",
            metadata_json={"reason": "Late delivery"},
        )
    )
    db.commit()
    return merchant, _ctx(db, merchant)


def test_ar_is_invoiced_plus_uninvoiced_minus_credits(db) -> None:
    merchant, _ctx_ = _books(db)
    ar = merchant_ar(db, merchant)

    assert ar.invoiced_cents == INVOICED_CENTS + INVOICE_FEES_CENTS
    assert ar.uninvoiced_cents == UNINVOICED_CENTS
    assert ar.credits_cents == CREDIT_CENTS
    assert ar.outstanding_cents == (
        INVOICED_CENTS + INVOICE_FEES_CENTS + UNINVOICED_CENTS - CREDIT_CENTS
    )


def test_admin_360_and_merchant_billing_quote_the_same_cents(db) -> None:
    merchant, ctx = _books(db)
    ar = merchant_ar(db, merchant)

    metrics = Merchant360Service()._metrics(db, merchant, None)
    overview = MerchantBillingService().overview(db, ctx)
    summary = MerchantBillingService().statement_summary(db, ctx)

    assert metrics["outstanding_balance_cents"] == ar.outstanding_cents
    assert overview["outstanding_balance_cents"] == ar.outstanding_cents
    assert summary["outstanding_balance_cents"] == ar.outstanding_cents
    assert MerchantBillingService().outstanding_balance(db, ctx) == ar.outstanding_cents

    # Same breakdown, not just the same total.
    assert overview["outstanding_invoices_cents"] == ar.invoiced_cents
    assert overview["uninvoiced_orders_cents"] == ar.uninvoiced_cents
    assert overview["credit_notes_cents"] == ar.credits_cents


def test_merchant_dashboard_shows_the_same_number(db) -> None:
    from porterchain_api.merchant_engine.dashboard_service import MerchantDashboardService

    merchant, ctx = _books(db)
    ar = merchant_ar(db, merchant)
    dash = MerchantDashboardService().get_dashboard(db, ctx)

    assert dash["outstanding_balance_cents"] == ar.outstanding_cents
    assert dash["account_balance_cents"] == ar.outstanding_cents
    # The invoices key must be the invoiced slice, not the whole balance.
    assert dash["outstanding_invoices_cents"] == ar.invoiced_cents


def test_collections_agrees_on_the_invoiced_portion(db) -> None:
    merchant, _ctx_ = _books(db)
    ar = merchant_ar(db, merchant)

    rows = [
        r
        for r in AdminFinanceService().collections(db)
        if r.get("merchant_id") == merchant.id
    ]
    assert rows, "the open invoice should be collectable"
    assert sum(int(r["outstanding_cents"]) for r in rows) == ar.invoiced_cents
    assert all("days_overdue" in r for r in rows)


def test_collections_lists_every_open_invoice_not_just_the_last(db) -> None:
    merchant, _ctx_ = _books(db)
    for _ in range(2):
        extra = _order(db, merchant, cents=10_000, state=OrderState.INVOICED.value)
        db.add(
            Invoice(
                invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
                order_id=extra.id,
                merchant_id=merchant.id,
                amount_cents=10_000,
                tax_cents=0,
                fees_cents=0,
                currency="cad",
                due_at=datetime.now(UTC) - timedelta(days=5),
            )
        )
    db.commit()

    rows = [
        r
        for r in AdminFinanceService().collections(db)
        if r.get("merchant_id") == merchant.id
    ]
    assert len(rows) == 3
    assert sum(int(r["outstanding_cents"]) for r in rows) == merchant_ar(db, merchant).invoiced_cents
    assert [r for r in rows if r["days_overdue"] > 0], "overdue invoices report aging"


def test_collections_never_crashes_without_open_invoices(db) -> None:
    # The whole list must survive a book with nothing collectable.
    rows = AdminFinanceService().collections(db)
    assert isinstance(rows, list)


def test_crm_sales_ar_stays_out_of_delivery_ar(db) -> None:
    merchant, _ctx_ = _books(db)
    metrics = Merchant360Service()._metrics(db, merchant, None)
    ar = merchant_ar(db, merchant)

    # CRM sales invoices live on their own key and never inflate delivery AR.
    assert metrics["crm_outstanding_balance_cents"] == 0
    assert metrics["outstanding_balance_cents"] == ar.outstanding_cents
