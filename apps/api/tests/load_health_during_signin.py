"""Load test: 2000 /health calls (50 concurrent) while 20 slow (1.5 s) Clerk sign-ins run.
Run: .venv/bin/python tests/load_health_during_signin.py"""
import asyncio, statistics, time, sys
from unittest.mock import MagicMock
import httpx, pytest
sys.path.insert(0, "tests")
import test_api_freeze_regression as t

async def main():
    mp = pytest.MonkeyPatch()
    t.slow_clerk.__wrapped__(mp)
    app = t._app_with_driver_route()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        sign = [asyncio.create_task(c.get("/driver-api/v1/jobs", headers={"Authorization": "Bearer x"})) for _ in range(20)]
        lat = []
        sem = asyncio.Semaphore(50)
        async def one():
            async with sem:
                s = time.perf_counter(); r = await c.get("/health"); lat.append(time.perf_counter() - s); assert r.status_code == 200
        t0 = time.perf_counter()
        await asyncio.gather(*(one() for _ in range(2000)))
        dur = time.perf_counter() - t0
        await asyncio.gather(*sign)
    lat.sort()
    print(f"health n={len(lat)} in {dur:.2f}s  p50={statistics.median(lat)*1000:.1f}ms p99={lat[int(len(lat)*.99)]*1000:.1f}ms max={lat[-1]*1000:.1f}ms")
    mp.undo()
asyncio.run(main())
