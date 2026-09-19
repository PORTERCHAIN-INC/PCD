"""PostgreSQL-safe JSON column helpers for SQLAlchemy queries."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement


def json_text(column: InstrumentedAttribute[dict[str, Any]] | Any, key: str) -> ColumnElement[str]:
    """Extract a JSON object field as text (PostgreSQL JSON/JSONB)."""
    return column[key].astext


def json_text_lower(column: InstrumentedAttribute[dict[str, Any]] | Any, key: str) -> ColumnElement[str]:
    return func.lower(json_text(column, key))
