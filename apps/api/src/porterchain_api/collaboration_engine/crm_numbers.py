"""CRM number generation and quote totals."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_helpers import _today



class CrmNumbersMixin:
    def _next_number(self, db: Session, model, attr: str, prefix: str) -> str:
        year = _today().year
        count = db.query(func.count()).select_from(model).scalar() or 0
        return f"{prefix}-{year}-{count + 1:04d}"

    @staticmethod
    def _quote_totals(line_items: list[dict], tax_cents: int) -> tuple[int, int]:
        subtotal = 0
        for item in line_items:
            amount = item.get("amount_cents")
            if not amount:
                amount = int(item.get("quantity", 1) * item.get("unit_price_cents", 0))
                item["amount_cents"] = amount
            subtotal += amount
        return subtotal, subtotal + tax_cents
