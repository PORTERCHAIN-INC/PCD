"""Route import service — geocode mocked, quote path uses supplied lat/lng."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.merchant_engine.import_geocode import GeocodeResult
from porterchain_api.merchant_engine.route_import_service import MerchantRouteImportService


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


def _geo(lat: float, lng: float, raw: str) -> GeocodeResult:
    return GeocodeResult(
        lat=lat,
        lng=lng,
        formatted=raw,
        status="ok",
        confidence=0.9,
        unit=None,
        raw=raw,
        geocode_query=raw,
        issues=[],
    )


@patch("porterchain_api.merchant_engine.route_import_service.get_pricing_service")
@patch("porterchain_api.merchant_engine.route_import_service.resolve_route_distance")
@patch("porterchain_api.merchant_engine.route_import_service.geocode_stop")
def test_create_from_json_builds_quote(mock_geo, mock_dist, mock_pricing, ctx):
    mock_geo.side_effect = [
        _geo(43.65, -79.38, "pickup"),
        _geo(43.66, -79.39, "drop1"),
        _geo(43.67, -79.40, "drop2"),
    ]
    mock_dist.return_value = (18000, 2400, "valhalla")
    breakdown = MagicMock()
    breakdown.final_cents = 28500
    breakdown.subtotal_cents = 28500
    breakdown.tax_cents = 0
    breakdown.items = []
    mock_pricing.return_value.calculate_merchant.return_value = breakdown

    db = MagicMock()
    svc = MerchantRouteImportService()

    # avoid real DB: stub persist
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
        assert cfg["quote"]["amount_cents"] == 28500
        assert cfg["quote"]["routing_source"] == "valhalla"
        assert cfg["quote"]["total_drops"] == 2
        assert len(cfg["stops"]) == 3
