"""P3 — verification source badges + quality bonus scoring."""

from __future__ import annotations

from uuid import uuid4

from porterchain_api.admin_engine.driver360_board import (
    health_score,
    verification_quality_bonus,
    verification_score,
)
from porterchain_api.admin_engine.control_tower.scoring import driver_verification_gap
from porterchain_api.admin_models import Driver
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_engine.verification_sources import (
    is_provider_verified,
    resolve_source,
    verification_sources_payload,
)


def _driver(**kwargs) -> Driver:
    suffix = uuid4().hex[:8]
    base = dict(
        id=str(uuid4()),
        email=f"p3-{suffix}@test.porterchain.com",
        full_name=f"P3 Driver {suffix}",
        status=DriverStatus.APPROVED.value,
        license_verified=True,
        insurance_verified=True,
        vehicle_verified=True,
        background_check_status="cleared",
        documents={},
    )
    base.update(kwargs)
    return Driver(**base)


def test_resolve_source_auto_and_manual() -> None:
    assert resolve_source({"verification_source": "auto", "provider": "stripe_identity"}) == "auto"
    assert resolve_source({"verification_source": "rules", "provider": "ontario_abstract"}) == "rules"
    assert resolve_source({"verification_source": "manual", "provider": "admin"}) == "manual"
    assert resolve_source({"provider": "checkr", "verified": True}) == "auto"


def test_quality_bonus_weights_provider_verified() -> None:
    manual = _driver(
        documents={
            "license": {"verified": True, "verification_source": "manual"},
            "background_check": {"verified": True, "verification_source": "manual"},
        }
    )
    auto = _driver(
        documents={
            "license": {
                "verified": True,
                "verification_source": "auto",
                "provider": "stripe_identity",
            },
            "background_check": {
                "verified": True,
                "verification_source": "auto",
                "provider": "checkr",
            },
            "abstract": {
                "verified": True,
                "verification_source": "rules",
                "provider": "ontario_abstract",
            },
        }
    )
    assert verification_score(manual) == 4
    assert verification_quality_bonus(manual) == 0
    assert verification_quality_bonus(auto) >= 3
    metrics = {
        "completion_rate": 90,
        "cancellation_rate": 0,
        "incidents": 0,
        "orders_today": 0,
        "lifetime_orders": 10,
        "acceptance_rate": 90,
    }
    assert health_score(auto, metrics) > health_score(manual, metrics)


def test_gap_expired_docs() -> None:
    expired = _driver(
        insurance_verified=True,
        documents={"insurance": {"status": "expired", "verified": False}},
    )
    assert driver_verification_gap(expired) == "driver_insurance_expired"

    clean = _driver(documents={"abstract": {"status": "rejected", "verified": False}})
    assert driver_verification_gap(clean) is None


def test_sources_payload_includes_keys() -> None:
    driver = _driver(
        documents={
            "license": {
                "verified": True,
                "verification_source": "auto",
                "provider": "stripe_identity",
            }
        }
    )
    payload = verification_sources_payload(driver)
    assert payload["license"]["source"] == "auto"
    assert is_provider_verified(payload["license"]) or payload["license"]["verified"]
    assert "background_check" in payload
    assert "abstract" in payload
