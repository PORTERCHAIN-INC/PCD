"""Phase 5c — optimize DomainEvents catalog + driver-scoped golden fixture."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from porterchain_api.fleetbase_engine.optimize_events import (
    DEFAULT_OPTIMIZE_ENGINE,
    assert_driver_scoped,
    foreign_order_ids,
)
from porterchain_shared.events.catalog import CATALOG_VERSION, DomainEventType

FIXTURE = Path(__file__).parent / "fixtures" / "gta150_golden_optimize.json"


def test_optimize_lifecycle_events_in_catalog() -> None:
    assert CATALOG_VERSION.startswith("1.2")
    for name in (
        "OPTIMIZE_ENQUEUED",
        "OPTIMIZE_READY",
        "OPTIMIZE_APPLIED",
        "OPTIMIZE_REJECTED",
        "OPTIMIZE_ROLLED_BACK",
    ):
        assert hasattr(DomainEventType, name)
    assert DomainEventType.OPTIMIZE_ENQUEUED == "optimize.enqueued"
    assert DomainEventType.OPTIMIZE_READY == "optimize.ready"


def test_golden_fixture_driver_scoped_contract() -> None:
    data = json.loads(FIXTURE.read_text())
    owned = data["driver_owned_order_ids"]
    sandbox = data["sandbox_order_ids"]
    # Happy path: only owned ids, vroom engine.
    assert_driver_scoped(
        owned,
        owned,
        engine=DEFAULT_OPTIMIZE_ENGINE,
        sandbox_ids=sandbox,
    )
    # Cross-driver leak detected.
    try:
        assert_driver_scoped(owned, owned + ["ord-other-driver"], engine="vroom")
        raise AssertionError("expected cross_driver failure")
    except AssertionError as exc:
        assert "cross_driver_order_ids" in str(exc)
    # Sandbox excluded from live optimize.
    try:
        assert_driver_scoped(
            owned,
            owned + list(sandbox),
            engine="vroom",
            sandbox_ids=sandbox,
        )
        raise AssertionError("expected sandbox failure")
    except AssertionError as exc:
        assert "sandbox_order_ids_in_live_optimize" in str(exc)
    # Non-vroom engine rejected for driver-scoped contract.
    try:
        assert_driver_scoped(owned, owned, engine="greedy")
        raise AssertionError("expected engine failure")
    except AssertionError as exc:
        assert "engine_not_vroom" in str(exc)

    foreign = foreign_order_ids(owned, owned + ["x"])
    assert foreign == {"x"}
    assert data["baseline"]["distance_km"] > 0
    assert data["tile"] == "GTA150"
    assert all(s.get("fsa") for s in data["stops"])


def test_enqueue_emits_optimize_enqueued() -> None:
    from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService
    from porterchain_api.fleetbase_engine.optimize_run_store import STATUS_PENDING

    emitted: list[tuple] = []

    def _capture(event_type, *, run_id, payload=None, **_kw):
        emitted.append((event_type, run_id, payload or {}))

    svc = OrchestratorOpsService()
    with (
        patch.object(svc, "_shape_order_ids", return_value=["ord-1"]),
        patch.object(
            svc,
            "_resolve_fleetbase_ids",
            return_value=(["order_01HQXYZABCDEFGHJKLMNPQRST"], {"order_01HQXYZABCDEFGHJKLMNPQRST": "ord-1"}, []),
        ),
        patch.object(
            svc,
            "_synced_fleet",
            return_value=(["vehicle_01HQXYZABCDEFGHJKLMNPQR"], ["driver_01HQXYZABCDEFGHJKLMNPQRS"]),
        ),
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.write_optimize_run"
        ),
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.enqueue_optimize_job"
        ),
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.is_consumable_public_id",
            return_value=True,
        ),
        patch(
            "porterchain_api.fleetbase_engine.optimize_events.emit_optimize_event",
            side_effect=_capture,
        ),
    ):
        pending = svc.enqueue_run(
            object(),
            order_ids=["ord-1"],
            engine="vroom",
            shape="vehicle",
            vehicle_ids=["vehicle_01HQXYZABCDEFGHJKLMNPQR"],
            pc_driver_id="drv-1",
        )
    assert pending["status"] == STATUS_PENDING
    assert emitted
    assert emitted[0][0] == DomainEventType.OPTIMIZE_ENQUEUED
