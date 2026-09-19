"""Order persistence — repository pattern with tenant scoping (DD-07)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from porterchain_api.domain.tenant_access import assert_order_visible
from porterchain_api.domain.tenant_context import TenantKind, TenantScope
from porterchain_api.booking_models import Order


def _same_text(column, value: str):
    """Case-insensitive exact match.

    Deliberately not ``ilike``: a reference someone pastes may contain ``%`` or
    ``_``, and those must be characters to match, not wildcards.
    """
    return func.lower(column) == value.lower()


class OrderRepository:
    def get_by_id(self, db: Session, order_id: str) -> Order | None:
        return db.query(Order).filter(Order.id == order_id).first()

    def get_by_quote_id(self, db: Session, quote_id: str) -> Order | None:
        return db.query(Order).filter(Order.quote_id == quote_id).first()

    def get_by_tracking(self, db: Session, tracking_number: str) -> Order | None:
        """Unscoped lookup — public retail track-by-number only."""
        return db.query(Order).filter(Order.tracking_number == tracking_number).first()

    def get_for_scope(self, db: Session, order_id: str, scope: TenantScope) -> Order | None:
        q = db.query(Order).filter(Order.id == order_id)
        q = self._apply_scope(q, scope)
        return q.first()

    def require_for_scope(self, db: Session, order_id: str, scope: TenantScope) -> Order:
        order = self.get_for_scope(db, order_id, scope)
        return assert_order_visible(order, scope)

    def get_by_tracking_for_scope(
        self,
        db: Session,
        tracking_number: str,
        scope: TenantScope,
    ) -> Order | None:
        q = db.query(Order).filter(Order.tracking_number == tracking_number)
        q = self._apply_scope(q, scope)
        return q.first()

    def require_by_tracking_for_scope(
        self,
        db: Session,
        tracking_number: str,
        scope: TenantScope,
    ) -> Order:
        order = self.get_by_tracking_for_scope(db, tracking_number, scope)
        return assert_order_visible(order, scope)

    def list_for_scope(
        self,
        db: Session,
        scope: TenantScope,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        q = db.query(Order)
        q = self._apply_scope(q, scope)
        return q.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    def get_for_merchant(self, db: Session, merchant_id: str, order_id: str) -> Order | None:
        return self.get_for_scope(db, order_id, TenantScope.merchant(merchant_id))

    def require_for_merchant(self, db: Session, merchant_id: str, order_id: str) -> Order:
        return self.require_for_scope(db, order_id, TenantScope.merchant(merchant_id))

    def get_by_tracking_for_merchant(
        self,
        db: Session,
        merchant_id: str,
        tracking_number: str,
    ) -> Order | None:
        """Case-insensitive: numbers are stored uppercase but get typed and pasted (BK)."""
        q = (tracking_number or "").strip()
        if not q:
            return None
        return (
            db.query(Order)
            .filter(Order.merchant_id == merchant_id, _same_text(Order.tracking_number, q))
            .first()
        )

    def get_by_order_number_for_merchant(
        self,
        db: Session,
        merchant_id: str,
        order_number: str,
    ) -> Order | None:
        q = (order_number or "").strip()
        if not q:
            return None
        return (
            db.query(Order)
            .filter(Order.merchant_id == merchant_id, _same_text(Order.order_number, q))
            .first()
        )

    def find_for_merchant_lookup(
        self,
        db: Session,
        merchant_id: str,
        query: str,
    ) -> list[Order]:
        """Tracking number, order number, or PO — exact, case-insensitive, company-scoped (BK).

        Tracking and order numbers are unique, so a hit on either wins outright.
        A PO is the customer's own reference and can cover several drops, so every
        match is returned newest first and the caller decides what to show.
        """
        q = (query or "").strip()
        if not q:
            return []

        exact = self.get_by_tracking_for_merchant(db, merchant_id, q) or self.get_by_order_number_for_merchant(
            db, merchant_id, q
        )
        if exact:
            return [exact]

        return (
            db.query(Order)
            .filter(
                Order.merchant_id == merchant_id,
                _same_text(Order.purchase_order_number, q),
            )
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_by_lookup_for_merchant(
        self,
        db: Session,
        merchant_id: str,
        query: str,
    ) -> Order | None:
        """First match for a tracking number, order number, or PO. Company-scoped only."""
        matches = self.find_for_merchant_lookup(db, merchant_id, query)
        return matches[0] if matches else None

    def list_for_merchant(
        self,
        db: Session,
        merchant_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        return self.list_for_scope(db, TenantScope.merchant(merchant_id), limit=limit, offset=offset)

    def get_for_customer(self, db: Session, customer_id: str, order_id: str) -> Order | None:
        return self.get_for_scope(db, order_id, TenantScope.customer(customer_id))

    def require_for_customer(self, db: Session, customer_id: str, order_id: str) -> Order:
        return self.require_for_scope(db, order_id, TenantScope.customer(customer_id))

    def list_for_customer(
        self,
        db: Session,
        customer_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        return self.list_for_scope(db, TenantScope.customer(customer_id), limit=limit, offset=offset)

    @staticmethod
    def _apply_scope(q: Query, scope: TenantScope) -> Query:
        if scope.kind == TenantKind.MERCHANT:
            return q.filter(Order.merchant_id == scope.tenant_id)
        return q.filter(Order.customer_id == scope.tenant_id)
