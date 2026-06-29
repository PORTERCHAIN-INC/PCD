from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from porterchain_api.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from porterchain_api import models  # noqa: F401
    from porterchain_api import merchant_models  # noqa: F401
    from porterchain_api import admin_models  # noqa: F401
    from porterchain_api import crm_models  # noqa: F401
    from porterchain_api import fleetbase_models  # noqa: F401
    from porterchain_api import identity_models  # noqa: F401
    from porterchain_api import driver_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()


def _migrate_sqlite_schema() -> None:
    """Add columns for existing SQLite dev databases."""
    if not settings.database_url.startswith("sqlite"):
        return
    migrations = [
        ("quotes", "declared_value_cents", "INTEGER"),
        ("quotes", "additional_stops", "TEXT"),
        ("quotes", "special_instructions", "TEXT"),
        ("quotes", "visitor_session_id", "VARCHAR(64)"),
        ("orders", "order_number", "VARCHAR(32)"),
        ("orders", "internal_reference", "VARCHAR(128)"),
        ("orders", "purchase_order_number", "VARCHAR(128)"),
        ("orders", "cost_centre", "VARCHAR(64)"),
        ("orders", "special_instructions", "TEXT"),
        ("customers", "visitor_session_id", "VARCHAR(64)"),
        ("admin_users", "fleetbase_user_uuid", "VARCHAR(128)"),
        ("drivers", "clerk_user_id", "VARCHAR(128)"),
        ("orders", "assigned_driver_id", "VARCHAR(36)"),
        ("promotions", "promotion_type", "VARCHAR(32)"),
        ("promotions", "merchant_id", "VARCHAR(36)"),
        ("promotions", "config", "TEXT"),
        ("crm_leads", "custom_fields", "TEXT"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            existing = {row[1] for row in rows}
            if column not in existing:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()

    with engine.connect() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(crm_leads)").fetchall()
        if any(row[1] == "custom_fields" for row in rows):
            conn.exec_driver_sql(
                "UPDATE crm_leads SET custom_fields = '{}' WHERE custom_fields IS NULL"
            )
            conn.commit()

    with engine.connect() as conn:
        conn.exec_driver_sql(
            "UPDATE orders SET order_number = tracking_number WHERE order_number IS NULL OR order_number = ''"
        )
        conn.commit()
