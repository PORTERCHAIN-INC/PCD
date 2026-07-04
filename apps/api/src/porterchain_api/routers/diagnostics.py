"""Enterprise Validation & Diagnostics API — /v1/admin/diagnostics/*"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_service import (
    TEST_CATALOG,
    TEST_IDS,
    AdminDiagnosticsService,
)
from porterchain_api.admin_engine.e2e_validation_catalog import DEFAULT_MERCHANT_BULK_COUNT
from porterchain_api.admin_engine.e2e_validation_service import E2EValidationService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db

router = APIRouter(prefix="/v1/admin/diagnostics", tags=["diagnostics"])

_svc = AdminDiagnosticsService()
_e2e = E2EValidationService()
Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _guard(ctx: AdminContext, module: str = "diagnostics") -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


class ReportsRequest(BaseModel):
    write_files: bool = False


class E2ERunRequest(BaseModel):
    write_files: bool = False
    cleanup: bool = True
    merchant_order_count: int = DEFAULT_MERCHANT_BULK_COUNT


@router.get("/center")
def diagnostics_center(
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx)
    return _svc.center(db, settings)


@router.get("/health")
def diagnostics_health(
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx)
    return _svc.health_dashboard(db, settings)


@router.get("/tests")
def list_tests(ctx: Ctx) -> dict:
    _guard(ctx)
    return {"tests": TEST_CATALOG, "count": len(TEST_CATALOG)}


@router.post("/tests/run")
def run_all_tests(
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx)
    return _svc.run_platform_validation(db, settings)


@router.post("/tests/{test_id}")
def run_test(
    test_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx)
    if test_id not in TEST_IDS:
        raise HTTPException(status_code=404, detail=f"Unknown test: {test_id}")
    return _svc.run_test(test_id, db, settings)


@router.get("/architecture")
def architecture_validation(
    ctx: Ctx,
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx)
    return _svc.architecture_validation(settings)


@router.get("/modules")
def module_validation(
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx)
    return _svc.module_validation(db, settings)


@router.get("/workflows")
def workflow_scenarios(
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx)
    return _svc.workflow_scenarios(db, settings)


@router.post("/workflows/{scenario_id}/simulate")
def simulate_workflow(
    scenario_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx)
    if scenario_id not in ("retail_customer", "merchant_b2b", "admin_ops"):
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {scenario_id}")
    return _svc.simulate_workflow(scenario_id, db, settings)


@router.get("/events")
def event_bus_inspector(
    ctx: Ctx,
    db: Session = Depends(get_db),
    filter: str | None = Query(None, description="Filter by order, driver, merchant, customer"),
    limit: int = Query(100, le=500),
) -> dict:
    _guard(ctx)
    return _svc.event_bus_inspector(db, aggregate_filter=filter, limit=limit)


@router.get("/fleetbase-sync")
def fleetbase_sync_monitor(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx)
    return _svc.fleetbase_sync_monitor(db)


@router.post("/chaos/{scenario}")
def chaos_test(
    scenario: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx, "diagnostics_write")
    return _svc.chaos_test(scenario, db, settings)


@router.get("/observability")
def observability(
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx)
    return _svc.observability(db, settings)


@router.post("/reports/generate")
def generate_reports(
    ctx: Ctx,
    body: ReportsRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx, "diagnostics_write")
    return _svc.generate_reports(db, settings, write_files=body.write_files)


@router.post("/e2e/run")
def run_e2e_validation(
    ctx: Ctx,
    body: E2ERunRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Enterprise End-to-End Operations Validation — all 10 phases."""
    _guard(ctx, "diagnostics_write")
    return _e2e.run_full(
        db,
        settings,
        write_files=body.write_files,
        cleanup=body.cleanup,
        merchant_order_count=body.merchant_order_count,
    )


@router.get("/e2e/phases")
def e2e_phases(ctx: Ctx) -> dict:
    _guard(ctx)
    from porterchain_api.admin_engine.e2e_validation_catalog import (
        E2E_REPORT_FILES,
        FAILURE_SCENARIOS,
        FORWARD_LOGISTICS_STEPS,
        MERCHANT_SCENARIO_STEPS,
        REVERSE_LOGISTICS_FLOW,
        SYSTEM_CHAIN,
    )

    return {
        "phases": [
            {"id": 1, "name": "System Layer Validation", "chain": list(SYSTEM_CHAIN)},
            {"id": 2, "name": "Forward Logistics", "steps": list(FORWARD_LOGISTICS_STEPS)},
            {"id": 3, "name": "Merchant Scenario", "steps": list(MERCHANT_SCENARIO_STEPS)},
            {"id": 4, "name": "Reverse Logistics", "steps": list(REVERSE_LOGISTICS_FLOW)},
            {"id": 5, "name": "Failure Scenarios", "scenarios": list(FAILURE_SCENARIOS)},
            {"id": 6, "name": "Event Bus Validation"},
            {"id": 7, "name": "Notification Validation"},
            {"id": 8, "name": "System Consistency"},
            {"id": 9, "name": "Observability"},
            {"id": 10, "name": "Report Generation", "reports": list(E2E_REPORT_FILES)},
        ]
    }
