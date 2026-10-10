"""Route import service — geocode is deferred off the request path."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.merchant_engine.route_import_service import (
    MerchantRouteImportService,
)


@pytest.fixture
def ctx():
    merchant = MagicMock()
    merchant.id = "m1"
    user = MagicMock()
    user.id = "u1"
    c = MagicMock()
    c.merchant = merchant
    c.user = user
    return c


@patch("porterchain_api.merchant_engine.route_import_service.MerchantRouteImportService._enqueue_geocode")
@patch("porterchain_api.merchant_engine.import_quote.get_pricing_service")
@patch("porterchain_api.merchant_engine.import_quote.resolve_route_distance")
def test_create_from_json_defers_geocode(mock_dist, mock_pricing, mock_enq, ctx):
    mock_dist.return_value = (18000, 2400, "valhalla")
    db = MagicMock()
    svc = MerchantRouteImportService()

    with patch.object(svc, "_persist_job") as persist:
        job = MagicMock()
        job.id = "job1"
        persist.return_value = job
        result = svc.create_from_json(
            db,
            ctx,
            {
                "vehicle_class": "highRoof",
                "scheduled_at": datetime.now(UTC).isoformat(),
                "stops": [
                    {"sequence": 1, "stop_type": "pickup", "address": "100 King St W, Toronto"},
                    {"sequence": 2, "stop_type": "drop", "address": "200 Bay St, Toronto"},
                    {"sequence": 3, "stop_type": "drop", "address": "1 Dundas St E, Toronto"},
                ],
            },
        )
        assert result is job
        cfg = persist.call_args.kwargs["job_config"]
        assert cfg["quote"] is None
        assert all(s["geocode_status"] == "pending" for s in cfg["stops"])
        assert len(cfg["stops"]) == 3
        mock_enq.assert_called_once()
        mock_pricing.assert_not_called()
