"""Admin-editable margin estimates (Settings key ``pricing_margin_estimates``)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import SystemConfig
from porterchain_pricing.margin import normalize_margin_estimates


def load_margin_estimates(db: Session) -> dict[str, Any]:
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.key == "pricing_margin_estimates")
        .first()
    )
    try:
        return normalize_margin_estimates(row.value if row else None)
    except ValueError:
        return normalize_margin_estimates(None)
