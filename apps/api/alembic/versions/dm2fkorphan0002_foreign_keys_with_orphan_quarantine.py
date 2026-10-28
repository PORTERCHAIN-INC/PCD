"""Add the missing foreign keys (and their indexes), quarantining orphan rows first.

Revision ID: dm2fkorphan0002
Revises: dm1driftfix0001

For every ``<table>.<col> -> <target>.id`` below:

1. Orphans (value set but no matching target row) are copied into ``fk_orphan_quarantine``
   (table, column, the row's primary key, the bad value, the whole row as JSON, action).
2. Nullable column: the bad value is set to NULL (action='nulled').
   NOT NULL column: the row is removed from the live table (action='moved'); it stays
   in quarantine as JSON and can be re-inserted (downgrade does exactly that).
   Nothing is ever deleted without a full copy, and the counts are printed.
3. The FK is added ``NOT VALID`` and then ``VALIDATE``d (short lock, see docs/migrations).
4. A btree index is created on the column when none existed.

Also adds the indexes ``orders.customer_id``, ``quotes.customer_id``, ``leads.quote_id``
and ``leads.customer_id``.

Downgrade drops the FKs and new indexes, then restores every quarantined value/row and
drops ``fk_orphan_quarantine``, returning the data to its exact pre-upgrade state.

Not linked on purpose (documented in docs/data/FK_DECISIONS.md): polymorphic
``notification_*.user_id`` (role + id of merchant/driver/customer/staff), synthetic
``dispatch_routes.vehicle_id`` / ``driver_shifts.route_id``, the anonymous
``visitor_session_id`` cookie key (quotes/customers/crm_leads: written before, or without,
a ``visitor_sessions`` row), and Stripe's external
``stripe_payouts.stripe_payout_id``.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "dm2fkorphan0002"
down_revision = "dm1driftfix0001"
branch_labels = None
depends_on = None

FKS: tuple[tuple[str, str, str, str], ...] = (
 ("abandoned_checkouts","quote_id","quotes","CASCADE"),
 ("abandoned_checkouts","customer_id","customers","SET NULL"),
 ("billing_ledger_entries","payment_id","payments","RESTRICT"),
 ("billing_ledger_entries","order_id","orders","RESTRICT"),
 ("billing_ledger_entries","merchant_id","merchants","RESTRICT"),
 ("booking_attachment_events","order_id","orders","SET NULL"),
 ("booking_attachments","merchant_id","merchants","SET NULL"),
 ("booking_attachments","customer_id","customers","SET NULL"),
 ("booking_drafts","booking_id","bookings","SET NULL"),
 ("booking_drafts","order_id","orders","SET NULL"),
 ("crm_companies","merchant_id","merchants","SET NULL"),
 ("crm_contracts","company_id","crm_companies","SET NULL"),
 ("crm_invoices","company_id","crm_companies","SET NULL"),
 ("crm_quotations","company_id","crm_companies","SET NULL"),
 ("crm_sales_tasks","company_id","crm_companies","SET NULL"),
 ("crm_referral_credits","company_id","crm_companies","SET NULL"),
 ("crm_leads","company_id","crm_companies","SET NULL"),
 ("crm_lead_ingest_events","lead_id","crm_leads","SET NULL"),
 ("crm_referral_credits","lead_id","crm_leads","SET NULL"),
 ("crm_suppressions","lead_id","crm_leads","SET NULL"),
 ("marketing_subscribers","lead_id","crm_leads","SET NULL"),
 ("crm_leads","quote_id","quotes","SET NULL"),
 ("crm_leads","booking_draft_id","booking_drafts","SET NULL"),
 ("crm_leads","order_id","orders","SET NULL"),
 ("customer_credits","order_id","orders","SET NULL"),
 ("visitor_sessions","customer_id","customers","SET NULL"),
 ("driver_incidents","order_id","orders","SET NULL"),
 ("driver_stop_meta","order_id","orders","CASCADE"),
 ("driver_stop_meta","driver_id","drivers","CASCADE"),
 ("finance_reminder_drafts","merchant_id","merchants","CASCADE"),
 ("interac_transfers","merchant_id","merchants","RESTRICT"),
 ("interac_transfers","payment_id","payments","SET NULL"),
 ("merchant_contracts","crm_contract_id","crm_contracts","SET NULL"),
 ("pricing_fsa_rates","merchant_id","merchants","CASCADE"),
 ("pricing_tariffs","merchant_id","merchants","CASCADE"),
 ("promotions","merchant_id","merchants","CASCADE"),
 ("user_invitations","merchant_id","merchants","CASCADE"),
 ("privacy_deletion_jobs","customer_id","customers","SET NULL"),
 ("reorder_nudges","order_id","orders","CASCADE"),
)

#: Index created by this migration (column had none before).
NEW_INDEXES: tuple[tuple[str, str], ...] = (
    ("abandoned_checkouts", "customer_id"),
    ("marketing_subscribers", "lead_id"),
    ("customer_credits", "order_id"),
    ("interac_transfers", "payment_id"),
    ("reorder_nudges", "order_id"),
    ("orders", "customer_id"),
    ("quotes", "customer_id"),
    ("leads", "quote_id"),
    ("leads", "customer_id"),
)

QUARANTINE = "fk_orphan_quarantine"


def fk_name(table: str, column: str) -> str:
    return f"fk_{table}_{column}"[:63]


def _not_null(bind, table: str, column: str) -> bool:
    return not next(c for c in sa.inspect(bind).get_columns(table) if c["name"] == column)["nullable"]


def quarantine_orphans(bind, table: str, column: str, target: str) -> tuple[int, str]:
    """Copy orphans of ``table.column`` into quarantine, then NULL them or move them out."""
    orphan = (
        f"t.{column} IS NOT NULL AND NOT EXISTS "
        f"(SELECT 1 FROM {target} x WHERE x.id = t.{column})"
    )
    action = "moved" if _not_null(bind, table, column) else "nulled"
    n = bind.execute(
        sa.text(
            f"INSERT INTO {QUARANTINE} (table_name, column_name, row_pk, bad_value, row_data, action) "
            f"SELECT :t, :c, t.id::text, t.{column}::text, to_jsonb(t), :a FROM {table} t WHERE {orphan}"
        ),
        {"t": table, "c": column, "a": action},
    ).rowcount
    if n:
        if action == "moved":
            bind.execute(sa.text(f"DELETE FROM {table} t WHERE {orphan}"))
        else:
            bind.execute(sa.text(f"UPDATE {table} t SET {column} = NULL WHERE {orphan}"))
        print(f"[dm2fkorphan0002] {table}.{column}: {n} orphan row(s) {action} (see {QUARANTINE})")
    return n, action


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        QUARANTINE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.String(64), nullable=False),
        sa.Column("column_name", sa.String(64), nullable=False),
        sa.Column("row_pk", sa.String(64), nullable=False),
        sa.Column("bad_value", sa.String(128), nullable=False),
        sa.Column("row_data", postgresql.JSONB(), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fk_orphan_quarantine_table", QUARANTINE, ["table_name", "column_name"])

    for table, column, target, ondelete in FKS:
        quarantine_orphans(bind, table, column, target)
        name = fk_name(table, column)
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {name} FOREIGN KEY ({column}) "
            f"REFERENCES {target} (id) ON DELETE {ondelete} NOT VALID"
        )
        op.execute(f"ALTER TABLE {table} VALIDATE CONSTRAINT {name}")

    for table, column in NEW_INDEXES:
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    bind = op.get_bind()
    for table, column in reversed(NEW_INDEXES):
        op.drop_index(f"ix_{table}_{column}", table_name=table)
    for table, column, _target, _ondelete in reversed(FKS):
        op.drop_constraint(fk_name(table, column), table, type_="foreignkey")

    # Restore quarantined data exactly: moved rows back in, nulled values back.
    rows = bind.execute(
        sa.text(f"SELECT table_name, column_name, row_pk, bad_value, action FROM {QUARANTINE} ORDER BY id")
    ).all()
    for table, column, row_pk, bad_value, action in rows:
        if action == "moved":
            bind.execute(
                sa.text(
                    f"INSERT INTO {table} SELECT (jsonb_populate_record(NULL::{table}, q.row_data)).* "
                    f"FROM {QUARANTINE} q WHERE q.table_name = :t AND q.column_name = :c AND q.row_pk = :pk "
                    "ON CONFLICT DO NOTHING"
                ),
                {"t": table, "c": column, "pk": row_pk},
            )
        else:
            bind.execute(
                sa.text(f"UPDATE {table} SET {column} = :v WHERE id::text = :pk AND {column} IS NULL"),
                {"v": bad_value, "pk": row_pk},
            )
    op.drop_index("ix_fk_orphan_quarantine_table", table_name=QUARANTINE)
    op.drop_table(QUARANTINE)
