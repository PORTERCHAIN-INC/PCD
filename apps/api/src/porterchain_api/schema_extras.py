"""Database-level objects that live outside the per-table ORM classes.

These indexes already exist in every database (created by earlier migrations) but are
not expressible as plain ``index=True`` columns: partial unique indexes, functional
indexes, GIN indexes and DESC composite indexes. Declaring them here keeps
``alembic check`` honest (model == migrations) without touching each model file.

Also holds :class:`LegacyExternalRef`, the read-only archive of retired Fleetbase ids
written by migration ``fx0retirefleet5e6f``. Nothing writes to it at runtime; it is kept
so the retired ids stay recoverable (that migration's downgrade restores from it).

Import this module after all model modules (``alembic/env.py`` does).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from porterchain_api.db import Base


class LegacyExternalRef(Base):
    __tablename__ = "legacy_external_refs"
    __table_args__ = (Index("ix_legacy_external_refs_entity", "entity", "entity_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32))
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    field: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FkOrphanQuarantine(Base):
    """Rows/values that pointed at a missing parent when migration ``dm2fkorphan0002``
    added the foreign keys. ``action='nulled'``: the column was set to NULL;
    ``action='moved'``: the whole row was taken out of the live table (``row_data``).
    Review with ``SELECT * FROM fk_orphan_quarantine``; downgrade restores everything."""

    __tablename__ = "fk_orphan_quarantine"
    __table_args__ = (Index("ix_fk_orphan_quarantine_table", "table_name", "column_name"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(64))
    column_name: Mapped[str] = mapped_column(String(64))
    row_pk: Mapped[str] = mapped_column(String(64))
    bad_value: Mapped[str] = mapped_column(String(128))
    row_data: Mapped[dict] = mapped_column(JSONB)
    action: Mapped[str] = mapped_column(String(16))
    quarantined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def _t(name: str):
    return Base.metadata.tables[name]


def _register() -> None:
    md = Base.metadata
    if getattr(md, "_pc_schema_extras", False):
        return
    md._pc_schema_extras = True  # type: ignore[attr-defined]

    Index("ix_ai_usage_logs_created_at", _t("ai_usage_logs").c.created_at)
    Index(
        "uq_billing_ledger_idempotency_key",
        _t("billing_ledger_entries").c.idempotency_key,
        unique=True,
        postgresql_where=text("idempotency_key IS NOT NULL"),
    )
    for table, col in (("crm_companies", "address"), ("crm_leads", "address"), ("crm_leads", "custom_fields")):
        Index(
            f"ix_{table}_{col}_gin",
            _t(table).c[col],
            postgresql_using="gin",
            postgresql_ops={col: "jsonb_path_ops"},
        )
    Index(
        "uq_crm_leads_quote_id",
        _t("crm_leads").c.quote_id,
        unique=True,
        postgresql_where=text("quote_id IS NOT NULL"),
    )
    Index("uq_customers_email_lower", func.lower(_t("customers").c.email), unique=True)
    Index("uq_dispatch_stop_events_client_id", _t("dispatch_stop_events").c.client_id, unique=True)
    Index(
        "ix_domain_events_type_occurred",
        _t("domain_events").c.event_type,
        _t("domain_events").c.occurred_at.desc(),
    )
    Index(
        "uq_drivers_crm_lead_id",
        _t("drivers").c.crm_lead_id,
        unique=True,
        postgresql_where=text("crm_lead_id IS NOT NULL"),
    )
    hst = func.regexp_replace(_t("merchants").c.hst_number, r"\D", "", "g")
    Index(
        "uq_merchants_hst_normalized",
        hst,
        unique=True,
        postgresql_where=text(
            "deleted_at IS NULL AND hst_number IS NOT NULL "
            "AND regexp_replace(hst_number::text, '\\D', '', 'g') <> ''"
        ),
    )
    orders = _t("orders")
    Index("ix_orders_merchant_state", orders.c.merchant_id, orders.c.state)
    Index("ix_orders_state_created_at", orders.c.state, orders.c.created_at.desc())
    Index(
        "uq_orders_quote_id",
        orders.c.quote_id,
        unique=True,
        postgresql_where=text("quote_id IS NOT NULL"),
    )
    Index("uq_shopify_shops_shop_domain", _t("shopify_shops").c.shop_domain, unique=True)



_register()
