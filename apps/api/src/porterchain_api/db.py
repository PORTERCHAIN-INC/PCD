from collections.abc import Generator, Iterator
from contextlib import contextmanager
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

# Server-side guards: a leaked/stalled request can never pin a pooled connection
# ("idle in transaction") long enough to exhaust the pool and take login down.
_PG_GUARDS = {"options": "-c idle_in_transaction_session_timeout=60000 -c statement_timeout=30000"}
_require_postgresql_url(settings.database_url)

engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,
    connect_args=_PG_GUARDS,
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


def _safe_close(db: Session) -> None:
    """Return the connection to the pool even if Postgres already killed it.

    After idle_in_transaction_session_timeout the server drops the socket; a plain
    close() then raises during ROLLBACK. Invalidate so the pool discards the dead
    connection instead of leaking the checkout.
    """
    try:
        db.rollback()
    except Exception:  # noqa: BLE001
        try:
            db.invalidate()
        except Exception:  # noqa: BLE001
            pass
    try:
        db.close()
    except Exception:  # noqa: BLE001
        pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        _safe_close(db)


REPORT_STATEMENT_TIMEOUT_MS = 300_000


def get_report_db() -> Generator[Session, None, None]:
    """Session for exports/reports: 5 min statement cap instead of the 30 s default."""
    db = SessionLocal()
    try:
        db.execute(text(f"SET statement_timeout = {REPORT_STATEMENT_TIMEOUT_MS}"))
        yield db
    finally:
        try:
            db.rollback()
            db.execute(text("RESET statement_timeout"))
            db.commit()
        except Exception:  # noqa: BLE001 — never block close on cleanup
            pass
        _safe_close(db)


@contextmanager
def db_transaction(db: Session) -> Iterator[None]:
    """Commit a unit of work on a request session that may already be in a transaction.

    SQLAlchemy 2 autobegins on the first query (e.g. auth context load). Using
    ``with db.begin()`` after that raises ``InvalidRequestError``. Prefer this helper
    for mutating routes that share the session with Depends(get_db).
    """
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise


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
        _safe_close(db)


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
