"""Give every pytest session a fresh, migrated test database.

The shared test DB used to keep every row from every run (thousands of orders,
exceptions, merchants), which made list/limit tests flaky and the DB grow without end.
At session start we now:

1. keep a migrated *template* database ``<db>_tmpl`` (rebuilt only when the Alembic
   migrations change; their content hash is stored as the template's comment), and
2. drop the test database and re-create it from that template (about a second),
3. flush the test Redis database.

Hard guard: this only ever runs against localhost:55432 with a database name ending in
``_test`` and Redis on localhost:56379. Anything else raises before a single statement
runs. Opt out with ``PCD_TEST_DB_RESET=0``.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

API_DIR = Path(__file__).resolve().parents[1]
VERSIONS = API_DIR / "alembic" / "versions"
_LOCAL = {"127.0.0.1", "localhost", "::1"}


class UnsafeResetTarget(RuntimeError):
    pass


def _check(db_url: str, redis_url: str) -> tuple[str, str]:
    p = urlsplit(db_url.replace("postgresql+psycopg://", "postgresql://"))
    name = (p.path or "/").lstrip("/")
    if p.hostname not in _LOCAL or p.port != 55432 or not name.endswith("_test"):
        raise UnsafeResetTarget(f"refusing to reset {p.hostname}:{p.port}/{name}: only localhost:55432/*_test")
    if redis_url:
        r = urlsplit(redis_url)
        if r.hostname not in _LOCAL or r.port != 56379:
            raise UnsafeResetTarget(f"refusing to flush redis {r.hostname}:{r.port}: only localhost:56379")
    return f"postgresql://{p.username}:{p.password}@{p.hostname}:{p.port}", name


def migrations_hash() -> str:
    h = hashlib.sha256()
    for f in sorted(VERSIONS.glob("*.py")):
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def _migrate(server: str, dbname: str, db_url: str) -> None:
    env = {
        "HOME": os.environ.get("HOME", ""),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "DATABASE_URL": db_url.rsplit("/", 1)[0] + "/" + dbname,
        "REDIS_URL": os.environ.get("REDIS_URL", ""),
        "SPICEDB_ENDPOINT": os.environ.get("SPICEDB_ENDPOINT", ""),
        "SPICEDB_PRESHARED_KEY": os.environ.get("SPICEDB_PRESHARED_KEY", ""),
    }
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_DIR, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )


def reset_test_database(db_url: str, redis_url: str = "") -> str:
    """Drop + re-create the test DB from a migrated template. Returns what was done."""
    import psycopg

    server, name = _check(db_url, redis_url)
    tmpl = f"{name}_tmpl"
    want = migrations_hash()
    with psycopg.connect(f"{server}/postgres", autocommit=True) as con:
        row = con.execute(
            "select shobj_description(d.oid, 'pg_database') from pg_database d where datname = %s", (tmpl,)
        ).fetchone()
        rebuilt = False
        if row is None or row[0] != want:
            con.execute(f'drop database if exists "{tmpl}" with (force)')
            con.execute(f'create database "{tmpl}" template template1')  # postgis image: extensions in template1
            _migrate(server, tmpl, db_url)
            con.execute(f"comment on database \"{tmpl}\" is '{want}'")
            rebuilt = True
        con.execute(f'drop database if exists "{name}" with (force)')
        con.execute(f'create database "{name}" template "{tmpl}"')
    if redis_url:
        import redis

        redis.Redis.from_url(redis_url).flushdb()
    return f"test DB {name} recreated from {tmpl}" + (" (template rebuilt)" if rebuilt else "")


def reset_test_spicedb(endpoint: str, key: str) -> int:
    """Delete every relationship in the test SpiceDB (127.0.0.1:55051 only)."""
    import re

    host, _, port = endpoint.rpartition(":")
    if host not in ("127.0.0.1", "localhost") or port != "55051":
        raise UnsafeResetTarget(f"refusing to wipe spicedb {endpoint}: only localhost:55051")
    from authzed.api.v1 import (
        Client,
        DeleteRelationshipsRequest,
        ReadSchemaRequest,
        RelationshipFilter,
    )
    from grpcutil import insecure_bearer_token_credentials

    client = Client(f"127.0.0.1:{port}", insecure_bearer_token_credentials(key))
    try:
        schema = client.ReadSchema(ReadSchemaRequest()).schema_text
    except Exception:  # no schema written yet -> nothing to delete
        return 0
    types = re.findall(r"^definition\s+(\S+)", schema, re.M)
    for t in types:
        client.DeleteRelationships(
            DeleteRelationshipsRequest(relationship_filter=RelationshipFilter(resource_type=t))
        )
    return len(types)
