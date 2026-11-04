"""Claim row writes owned by admin_engine (§3.2.3) — other modules call these."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim


def add_claim(db: Session, **fields: Any) -> Claim:
    c = Claim(**fields)
    db.add(c)
    db.flush()
    return c
