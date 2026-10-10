"""Enterprise Validation & Diagnostics API — /v1/admin/diagnostics/*"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_service import (
    TEST_CATALOG,
    TEST_IDS,
    AdminDiagnosticsService,
)
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas_admin import ReportsRequest
from porterchain_api.schemas_health import HealthDashboardResponse

router = APIRouter(prefix="/v1/admin/diagnostics", tags=["diagnostics"])

_svc = AdminDiagnosticsService()
Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _guard(ctx: AdminContext, module: str = "diagnostics") -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/center")
def diagnostics_center(
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx)
    return _svc.center(db, settings)


@router.get("/health", response_model=HealthDashboardResponse)
def diagnostics_health(
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthDashboardResponse:
    _guard(ctx)
    return HealthDashboardResponse.model_validate(_svc.health_dashboard(db, settings))


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


@router.get("/day-plan")
def day_plan_monitor(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Day-plan scorecard for diagnostics (OR-Tools + Valhalla)."""
    _guard(ctx)
    return _svc.day_plan_monitor(db)


@router.get("/merchant-webhook-delivery")
def merchant_webhook_delivery_monitor(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx)
    return _svc.merchant_webhook_delivery_monitor(db)


@router.get("/ai-usage")
def ai_usage(
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(40, ge=1, le=100),
) -> dict:
    """NVIDIA NIM / LLM usage ledger for diagnostics (read-only)."""
    from porterchain_api.intelligence_engine.usage import ai_usage_summary

    _guard(ctx)
    return ai_usage_summary(db, limit=limit)


@router.get("/execution-metrics")
def execution_metrics(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx)
    return _svc.execution_metrics_dashboard(db)


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
