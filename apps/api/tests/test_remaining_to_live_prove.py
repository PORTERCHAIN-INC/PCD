"""Dean remaining-to-live prove gates (R1–R3)."""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.admin_engine.control_tower.assignment import AssignmentMixin
from porterchain_api.admin_engine.dispatch_suggestions_service import DispatchSuggestionsService
from porterchain_api.config import Settings
from porterchain_api.merchant_engine.route_import_service import MerchantRouteImportService
from porterchain_api.platform.health import readiness
from porterchain_api.platform.metrics import note_routing_source, prometheus_metrics
from porterchain_event_bus.bus import STREAM_READ_COUNT
from porterchain_services.maps.service import HTTP_TIMEOUT_S, MapsService
from porterchain_driver.navigation import NavigationService


def test_optimize_run_handler_enqueues_without_solver():
    from porterchain_api.routers import operations as ops_router

    src = inspect.getsource(ops_router.optimize_run)
    assert "enqueue_run" in src
    assert "._orch.run(" not in src
    assert "run_orchestrator" not in src


def test_driver_optimize_handler_enqueues_without_tsp():
    from porterchain_api.routers.driver import jobs as jobs_router
    from porterchain_driver.jobs import JobsService
    from porterchain_driver.route_optimizer import DriverRouteOptimizer

    src = inspect.getsource(jobs_router.optimize_jobs)
    assert "optimize_route" in src
    opt_src = inspect.getsource(JobsService.optimize_route)
    assert "queue_one_van" in opt_src
    assert "_two_opt" not in inspect.getsource(DriverRouteOptimizer)
    assert "haversine" not in inspect.getsource(JobsService.optimize_route)


def test_merchant_optimize_enqueues_without_solver():
    src = inspect.getsource(MerchantRouteImportService.optimize)
    assert "_enqueue_optimize" in src
    assert "optimize_drop_order_with_source" not in src
    assert "2-opt" not in src


def test_quote_create_does_not_double_resolve_route():
    from porterchain_api.booking_engine.quote_service import QuoteService

    src = inspect.getsource(QuoteService.create_quote)
    assert src.count("resolve_route_distance") == 0


def test_route_distance_meters_is_one_multi_call():
    src = inspect.getsource(MapsService.route_distance_meters)
    assert "_valhalla_route_locations" in src or "route_multi" in src
    assert "for i in range" not in src


def test_route_session_does_not_loop_session():
    src = inspect.getsource(NavigationService.route_session)
    assert "for stop in stops" not in src
    assert "self.session(" in src


def test_worker_routing_mode_drains_only_routing():
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    sys.modules.pop("run", None)
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    else:
        sys.path.remove(str(worker_root))
        sys.path.insert(0, str(worker_root))
    from run import mode_includes, parse_worker_mode

    assert parse_worker_mode(["--mode", "routing"]) == "routing"
    assert mode_includes("routing", "events") is False
    assert mode_includes("routing", "queues") is False
    assert mode_includes("all", "queues") is True


def test_suggestions_cold_cache_returns_pending_without_compute():
    db = MagicMock()
    db.get.return_value = SimpleNamespace(id="ord-1")
    with (
        patch(
            "porterchain_api.admin_engine.control_tower.scoring.read_suggestions_cache",
            return_value=None,
        ),
        patch(
            "porterchain_api.admin_engine.control_tower.scoring.enqueue_score_job"
        ) as enqueue,
        patch(
            "porterchain_api.admin_engine.control_tower.scoring.compute_ranked_suggestions"
        ) as compute,
    ):
        out = DispatchSuggestionsService().suggest(db, "ord-1")
    assert out["source"] == "pending"
    assert out["drivers"] == []
    enqueue.assert_called_once_with("ord-1")
    compute.assert_not_called()


