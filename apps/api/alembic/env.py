"""Alembic migration environment."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from porterchain_api.config import get_settings
from porterchain_api.db import Base

# Import all models so metadata is complete.
from porterchain_api import (  # noqa: F401
    admin_models,
    booking_draft_models,
    booking_models,
    crm_models,
    driver_models,
    fleetbase_models,
    identity_models,
    merchant_models,
    models,
    user_models,
    invitation_models,
)
from porterchain_api.billing_engine import models as billing_models  # noqa: F401
from porterchain_api.notification_engine import models as notification_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
