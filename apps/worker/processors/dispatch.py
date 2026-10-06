"""Dispatch queue — PorterChain day-plan and suggestion jobs."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def process_dispatch(payload: dict[str, Any]) -> None:
    action = payload.get("action") or "dispatch_ready"
    if action == "geocode_import":
        job_id = payload.get("job_id")
        if not job_id:
            logger.warning("dispatch geocode_import missing job_id: %s", payload)
            return
        _geocode_import(job_id)
        return

    if action == "optimize_import":
        job_id = payload.get("job_id")
        if not job_id:
            logger.warning("dispatch optimize_import missing job_id: %s", payload)
            return
        _optimize_import(job_id)
        return

    if action == "optimize_run":
        run_id = payload.get("run_id")
        if not run_id:
            logger.warning("dispatch optimize_run missing run_id: %s", payload)
            return
        _optimize_run(run_id)
        return

    order_id = payload.get("order_id")
    if not order_id:
        logger.warning("dispatch job missing order_id: %s", payload)
        return

    if action == "score_suggestions":
        _score_suggestions(order_id)
        return

    logger.info(
        "dispatch sync skipped; PorterChain keeps the order order_id=%s action=%s",
        order_id,
        action,
    )


def _score_suggestions(order_id: str) -> None:
    """P1-2: Valhalla-matrix ranking + capability/skills/window filters → Redis cache."""
    from porterchain_api.admin_engine.control_tower.scoring import (
        compute_ranked_suggestions,
        write_suggestions_cache,
    )
    from porterchain_api.db import SessionLocal

    with SessionLocal() as db:
        try:
            result = compute_ranked_suggestions(db, order_id)
        except LookupError:
            logger.warning("score_suggestions: order %s not found", order_id)
            return
        write_suggestions_cache(order_id, result)
    logger.info(
        "score_suggestions completed: order_id=%s drivers=%s filtered=%s matrix=%s",
        order_id,
        len(result.get("drivers") or []),
        result.get("filtered_out_count"),
        result.get("matrix_source"),
    )


def _optimize_run(run_id: str) -> None:
    """One-van day plan in this worker (OR-Tools + Valhalla)."""
    import porterchain_api.user_models  # noqa: F401 — Driver FK metadata in worker
    from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService
    from porterchain_api.db import SessionLocal

    with SessionLocal() as db:
        rec = OrchestratorOpsService().get_run(run_id) or {}
        if isinstance(rec, dict) and rec.get("engine") == "porterchain":
            from porterchain_api.dispatch_engine.day_plan import finish_porterchain_run

            result = finish_porterchain_run(db, run_id, rec)
        else:
            result = OrchestratorOpsService().execute_queued_run(db, run_id)
    logger.info(
        "optimize_run completed: run_id=%s status=%s assigned=%s",
        run_id,
        result.get("status"),
        len(result.get("assignments") or []),
    )


def _geocode_import(job_id: str) -> None:
    from porterchain_api.db import SessionLocal
    from porterchain_api.merchant_engine.route_import_service import MerchantRouteImportService

    with SessionLocal() as db:
        MerchantRouteImportService().apply_geocode_job(db, job_id)
    logger.info("geocode_import completed: job_id=%s", job_id)


def _optimize_import(job_id: str) -> None:
    from porterchain_api.db import SessionLocal
    from porterchain_api.merchant_engine.route_import_service import MerchantRouteImportService

    with SessionLocal() as db:
        MerchantRouteImportService().apply_optimize_job(db, job_id)
    logger.info("optimize_import completed: job_id=%s", job_id)
