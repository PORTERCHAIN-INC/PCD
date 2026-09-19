"""P0a — FK integrity so jobs and AR can join."""

from alembic import op
import sqlalchemy as sa

revision = "t2u3v4w5x6y7"
down_revision = "s1t2u3v4w5x6"
branch_labels = None
depends_on = None


def _null_orphans(table: str, column: str, parent_table: str, parent_col: str = "id") -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET {column} = NULL
            WHERE {column} IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM {parent_table} p WHERE p.{parent_col} = {table}.{column}
              )
            """
        )
    )


def upgrade() -> None:
    _null_orphans("orders", "merchant_id", "merchants")
    op.create_foreign_key(
        "fk_orders_merchant_id_merchants",
        "orders",
        "merchants",
        ["merchant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    _null_orphans("orders", "assigned_driver_id", "drivers")
    op.create_foreign_key(
        "fk_orders_assigned_driver_id_drivers",
        "orders",
        "drivers",
        ["assigned_driver_id"],
        ["id"],
        ondelete="SET NULL",
    )

    for col, parent in (
        ("customer_id", "customers"),
        ("merchant_id", "merchants"),
        ("driver_id", "drivers"),
        ("order_id", "orders"),
    ):
        _null_orphans("support_tickets", col, parent)
        op.create_foreign_key(
            f"fk_support_tickets_{col}_{parent}",
            "support_tickets",
            parent,
            [col],
            ["id"],
            ondelete="SET NULL",
        )

    op.alter_column("claims", "order_id", existing_type=sa.String(length=36), nullable=True)
    op.add_column("claims", sa.Column("merchant_id", sa.String(length=36), nullable=True))
    op.create_index("ix_claims_merchant_id", "claims", ["merchant_id"])
    _null_orphans("claims", "order_id", "orders")
    _null_orphans("claims", "merchant_id", "merchants")
    op.create_foreign_key(
        "fk_claims_order_id_orders",
        "claims",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_claims_merchant_id_merchants",
        "claims",
        "merchants",
        ["merchant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    _null_orphans("leads", "quote_id", "quotes")
    _null_orphans("leads", "customer_id", "customers")
    op.create_foreign_key("fk_leads_quote_id_quotes", "leads", "quotes", ["quote_id"], ["id"])
    op.create_foreign_key(
        "fk_leads_customer_id_customers", "leads", "customers", ["customer_id"], ["id"]
    )

    op.execute(
        sa.text(
            """
            DELETE FROM identity_links
            WHERE NOT EXISTS (
                SELECT 1 FROM porterchain_users u
                WHERE u.id = identity_links.platform_user_id
            )
            """
        )
    )
    op.create_foreign_key(
        "fk_identity_links_platform_user_id",
        "identity_links",
        "porterchain_users",
        ["platform_user_id"],
        ["id"],
    )

    op.execute(
        sa.text(
            """
            DELETE FROM merchant_contracts
            WHERE NOT EXISTS (
                SELECT 1 FROM merchants m WHERE m.id = merchant_contracts.merchant_id
            )
            """
        )
    )
    op.create_foreign_key(
        "fk_merchant_contracts_merchant_id",
        "merchant_contracts",
        "merchants",
        ["merchant_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_merchant_contracts_merchant_id", "merchant_contracts", type_="foreignkey")
    op.drop_constraint("fk_identity_links_platform_user_id", "identity_links", type_="foreignkey")
    op.drop_constraint("fk_leads_customer_id_customers", "leads", type_="foreignkey")
    op.drop_constraint("fk_leads_quote_id_quotes", "leads", type_="foreignkey")
    op.drop_constraint("fk_claims_merchant_id_merchants", "claims", type_="foreignkey")
    op.drop_constraint("fk_claims_order_id_orders", "claims", type_="foreignkey")
    op.drop_index("ix_claims_merchant_id", table_name="claims")
    op.drop_column("claims", "merchant_id")
    op.alter_column("claims", "order_id", existing_type=sa.String(length=36), nullable=False)
    for col, parent in (
        ("order_id", "orders"),
        ("driver_id", "drivers"),
        ("merchant_id", "merchants"),
        ("customer_id", "customers"),
    ):
        op.drop_constraint(f"fk_support_tickets_{col}_{parent}", "support_tickets", type_="foreignkey")
    op.drop_constraint("fk_orders_assigned_driver_id_drivers", "orders", type_="foreignkey")
    op.drop_constraint("fk_orders_merchant_id_merchants", "orders", type_="foreignkey")
