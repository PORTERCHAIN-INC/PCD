"""cuOpt shadow client + compare (Phase 2b) — never commits."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from porterchain_api.intelligence_engine.cuopt_client import (
    _parse_cuopt_response,
    optimize_routing,
)
from porterchain_api.intelligence_engine.cuopt_shadow import (
    cuopt_shadow_enabled,
    run_cuopt_shadow,
)


def test_parse_cuopt_response_extracts_cost() -> None:
    parsed = _parse_cuopt_response(
        {
            "response": {
                "solver_response": {
                    "cost": 12500,
                    "vehicle_data": {
                        "0": {"route": [0, 1, 2, 0], "cost": 12500},
                    },
                }
            }
        }
    )
    assert parsed["ok"] is True
    assert parsed["total_cost"] == 12500.0
    assert parsed["vehicle_count_used"] == 1


def test_optimize_routing_posts_catalog_shape() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": {"cost": 8000, "vehicle_data": {}}}

    with (
        patch(
            "porterchain_api.intelligence_engine.cuopt_client.get_platform_settings",
            return_value=type(
                "S",
                (),
                {
                    "nvidia_api_key": "nvapi-test",
                    "nvidia_cuopt_url": "https://optimize.api.nvidia.com/v1/nvidia/cuopt",
                },
            )(),
        ),
        patch("porterchain_api.intelligence_engine.cuopt_client.httpx.Client") as client_cls,
    ):
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.post.return_value = mock_resp
        client_cls.return_value = client
        out = optimize_routing(cost_matrix=[[0, 1000], [1000, 0]], vehicle_count=1)

    assert out["total_cost"] == 8000.0
    body = client.post.call_args.kwargs["json"]
    assert body["action"] == "cuOpt_OptimizedRouting"
    assert "cost_matrix_data" in body["data"]


def test_shadow_disabled_by_default() -> None:
    assert cuopt_shadow_enabled(type("S", (), {"phase2_cuopt_shadow": False})()) is False
    out = run_cuopt_shadow(
        MagicMock(),
        order_ids=["a"],
        vroom_metrics={"after_distance_km": 10},
    )
    assert out["status"] == "disabled"


def test_shadow_compares_when_matrix_and_cuopt_ok() -> None:
    db = MagicMock()
    order = MagicMock()
    order.id = "o1"
    order.pickup = {"lat": 43.65, "lng": -79.38}
    order2 = MagicMock()
    order2.id = "o2"
    order2.pickup = {"lat": 43.66, "lng": -79.39}
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.all.return_value = [order, order2]

    with (
        patch(
            "porterchain_api.intelligence_engine.cuopt_shadow.cuopt_shadow_enabled",
            return_value=True,
        ),
        patch(
            "porterchain_api.intelligence_engine.cuopt_client.cuopt_configured",
            return_value=True,
        ),
        patch(
            "porterchain_api.intelligence_engine.cuopt_shadow._maps_duration_matrix",
            return_value=[[0.0, 5000.0], [5000.0, 0.0]],
        ),
        patch(
            "porterchain_api.intelligence_engine.cuopt_client.optimize_routing",
            return_value={
                "ok": True,
                "total_cost": 4000.0,
                "latency_ms": 120,
                "vehicle_count_used": 1,
                "routes": [],
            },
        ),
        patch(
            "porterchain_api.intelligence_engine.usage.record_ai_usage",
        ),
    ):
        out = run_cuopt_shadow(
            db,
            order_ids=["o1", "o2"],
            vroom_metrics={"after_distance_km": 5.0},
            vehicle_count=1,
        )

    assert out["status"] == "ok"
    assert out["winner"] == "cuopt"
    assert out["commit_sot"] == "porterchain_ortools"
    assert out["cuopt_distance_km"] == 4.0
