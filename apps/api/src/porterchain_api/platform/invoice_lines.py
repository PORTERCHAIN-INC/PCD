"""Invoice line helpers — admin e2e / finance may call without importing billing_engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def ensure_invoice_line(db: Session, invoice: Any, order: Any) -> Any:
    from porterchain_api.billing_engine.invoice_document import (
        ensure_invoice_line as _ensure,
    )

    return _ensure(db, invoice, order)
