"""TaxRegistration rows owned by admin_engine (§3.2.3); platform.tax_registration delegates."""

from __future__ import annotations

from typing import Any

from porterchain_api.admin_models import TaxRegistration


def registration_rows(db: Any) -> list[Any]:
    return (
        db.query(TaxRegistration)
        .order_by(TaxRegistration.effective_from.asc(), TaxRegistration.created_at.asc())
        .all()
    )


def add_registration(db: Any, **fields: Any) -> Any:
    row = TaxRegistration(**fields)
    db.add(row)
    db.flush()
    return row
