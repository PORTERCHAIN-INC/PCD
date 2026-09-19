"""Monopoly + investor metrics tests (§9.2 · §10.1)."""

from __future__ import annotations

from porterchain_api.admin_engine.investor_metrics_service import InvestorMetricsService
from porterchain_api.admin_engine.monopoly_metrics_service import MonopolyMetricsService
from porterchain_api.reporting.monopoly_metrics import (
    carrier_pool_legal_model,
    icp_geo_share,
    monopoly_snapshot,
    route_density_optimization,
    white_label_adoption,
)


def test_route_density_empty_shape(db):
    payload = route_density_optimization(db, window_days=7)
    assert payload["window_days"] == 7
    assert "hotspots" in payload
    assert isinstance(payload["hotspots"], list)


def test_icp_geo_share_shape(db):
    payload = icp_geo_share(db, window_days=30)
    assert "icp_geo_share_pct" in payload
    assert "target_pct" in payload
    assert "meets_target" in payload


def test_white_label_adoption_shape(db):
    payload = white_label_adoption(db)
    assert "merchants_total" in payload
    assert "adoption_pct" in payload


def test_carrier_pool_legal_model():
    payload = carrier_pool_legal_model()
    assert payload["model"] == "independent_contractor_carrier_pool"
    assert "docs" in payload


def test_monopoly_snapshot_keys(db):
    payload = monopoly_snapshot(db, window_days=14)
    for key in ("route_density", "icp_geo_share", "white_label", "carrier_pool_legal"):
        assert key in payload


def test_investor_metrics_shape(db):
    svc = InvestorMetricsService()
    payload = svc.snapshot(db)
    assert "metrics" in payload
    metrics = payload["metrics"]
    for key in ("arr_cents", "yoy_growth_multiplier", "software_gross_margin_pct", "icp_logos"):
        assert key in metrics
        assert "target" in metrics[key]
        assert "meets_target" in metrics[key]


def test_monopoly_service_delegates(db):
    svc = MonopolyMetricsService()
    payload = svc.snapshot(db, window_days=7)
    assert payload["route_density"]["window_days"] == 7
