from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from porterchain_api.config import get_settings


class Base(DeclarativeBase):
    pass


def _require_postgresql_url(url: str) -> None:
    if url.startswith("sqlite"):
        raise RuntimeError(
            "SQLite is not supported for Porterchain business data. "
            "Set DATABASE_URL=postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain "
            "and run `pnpm db:migrate`."
        )
    if not url.startswith("postgresql"):
        raise RuntimeError(
            f"Unsupported DATABASE_URL scheme (PostgreSQL required): {url.split(':', 1)[0]}"
        )


settings = get_settings()
_require_postgresql_url(settings.database_url)

engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

_REPLICA_POOL_SIZE = 5
_REPLICA_MAX_OVERFLOW = 10


@lru_cache
def _replica_db() -> tuple[Engine, sessionmaker[Session]] | None:
    replica_url = get_settings().database_url_replica
    if not replica_url:
        return None
    _require_postgresql_url(replica_url)
    replica_engine = create_engine(
        replica_url,
        pool_size=_REPLICA_POOL_SIZE,
        max_overflow=_REPLICA_MAX_OVERFLOW,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
    )
    factory = sessionmaker(autocommit=False, autoflush=False, bind=replica_engine, expire_on_commit=False)
    return replica_engine, factory


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_read_db() -> Generator[Session, None, None]:
    """Read-only analytics session — uses replica when DATABASE_URL_REPLICA is set."""
    replica = _replica_db()
    if replica is None:
        yield from get_db()
        return
    _, factory = replica
    db = factory()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Verify PostgreSQL connectivity on startup. Schema is managed by Alembic only."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.commit()
    replica = _replica_db()
    if replica is not None:
        replica_engine, _ = replica
        with replica_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
