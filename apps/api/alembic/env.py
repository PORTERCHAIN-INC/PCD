"""Alembic migration environment."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from porterchain_api.config import get_settings
from porterchain_api.db import Base

# Import all models so metadata is complete.
from porterchain_api import (  # noqa: F401
    admin_models,
    booking_draft_models,
    booking_models,
    crm_models,
    driver_models,
    identity_models,
    merchant_models,
    user_models,
    unified_identity_models,
    website_content_models,
    invitation_models,
    forensics_models,
)
from porterchain_api import booking_attachment_models  # noqa: F401
from porterchain_api.billing_engine import models as billing_models  # noqa: F401
from porterchain_api.notification_engine import models as notification_models  # noqa: F401
from porterchain_api.intelligence_engine import usage_models as ai_usage_models  # noqa: F401
from porterchain_api.dispatch_engine import models as dispatch_models  # noqa: F401
from porterchain_api.platform import soft_delete as soft_delete_models  # noqa: F401
from porterchain_api.pricing_engine import models as pricing_models  # noqa: F401
from porterchain_api.org_engine import models as org_models  # noqa: F401
from porterchain_api.compliance_engine import models as compliance_models  # noqa: F401
from porterchain_api.batch_engine import models as batch_models  # noqa: F401
from porterchain_api.job_docs import models as job_docs_models  # noqa: F401
from porterchain_api.ops_rules import models as ops_rules_models  # noqa: F401
from porterchain_api import schema_extras  # noqa: F401,E402  (must be last: indexes on the tables above)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Tables owned by Postgres extensions (PostGIS tiger geocoder, topology, spatial_ref_sys)
# are not ours: keep them out of autogenerate / `alembic check` instead of "dropping" them.
_EXTENSION_TABLES: set[str] = set()
_EXTENSION_SCHEMAS = {"tiger", "tiger_data", "topology"}


def load_extension_tables(connection) -> set[str]:  # noqa: ANN001
    rows = connection.execute(
        text(
            "SELECT c.relname FROM pg_depend d JOIN pg_class c ON c.oid = d.objid "
            "WHERE d.deptype = 'e' AND d.classid = 'pg_class'::regclass AND c.relkind IN ('r','v','m')"
        )
    )
    return {r[0] for r in rows}


def include_object(obj, name, type_, reflected, compare_to):  # noqa: ANN001
    table = obj if type_ == "table" else getattr(obj, "table", None)
    if table is not None and reflected and compare_to is None and type_ == "table":
        if table.schema in _EXTENSION_SCHEMAS or name in _EXTENSION_TABLES:
            return False
    if type_ == "index" and reflected and compare_to is None and table is not None:
        if table.name in _EXTENSION_TABLES:
            return False
    return True
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
        _EXTENSION_TABLES.update(load_extension_tables(connection))
        connection.commit()  # end the autobegun read so alembic owns (and commits) its transaction
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
