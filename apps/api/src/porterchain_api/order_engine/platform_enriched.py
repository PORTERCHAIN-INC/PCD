"""Enriched order list and duplicate detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import Session, aliased

from porterchain_api.booking_models import Customer, Invoice, Order, Payment, Quote
from porterchain_api.order_engine.buckets import HIGH_PRIORITY_CENTS, WORK_QUEUES
from porterchain_api.order_engine.filters import OrderFilters
from porterchain_api.platform.pagination import as_page, clamp_page

_INVOICED_STATES = ("INVOICED", "CLOSED")


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class OrderPlatformEnrichedMixin:
    def _filtered_query(self, db: Session, filters: OrderFilters):
        q = db.query(Order)
        if filters.sandbox_only:
            q = q.filter(Order.is_sandbox.is_(True))
        elif not filters.include_sandbox:
            q = q.filter(Order.is_sandbox.is_(False))
        if filters.state:
            q = q.filter(Order.state == filters.state)
        elif filters.queue:
            states = WORK_QUEUES.get(filters.queue)
            if states is None:
                raise ValueError("invalid_queue")
            q = q.filter(Order.state.in_(states))
        if filters.merchant_id:
            q = q.filter(Order.merchant_id == filters.merchant_id)
        if filters.driver_id:
            q = q.filter(Order.assigned_driver_id == filters.driver_id)
        if filters.customer_id:
            q = q.filter(Order.customer_id == filters.customer_id)
        q = self._apply_date_window(q, filters)
        if filters.amount_min_cents is not None:
            q = q.filter(Order.amount_cents >= filters.amount_min_cents)
        if filters.amount_max_cents is not None:
            q = q.filter(Order.amount_cents <= filters.amount_max_cents)
        if filters.search:
            like = f"%{filters.search}%"
            customer_ids = [c.id for c in db.query(Customer).filter(Customer.email.ilike(like)).limit(100).all()]
            clauses = [
                Order.tracking_number.ilike(like),
                Order.order_number.ilike(like),
                Order.purchase_order_number.ilike(like),
                Order.internal_reference.ilike(like),
                Order.cost_centre.ilike(like),
            ]
            if customer_ids:
                clauses.append(Order.customer_id.in_(customer_ids))
            q = q.filter(or_(*clauses))
        if filters.city:
            city_like = f"%{filters.city.lower()}%"
            q = q.filter(
                or_(
                    func.lower(func.json_extract_path_text(Order.pickup, "city")).like(city_like),
                    func.lower(func.json_extract_path_text(Order.dropoff, "city")).like(city_like),
                )
            )
        if filters.priority == "high":
            q = q.filter(Order.amount_cents >= HIGH_PRIORITY_CENTS)
        elif filters.priority == "normal":
            q = q.filter(Order.amount_cents < HIGH_PRIORITY_CENTS)
        if filters.service_type:
            q = q.filter(
                exists().where(and_(Quote.id == Order.quote_id, Quote.vehicle_class == filters.service_type))
            )
        if filters.invoice_status == "generated":
            q = q.filter(or_(exists().where(Invoice.order_id == Order.id), Order.state.in_(_INVOICED_STATES)))
        elif filters.invoice_status == "none":
            q = q.filter(~exists().where(Invoice.order_id == Order.id), Order.state.notin_(_INVOICED_STATES))
        if filters.payment_status:
            q = q.filter(self._payment_status_clause(filters.payment_status))
        return q.order_by(Order.updated_at.desc(), Order.id.desc())

    def _apply_date_window(self, q, filters: OrderFilters):
        if filters.date_field not in (None, "", "created", "scheduled"):
            raise ValueError("invalid_date_field")
        if not filters.date_from and not filters.date_to:
            return q
        column = Order.scheduled_at if filters.date_field == "scheduled" else Order.created_at
        start = _as_utc(filters.date_from)
        end = _as_utc(filters.date_to)
        parts = []
        if start is not None:
            parts.append(column >= start)
        if end is not None:
            parts.append(column <= end)
        window = and_(*parts)
        if filters.include_carryover and start is not None and filters.date_field == "scheduled":
            return q.filter(or_(window, column < start))
        return q.filter(window)

    def _payment_status_clause(self, status: str):
        """Latest payment on the order, else latest payment on the quote."""
        by_order = aliased(Payment)
        newer_order = aliased(Payment)
        by_quote = aliased(Payment)
        newer_quote = aliased(Payment)
        any_order_pay = aliased(Payment)
        latest_on_order = exists().where(
            and_(
                by_order.order_id == Order.id,
                by_order.status == status,
                ~exists().where(
                    and_(
                        newer_order.order_id == Order.id,
                        newer_order.created_at > by_order.created_at,
                    )
                ),
            )
        )
        latest_on_quote = and_(
            ~exists().where(any_order_pay.order_id == Order.id),
            Order.quote_id.isnot(None),
            exists().where(
                and_(
                    by_quote.quote_id == Order.quote_id,
                    by_quote.status == status,
                    ~exists().where(
                        and_(
                            newer_quote.quote_id == Order.quote_id,
                            newer_quote.created_at > by_quote.created_at,
                        )
                    ),
                )
            ),
        )
        return or_(latest_on_order, latest_on_quote)

    def list_page(self, db: Session, filters: OrderFilters) -> dict[str, Any]:
        limit, offset = clamp_page(filters.limit, filters.offset)
        q = self._filtered_query(db, filters)
        total = q.count()
        merchants = self._merchant_map(db)
        drivers = self._driver_map(db)
        rows = [self._row(db, order, merchants, drivers) for order in q.offset(offset).limit(limit).all()]
        return as_page(rows, total, limit, offset)

    def list_enriched(self, db: Session, filters: OrderFilters) -> list[dict[str, Any]]:
        return self.list_page(db, filters)["items"]

    def find_duplicates(self, db: Session, order: Order) -> list[dict[str, Any]]:
        if not order.customer_id:
            return []
        window = order.created_at - timedelta(hours=24) if order.created_at else None
        q = db.query(Order).filter(
            Order.customer_id == order.customer_id,
            Order.id != order.id,
            Order.amount_cents == order.amount_cents,
        )
        if window:
            q = q.filter(Order.created_at >= window)
        return [
            {"order_id": o.id, "order_number": o.order_number, "tracking_number": o.tracking_number, "state": o.state}
            for o in q.limit(10).all()
        ]
