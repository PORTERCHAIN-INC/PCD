"""G21 A-APR-02: reviewer demo driver sees 2 sandbox jobs; actions write nothing."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from porterchain_api.config import Settings
from porterchain_api.review import reviewer_sandbox as rs
from porterchain_api.schemas_driver import DriverJobsListResponse


def _s(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


def test_reviewer_off_by_default() -> None:
    drv = SimpleNamespace(email="review.driver@porterchain.com")
    assert not rs.is_reviewer_driver(drv, _s(reviewer_driver_emails="review.driver@porterchain.com"))


def test_reviewer_driver_matches_when_enabled() -> None:
    s = _s(reviewer_accounts_enabled=True, reviewer_driver_emails=" Review.Driver@porterchain.com ")
    assert rs.is_reviewer_driver(SimpleNamespace(email="review.driver@porterchain.com"), s)
    assert not rs.is_reviewer_driver(SimpleNamespace(email="real@driver.ca"), s)


def test_two_sandbox_jobs_fit_the_schema() -> None:
    body = DriverJobsListResponse.model_validate(rs.sandbox_jobs())
    assert len(body.jobs) == 2 and all(j.order_id.startswith("sandbox-") for j in body.jobs)


def _app(enabled: bool = True) -> TestClient:
    app = FastAPI()

    @app.api_route("/{p:path}", methods=["GET", "POST"])
    def real(p: str):  # would be the real handler; must never be reached for sandbox ids
        raise AssertionError(f"real handler reached: {p}")

    app.add_middleware(rs.ReviewerSandboxMiddleware, enabled=lambda: enabled)
    return TestClient(app)


def test_pickup_and_pod_on_sandbox_ids_never_reach_real_handlers() -> None:
    c = _app()
    h = {"Authorization": "Bearer t"}
    r = rs.SANDBOX_ROUTE_ID
    for path in (
        f"/driver-api/v1/routes/{r}/start",
        f"/driver-api/v1/routes/{r}/stops/sandbox-job-1-pickup/arrive",
        f"/driver-api/v1/routes/{r}/stops/sandbox-job-1-delivery/pod-photo",
        f"/driver-api/v1/routes/{r}/stops/sandbox-job-1-delivery/pod-complete",
        "/driver-api/v1/orders/sandbox-job-1/packages/scan",
    ):
        res = c.post(path, headers=h)
        assert res.status_code == 200 and res.json()["sandbox"] is True, path
    assert c.get("/driver-api/v1/jobs/sandbox-job-2", headers=h).json()["order_number"] == "PC-REVIEW-2"
    assert c.post(f"/driver-api/v1/routes/{r}/start").status_code == 401


def test_flag_off_middleware_passes_through() -> None:
    import pytest

    with pytest.raises(AssertionError, match="real handler reached"):
        _app(False).post("/driver-api/v1/routes/sandbox-route-review/start", headers={"Authorization": "Bearer t"})
