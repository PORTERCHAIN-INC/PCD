"""Idempotency key reuse for route import JSON creates."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from porterchain_api.merchant_engine.route_import_service import KIND_ROUTE_V1, MerchantRouteImportService


def test_idempotency_returns_existing_job():
    ctx = MagicMock()
    ctx.merchant.id = "m1"
    existing = MagicMock()
    existing.id = "job-existing"
    existing.kind = KIND_ROUTE_V1
    existing.job_config = {"idempotency_key": "k-1"}

    db = MagicMock()
    q = db.query.return_value
    q.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [existing]

    svc = MerchantRouteImportService()
    with patch.object(svc, "_resolve_stops") as resolve:
        out = svc.create_from_json(
            db,
            ctx,
            {
                "idempotency_key": "k-1",
                "vehicle_class": "highRoof",
                "stops": [
                    {"address": "a", "stop_type": "pickup"},
                    {"address": "b", "stop_type": "drop"},
                ],
            },
        )
        assert out is existing
        resolve.assert_not_called()
