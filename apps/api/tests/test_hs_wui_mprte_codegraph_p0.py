"""P0 contracts: HS-* / W-UI|W-VIS|W-SPA / MP-RTE — CodeGraph field schemas.

SSOT fields: docs/CODEGRAPH_QUOTE_VISITOR_OPTIMIZE_SCHEMAS.md
Catalog IDs: docs/DEVELOPMENT_TEST_CASES.md (HS-*), WEBSITE_PERSONA_*, MERCHANT matrix MP-RTE-*.

Does not duplicate live vendor e2e (compose Valhalla/Mailpit) — unit/contract only.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService
from porterchain_api.booking_models import Quote, VisitorSession
from porterchain_api.merchant_engine.route_import_service import MerchantRouteImportService
from porterchain_api.schemas_admin import OptimizeCommitBody, OptimizeRunBody
from porterchain_api.schemas_booking import (
    CreateQuoteRequest,
    QuoteResponse,
    VisitorTrackingInput,
)
from porterchain_services.maps.service import MapsService, OSRM_PUBLIC_DEMO_LAST_RESORT

REPO = Path(__file__).resolve().parents[3]
API_ENGINES = REPO / "apps" / "api" / "src" / "porterchain_api"
WEBSITE_SRC = REPO / "website" / "src"


def _iter_engine_py() -> list[Path]:
    out: list[Path] = []
    for name in (
        "booking_engine",
        "merchant_engine",
        "admin_engine",
        "driver_engine",
        "dispatch_engine",
        "pricing_engine",
        "billing_engine",
        "notification_engine",
    ):
        root = API_ENGINES / name
        if not root.is_dir():
            continue
        out.extend(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    return out


@pytest.mark.tc_id("HS-09")
def test_hs09_maps_route_with_source_valhalla_label() -> None:
    svc = MapsService()
    svc.ctx = SimpleNamespace(
        settings=SimpleNamespace(
            routing_engine="valhalla",
            valhalla_url="http://valhalla.test",
            osrm_url="http://osrm.test",
            osrm_allow_public_demo=False,
        )
    )
    with (
        patch.object(svc, "_valhalla_route", return_value={"distance": 1500, "time": 200}),
        patch.object(svc, "_osrm_route") as osrm,
    ):
        leg, source = svc.route_with_source((43.65, -79.38), (43.66, -79.39))
    assert leg is not None
    assert source == "valhalla"
    osrm.assert_not_called()


@pytest.mark.tc_id("HS-10")
def test_hs10_osrm_fallback_and_public_demo_gated() -> None:
    svc = MapsService()
    svc.ctx = SimpleNamespace(
        settings=SimpleNamespace(
            routing_engine="valhalla",
            valhalla_url="http://valhalla.test",
            osrm_url="http://osrm.test",
            osrm_allow_public_demo=False,
        )
    )
    with (
        patch.object(svc, "_valhalla_route", return_value=None),
        patch.object(svc, "_osrm_route", return_value={"distance": 800, "time": 90}),
    ):
        leg, source = svc.route_with_source((43.65, -79.38), (43.66, -79.39))
    assert source == "osrm"
    assert leg is not None

    # Public demo must not be the default base when allow flag is false and osrm_url set.
    assert svc._osrm_base() == "http://osrm.test"
    svc.ctx.settings.osrm_url = ""
    assert svc._osrm_base() is None
    assert "project-osrm.org" in OSRM_PUBLIC_DEMO_LAST_RESORT


@pytest.mark.tc_id("HS-13")
def test_hs13_optimize_run_body_defaults_porterchain_day_plan() -> None:
    body = OptimizeRunBody()
    assert body.mode == "allocate"
    assert body.engine == "porterchain"
    assert body.shape == "fleet"

    commit = OptimizeCommitBody(assignments=[{"order_id": "order_x"}])
    assert commit.run_id is None

    db = MagicMock()
    order = SimpleNamespace(id="pc-1", assigned_driver_id="drv-1", merchant_id=None)
    svc = OrchestratorOpsService()
    with (
        patch.object(svc, "_shape_order_ids", return_value=["pc-1"]),
        patch.object(svc, "_load_orders", return_value=[order]),
        patch.object(svc, "_resolve_pc_driver", return_value="drv-1"),
        patch.object(svc, "_vehicle_for_driver", return_value=None),
        patch(
            "porterchain_api.dispatch_engine.day_plan.queue_one_van",
            return_value={"ok": True, "status": "pending", "run_id": "run-1", "engine": "porterchain"},
        ) as enq,
        patch("porterchain_api.driver_engine.last_known.read_last_known", return_value=None),
        patch("porterchain_api.dispatch_engine.optimize_events.emit_enqueued"),
    ):
        out = svc.enqueue_run(db)
    assert out["ok"] is True
    assert out["status"] == "pending"
    enq.assert_called_once()
    sig = inspect.signature(OrchestratorOpsService.enqueue_run)
    assert sig.parameters["engine"].default == "porterchain"


@pytest.mark.tc_id("MP-RTE-002b")
def test_mp_rte_optimize_enqueues_worker_not_maps_tsp() -> None:
    db = MagicMock()
    job = SimpleNamespace(
        id="job-rte-1",
        status="preview",
        job_config={"stops": [{"geocode_status": "ok", "lat": 43.65, "lng": -79.38}]},
    )
    svc = MerchantRouteImportService()
    with (
        patch.object(svc, "get_job", return_value=job),
        patch.object(svc, "_assert_unconfirmed"),
        patch.object(svc, "_enqueue_optimize") as enq,
        patch("porterchain_services.maps.service.MapsService") as maps_cls,
    ):
        out = svc.optimize(db, MagicMock(), "job-rte-1")
    assert out.job_config["optimize_status"] == "pending"
    assert out.job_config["optimized"] is False
    enq.assert_called_once_with("job-rte-1")
    maps_cls.assert_not_called()


@pytest.mark.tc_id("MP-RTE-002c")
def test_mp_rte_no_vroom_client_under_engines() -> None:
    """No PorterChain VROOM HTTP/SDK client under *_engine (Fleetbase owns VROOM).

    Diagnostics may *mention* VROOM_ENDPOINT_MODE in probe hints — that is not a client.
    """
    import re

    import_re = re.compile(r"(?m)^\s*(import\s+vroom\b|from\s+vroom\b)")
    client_re = re.compile(r"\bvroom_client\b|VroomClient\b|from\s+vroom_express\b")
    hits: list[str] = []
    for path in _iter_engine_py():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if import_re.search(text) or client_re.search(text):
            hits.append(str(path.relative_to(REPO)))
    assert not hits, f"forbidden VROOM client imports in engines: {hits}"


@pytest.mark.tc_id("MP-RTE-006")
def test_mp_rte_enqueue_optimize_payload_shape() -> None:
    """_enqueue_optimize posts optimize_import action (worker contract)."""
    svc = MerchantRouteImportService()
    with patch(
        "porterchain_api.dispatch_engine.routing_jobs.enqueue_routing_job"
    ) as enq:
        svc._enqueue_optimize("job-xyz")
    enq.assert_called_once_with({"action": "optimize_import", "job_id": "job-xyz"})


@pytest.mark.tc_id("W-VIS-001")
def test_w_vis_create_quote_and_tracking_schema() -> None:
    tracking_fields = set(VisitorTrackingInput.model_fields)
    for key in (
        "utm_source",
        "landing_page",
        "paths",
        "intent",
        "guide_stage",
        "page_view_count",
    ):
        assert key in tracking_fields

    quote_fields = set(CreateQuoteRequest.model_fields)
    assert "anonymous_session_id" in quote_fields
    assert "visitor_session_id" in quote_fields
    assert "tracking" in quote_fields

    resp_fields = set(QuoteResponse.model_fields)
    for key in ("quote_id", "amount_cents", "pricing_breakdown", "currency", "expires_at"):
        assert key in resp_fields
    # Response exposes distance_km; routing source is Maps facade, not QuoteResponse.
    assert "distance_km" in resp_fields
    assert "distance_source" not in resp_fields


@pytest.mark.tc_id("W-VIS-ORM")
def test_w_vis_visitor_session_orm_columns() -> None:
    cols = set(VisitorSession.__table__.columns.keys())
    for key in (
        "id",
        "utm_source",
        "signals",
        "touch_count",
        "intent_score",
        "quote_generated",
        "last_quote_id",
        "customer_id",
    ):
        assert key in cols
    quote_cols = set(Quote.__table__.columns.keys())
    assert "visitor_session_id" in quote_cols
    assert "anonymous_session_id" in quote_cols
    assert "distance_meters" in quote_cols
    assert "amount_cents" in quote_cols


@pytest.mark.tc_id("W-SPA-002")
def test_w_ui_website_src_no_fleetbase_vroom_socketcluster() -> None:
    if not WEBSITE_SRC.is_dir():
        pytest.skip("website src missing")
    banned = ("socketcluster", "vroom-express", "vroom_client", ":8000")
    # fleetbase as substring is noisy in marketing copy — ban SDK/HTTP patterns only.
    sdk_banned = (
        "socketcluster-client",
        "@socketcluster",
        "fleetbase-js",
        "from 'fleetbase",
        'from "fleetbase',
        "VROOM_ROUTER",
    )
    hits: list[str] = []
    for path in WEBSITE_SRC.rglob("*"):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        if "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for token in banned + sdk_banned:
            if token.lower() in lower:
                hits.append(f"{path.relative_to(REPO)}:{token}")
    assert not hits, f"website vendor leak: {hits[:20]}"


@pytest.mark.tc_id("W-UI-PAGE")
def test_w_ui_money_loop_pages_exist() -> None:
    """W-UI-002…007: locale money-loop pages present (Playwright mounts later)."""
    locale_app = REPO / "website" / "src" / "app" / "[locale]"
    required = (
        "quote/page.tsx",
        "book/page.tsx",
        "book/continue/page.tsx",
        "book/success/page.tsx",
        "track/page.tsx",
        "track/[tracking]/page.tsx",
        "contact/page.tsx",
    )
    missing = [rel for rel in required if not (locale_app / rel).is_file()]
    assert not missing, f"missing website pages: {missing}"
