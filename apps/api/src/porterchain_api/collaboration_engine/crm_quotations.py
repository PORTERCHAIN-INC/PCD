"""CRM quotations."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_helpers import _today


class CrmQuotationsMixin:
    def _next_number(self, db: Session, model, attr: str, prefix: str) -> str:
        year = _today().year
        count = db.query(func.count()).select_from(model).scalar() or 0
        return f"{prefix}-{year}-{count + 1:04d}"
