"""Enriched order list and duplicate detection."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.models import Customer, Order
from porterchain_api.order_engine.filters import OrderFilters


class OrderPlatformEnrichedMixin:
    def list_enriched(self, db: Session, filters: OrderFilters) -> list[dict[str, Any]]:
        q = db.query(Order).order_by(Order.updated_at.desc())
        if filters.state:
            q = q.filter(Order.state == filters.state)
        if filters.merchant_id:
            q = q.filter(Order.merchant_id == filters.merchant_id)
        if filters.driver_id:
            q = q.filter(Order.assigned_driver_id == filters.driver_id)
        if filters.date_from:
            q = q.filter(Order.created_at >= filters.date_from)
        if filters.date_to:
            q = q.filter(Order.created_at <= filters.date_to)
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
            ]
            if customer_ids:
                clauses.append(Order.customer_id.in_(customer_ids))
            q = q.filter(or_(*clauses))

        merchants = self._merchant_map(db)
        drivers = self._driver_map(db)
        rows: list[dict[str, Any]] = []
        for order in q.offset(filters.offset).limit(filters.limit).all():
            row = self._row(db, order, merchants, drivers)
            if filters.payment_status and row["payment_status"] != filters.payment_status:
                continue
            if filters.invoice_status and row["invoice_status"] != filters.invoice_status:
                continue
            if filters.priority and row["priority"] != filters.priority:
                continue
            if filters.service_type and row["service_type"] != filters.service_type:
                continue
            if filters.city:
                city_like = filters.city.lower()
                pickup = (order.pickup or {}).get("city", "")
                dropoff = (order.dropoff or {}).get("city", "")
                if city_like not in str(pickup).lower() and city_like not in str(dropoff).lower():
                    continue
            rows.append(row)
        return rows

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
