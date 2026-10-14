"""Regression for the 2026-10-14 prod freeze.

Root cause: async auth dependencies (get_driver_context) ran *blocking* work on the
event loop — Clerk Backend user lookups (sync httpx, 20 s timeout) and SQLAlchemy
pool checkouts (30 s pool_timeout). One slow Clerk call froze every request,
including /health, and left other sessions idle-in-transaction until Postgres
killed them at 60 s.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from starlette.concurrency import run_in_threadpool

from porterchain_api.auth import driver as driver_auth
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.db import get_db

SLOW_CLERK_S = 1.5


def _app_with_driver_route() -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/driver-api/v1/jobs")
    def jobs(ctx=Depends(driver_auth.get_driver_context)):  # noqa: B008
        return {"ok": True}

    app.dependency_overrides[get_db] = lambda: MagicMock()
    return app


async def _hammer_health(client: httpx.AsyncClient, seconds: float) -> list[float]:
    lat: list[float] = []
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        t = time.perf_counter()
        r = await client.get("/health")
        assert r.status_code == 200
        lat.append(time.perf_counter() - t)
        # Probe cadence like Docker/Caddy: a real suspension point, so a blocked
        # loop shows up as a stalled probe.
        t = time.perf_counter()
        await asyncio.sleep(0.005)
        lat.append(time.perf_counter() - t)
    return lat


@pytest.fixture
def slow_clerk(monkeypatch):
    async def fake_verify(token, settings, **_):
        return ClerkClaims(clerk_user_id="user_slow", email=None)

    def slow_enrich(claims, settings):
        return claims

    def stop_after_enrich(db, claims):
        # prepare -> UserSync -> email identity -> fetch_clerk_user: blocking
        # Clerk Backend HTTP with a DB transaction already open, like prod.
        time.sleep(SLOW_CLERK_S)
        raise HTTPException(status_code=403, detail="driver_not_found")

    import porterchain_api.auth.clerk as clerk_mod
    import porterchain_api.auth.email_identity as ei
    import porterchain_api.auth.prepare as prep

    monkeypatch.setattr(clerk_mod, "verify_clerk_token", fake_verify)
    monkeypatch.setattr(ei, "enrich_claims_with_verified_email", slow_enrich)
    monkeypatch.setattr(prep, "prepare_user_from_claims", stop_after_enrich)


@pytest.mark.anyio
async def test_slow_clerk_signin_does_not_freeze_health(slow_clerk):
    app = _app_with_driver_route()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        t0 = time.perf_counter()
        hammer = asyncio.create_task(_hammer_health(c, SLOW_CLERK_S))
        await asyncio.sleep(0.05)  # probes running; now drivers sign in
        signins = [
            asyncio.create_task(c.get("/driver-api/v1/jobs", headers={"Authorization": "Bearer jwt"}))
            for _ in range(5)
        ]
        lat = await hammer
        hammer_wall = time.perf_counter() - t0
        results = await asyncio.gather(*signins)
    assert all(r.status_code == 403 for r in results)
    lat.sort()
    p99 = lat[int(len(lat) * 0.99) - 1]
    # Before the fix the loop was blocked for 5 x 1.5 s: /health took >= 1.5 s.
    assert lat[-1] < 0.5, f"/health max {lat[-1]:.3f}s — event loop was blocked"
    assert len(lat) > 20, f"only {len(lat)} health calls completed"
    assert p99 < 0.25, f"/health p99 {p99:.3f}s during slow sign-in"
    assert hammer_wall < SLOW_CLERK_S + 0.5, f"health hammer stalled {hammer_wall:.2f}s"


@pytest.mark.anyio
async def test_pool_exhaustion_in_threadpool_does_not_block_loop():
    eng = create_engine(
        "sqlite://", poolclass=QueuePool, pool_size=1, max_overflow=0, pool_timeout=1.0
    )
    held = eng.connect()  # pool now exhausted
    try:
        def checkout():
            with eng.connect() as conn:
                conn.execute(text("select 1"))

        ticks = 0

        async def ticker():
            nonlocal ticks
            for _ in range(40):
                await asyncio.sleep(0.02)
                ticks += 1

        t0 = time.perf_counter()
        res = await asyncio.gather(run_in_threadpool(checkout), ticker(), return_exceptions=True)
        assert type(res[0]).__name__ == "TimeoutError"  # pool_timeout honoured
        assert time.perf_counter() - t0 < 3
        assert ticks == 40  # loop kept running during the 1 s pool wait
    finally:
        held.close()


def test_get_db_invalidates_killed_connection(monkeypatch):
    from porterchain_api import db as dbmod

    sess = MagicMock()
    sess.rollback.side_effect = Exception("terminating connection due to idle-in-transaction timeout")
    monkeypatch.setattr(dbmod, "SessionLocal", lambda: sess)
    gen = dbmod.get_db()
    next(gen)
    with pytest.raises(StopIteration):
        next(gen)
    sess.invalidate.assert_called_once()
    sess.close.assert_called_once()


def test_health_does_not_touch_db_pool(monkeypatch):
    from fastapi.testclient import TestClient

    from porterchain_api import db as dbmod
    from porterchain_api.main import create_app

    def boom(*a, **k):
        raise AssertionError("/health touched the DB pool")

    monkeypatch.setattr(dbmod.engine.pool, "connect", boom)
    monkeypatch.setattr(dbmod, "SessionLocal", boom)
    client = TestClient(create_app())  # no lifespan
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/health/live").status_code == 200


def test_clerk_get_user_has_short_timeout(monkeypatch):
    from porterchain_api.auth import clerk_client

    seen = {}
    real = httpx.Client

    def spy(*a, **k):
        seen["timeout"] = k.get("timeout")
        return real(*a, transport=httpx.MockTransport(lambda r: httpx.Response(404)), **k)

    monkeypatch.setattr(clerk_client.httpx, "Client", spy)
    assert clerk_client.ClerkClient("sk_test").get_user("user_x") is None
    t = seen["timeout"]
    assert isinstance(t, httpx.Timeout) and t.read <= 5 and t.connect <= 2


def test_pool_monitor_alerts(caplog):
    from porterchain_api.platform import db_pool_monitor as mon

    eng = create_engine("sqlite://", poolclass=QueuePool, pool_size=4, max_overflow=1)
    mon._last_alert.clear()
    conns = [eng.connect() for _ in range(5)]
    try:
        with caplog.at_level("ERROR", logger="porterchain.db_pool"):
            assert mon.check_pool(eng) is True
        assert "db_pool_pressure" in caplog.text
    finally:
        for c in conns:
            c.close()

    class Kill(Exception):
        pass

    Kill.__name__ = "IdleInTransactionSessionTimeout"
    ctx = MagicMock(original_exception=Kill())
    caplog.clear()
    with caplog.at_level("ERROR", logger="porterchain.db_pool"):
        mon._on_handle_error(ctx)
    assert "db_idle_in_transaction_killed" in caplog.text


@pytest.fixture
def anyio_backend():
    return "asyncio"
