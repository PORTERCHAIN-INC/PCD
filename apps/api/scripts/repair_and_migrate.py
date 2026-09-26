#!/usr/bin/env python3
"""Repair common Alembic drift on production and apply pending migrations."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

# Allow `from ensure_production_basics import ...` when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from porterchain_api.db import Base, SessionLocal, engine

# Tables required for public website quote/checkout flows.
CRITICAL_TABLES = (
    "quotes",
    "booking_drafts",
    "booking_draft_audits",
    "domain_events",
    "visitor_sessions",
    "pricing_tariffs",
    "pricing_zones",
    "promotions",
    "system_config",
)


def _table_exists(name: str) -> bool:
    return inspect(engine).has_table(name)


def _missing_critical() -> list[str]:
    return [name for name in CRITICAL_TABLES if not _table_exists(name)]


def _alembic_version() -> str | None:
    if not _table_exists("alembic_version"):
        return None
    with SessionLocal() as db:
        row = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
        return row[0] if row else None


def _load_all_models() -> None:
    """Register every SQLAlchemy model on Base.metadata (mirrors alembic/env.py)."""
    from porterchain_api import (  # noqa: F401
        admin_models,
        booking_draft_models,
        crm_models,
        driver_models,
        fleetbase_models,
        identity_models,
        invitation_models,
        merchant_models,
        models,
        user_models,
    )
    from porterchain_api.billing_engine import models as billing_models  # noqa: F401
    from porterchain_api.notification_engine import models as notification_models  # noqa: F401


def _create_missing_tables() -> None:
    _load_all_models()
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("repair: create_all(checkfirst=True) completed")


def _repair_quotes_columns() -> None:
    """Add columns missing from partially-applied production schemas."""
    if not _table_exists("quotes"):
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE quotes ADD COLUMN IF NOT EXISTS consent JSON"))
    print("repair: quotes column drift patched (consent)")


def _smoke_pricing() -> None:
    """Verify pricing repository can load DB context (catches missing promotions etc.)."""
    from datetime import UTC, datetime

    from porterchain_api.pricing_engine import get_pricing_service
    from porterchain_pricing.types import GeoPoint, PricingRequest

    with SessionLocal() as db:
        request = PricingRequest(
            pickup=GeoPoint(lat=43.65, lng=-79.38, formatted="repair smoke pickup"),
            dropoff=GeoPoint(lat=43.66, lng=-79.40, formatted="repair smoke dropoff"),
            vehicle_class="cargo_van",
            scheduled_at=datetime.now(UTC),
        )
        breakdown = get_pricing_service(db).calculate_retail(request)
        if breakdown.final_cents <= 0:
            raise RuntimeError("smoke pricing returned zero final_cents")
        print(f"repair: smoke pricing OK final_cents={breakdown.final_cents}")


def _repair_partial_initial_migration() -> bool:
    """Drop orphaned first table so the initial migration can run from scratch."""
    if not _table_exists("abandoned_checkouts"):
        return False
    if _table_exists("quotes"):
        return False
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS abandoned_checkouts CASCADE"))
    print("repair: dropped orphaned abandoned_checkouts (partial initial migration)")
    return True


def _is_duplicate_table_error(err: str) -> bool:
    lowered = err.lower()
    return "duplicatetable" in lowered or "already exists" in lowered


def _stamp_head(cfg) -> None:
    from alembic import command

    command.stamp(cfg, "head")
    print("repair: stamped alembic head")


def _upgrade_head(cfg) -> None:
    from alembic import command

    command.upgrade(cfg, "head")
    print("repair: alembic upgrade head OK")


def _ensure_schema() -> bool:
    missing = _missing_critical()
    if not missing:
        return True
    print(f"repair: missing critical tables: {missing}")
    _create_missing_tables()
    missing = _missing_critical()
    if missing:
        print(f"repair: FATAL still missing after create_all: {missing}", file=sys.stderr)
        return False
    return True


def main() -> int:
    version = _alembic_version()
    missing = _missing_critical()
    print(f"repair: alembic_version={version!r} missing_critical={missing or 'none'}")

    _repair_partial_initial_migration()

    from alembic.config import Config

    cfg = Config("alembic.ini")

    try:
        _upgrade_head(cfg)
    except Exception as exc:
        err = str(exc)
        print(f"repair: alembic upgrade failed: {err}", file=sys.stderr)
        # DB may already be stamped to a revision the running image hasn't baked yet
        # (stale layer / partial image). If critical tables exist, continue.
        if "Can't locate revision" in err and not _missing_critical():
            print(
                "repair: alembic_version unknown to this image but critical schema present — continuing",
                file=sys.stderr,
            )
        elif not _is_duplicate_table_error(err):
            return 1
        else:
            print("repair: duplicate table — filling gaps with create_all(checkfirst=True)")
            if not _ensure_schema():
                return 1
            if _alembic_version() is None:
                _stamp_head(cfg)
            else:
                try:
                    _upgrade_head(cfg)
                except Exception as exc2:
                    if "Can't locate revision" in str(exc2) and not _missing_critical():
                        print(
                            "repair: revision still unknown after create_all; schema OK — continuing",
                            file=sys.stderr,
                        )
                    elif not _is_duplicate_table_error(str(exc2)):
                        print(f"repair: upgrade after create_all failed: {exc2}", file=sys.stderr)
                        return 1
                    else:
                        _stamp_head(cfg)

    if not _ensure_schema():
        return 1
    if _alembic_version() is None:
        _stamp_head(cfg)

    from ensure_production_basics import ensure_production_basics

    ensure_production_basics()

    _repair_quotes_columns()

    try:
        _smoke_pricing()
    except Exception as exc:
        print(f"repair: smoke pricing failed: {exc}", file=sys.stderr)
        return 1

    print("repair: schema OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
