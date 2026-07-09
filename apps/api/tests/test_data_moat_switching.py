"""Data moat + switching costs tests (§8.2 · §8.3)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.reporting.data_moat import dwell_time_dataset, network_sla_benchmark
from porterchain_api.reporting.switching_costs import integration_depth, sla_history_12mo


def _merchant_ctx(db):
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Moat Merchant {suffix}",
        email=f"moat-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"user-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def test_dwell_time_empty_db_shape(db):
    payload = dwell_time_dataset(db, window_days=30)
    assert payload["samples"] == 0
    assert "summary" in payload


def test_network_sla_benchmark_shape(db):
    payload = network_sla_benchmark(db, window_days=7)
    assert "network_on_time_pct" in payload
    assert "vertical_window_sla_pct" in payload


def test_sla_history_12mo_shape(db):
    ctx = _merchant_ctx(db)
    payload = sla_history_12mo(db, ctx.merchant.id)
    assert payload["months"] == 12
    assert len(payload["labels"]) == 12
    assert len(payload["sla_percent"]) == 12


def test_integration_depth_counts_keys(db):
    ctx = _merchant_ctx(db)
    payload = integration_depth(db, ctx.merchant.id)
    assert payload["integration_channels"]["api_keys"] >= 0
    assert payload["threshold"] == 3
