"""Dispatch queue — Fleetbase sync jobs (DD-05a)."""

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

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
    from porterchain_api.booking_models import Order

    settings = get_settings()
    with SessionLocal() as db:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.warning("dispatch job: order %s not found", order_id)
            return

        sync = BookingSyncService()
        if action == "assign":
            driver_id = payload.get("driver_id")
            fleetbase_driver_id = None
            if driver_id:
                from porterchain_api.admin_models import Driver

                driver = db.query(Driver).filter(Driver.id == driver_id).first()
                if not driver:
                    logger.warning("dispatch assign: driver %s not found", driver_id)
                else:
                    if not driver.fleetbase_driver_id:
                        sync.push_driver(db, settings, driver)
                    fleetbase_driver_id = driver.fleetbase_driver_id
            sync.push_driver_assignment(
                db,
                settings,
                order,
                fleetbase_driver_id=fleetbase_driver_id,
                driver_id=driver_id,
            )
        else:
            sync.push_order(db, settings, order)
        db.commit()

    logger.info("dispatch job completed: order_id=%s action=%s", order_id, action)


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
    """Step 2 Wave 0: Fleetbase orchestrator preview → Redis (not the API thread)."""
    import porterchain_api.user_models  # noqa: F401 — Driver FK metadata in worker
    from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService
    from porterchain_api.db import SessionLocal

    with SessionLocal() as db:
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
