from collections.abc import Generator

from sqlalchemy import create_engine, text
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


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Verify PostgreSQL connectivity on startup. Schema is managed by Alembic only."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.commit()