def test_assignable_drivers_never_calls_adapter():
    mixin = AssignmentMixin()
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    db.query.return_value.filter.return_value.group_by.return_value.all.return_value = []
    with (
        patch(
            "porterchain_api.dispatch_engine.ops_mirror.online_map_from_mirror",
            return_value={},
        ),
        patch(
            "porterchain_api.services.fleetbase_integration.get_fleetbase_integration"
        ) as get_fb,
    ):
        assert mixin.assignable_drivers(db) == []
        get_fb.assert_not_called()


def test_navigation_session_source_has_no_fetch_route():
    src = inspect.getsource(NavigationService.session)
    assert "fetch_route" not in src
    assert STREAM_READ_COUNT == 25
    assert HTTP_TIMEOUT_S == 2.0


def test_route_import_resolve_does_not_sleep():
    with patch("porterchain_api.merchant_engine.import_geocode.time.sleep") as sleep, patch(
        "porterchain_api.merchant_engine.import_geocode._nominatim_search"
    ) as nominatim:
        resolved, _errors = MerchantRouteImportService()._resolve_stops(
            [
                {"sequence": 1, "stop_type": "pickup", "address": "100 King St W, Toronto"},
                {"sequence": 2, "stop_type": "drop", "address": "200 Bay St, Toronto"},
            ]
        )
        sleep.assert_not_called()
        nominatim.assert_not_called()
    assert all(s["geocode_status"] == "pending" for s in resolved)


def test_metrics_include_routing_source_gauges():
    note_routing_source("valhalla")
    text = prometheus_metrics()
    assert "porterchain_routing_source_total" in text
    assert 'source="valhalla"' in text


def test_readiness_ok_reports_dispatch_porterchain():
    db = MagicMock()
    db.execute.return_value = None
    settings = Settings(app_env="local")
    with (
        patch("porterchain_api.platform.health.ping_redis", return_value=True),
        patch("porterchain_api.platform.health._routing_health", return_value="ok"),
        patch(
            "porterchain_api.auth.clerk_registry.clerk_health_checks",
            return_value={"customer": "ok", "merchant": "ok", "admin": "ok", "driver": "ok"},
        ),
        patch(
            "porterchain_api.auth.clerk_registry.clerk_configuration_mode",
            return_value="enterprise",
        ),
        patch(
            "porterchain_api.merchant_engine.webhook_delivery_health.assess_merchant_webhook_delivery",
            return_value={"meets_slo": True, "success_pct": 100.0},
        ),
    ):
        result = readiness(db, settings)
    assert result["status"] == "ok"
    assert result["checks"].get("dispatch") == "porterchain"
    assert "fleetbase_sync" not in result["checks"]


def test_worker_modes_are_events_queues_routing_only():
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    sys.modules.pop("run", None)
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    else:
        sys.path.remove(str(worker_root))
        sys.path.insert(0, str(worker_root))
    from run import WORKER_MODES, _load_local_api_env, mode_includes, parse_worker_mode

    assert "fleetbase" not in WORKER_MODES
    assert parse_worker_mode(["--mode", "routing"]) == "routing"
    assert mode_includes("routing", "routing") is True
    assert mode_includes("routing", "events") is False
    assert mode_includes("all", "events") is True
    assert callable(_load_local_api_env)


def test_optimize_worker_imports_user_models_for_driver_fk():
    import inspect
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from processors import dispatch

    src = inspect.getsource(dispatch._optimize_run)
    assert "user_models" in src
    assert "execute_queued_run" in src


def test_driver_location_ping_commits():
    from porterchain_api.routers.driver import jobs as jobs_router

    src = inspect.getsource(jobs_router.location_ping)
    assert "db_transaction" in src
    assert "recorded_at" in src


def test_geocode_import_dispatch_uses_job_id():
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from processors import dispatch

    with patch.object(dispatch, "_geocode_import") as geo:
        dispatch.process_dispatch({"action": "geocode_import", "job_id": "job-9"})
        geo.assert_called_once_with("job-9")


def test_optimize_import_dispatch_uses_job_id():
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from processors import dispatch

    with patch.object(dispatch, "_optimize_import") as opt:
        dispatch.process_dispatch({"action": "optimize_import", "job_id": "job-opt"})
        opt.assert_called_once_with("job-opt")
