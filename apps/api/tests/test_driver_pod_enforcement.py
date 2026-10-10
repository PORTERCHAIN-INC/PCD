"""Readiness audit #5 — POD + on-duty gates on dropoff completion, admin override + audit."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from porterchain_driver import pod_policy
from porterchain_driver.pod import ProofOfDeliveryService
from porterchain_driver.pod_policy import DriverOffDuty, PodMissing


def _merchant(rules: dict | None = None, vertical: str | None = None):
    profile: dict = {}
    if rules is not None:
        profile["settings"] = {"customer_experience": {"delivery_rules": rules}}
    if vertical:
        profile["vertical"] = vertical
    return SimpleNamespace(profile=profile)


def _order(**kw):
    base = {"id": "ord-1", "state": "AT_DESTINATION", "compliance_metadata": {}, "merchant_id": None}
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _default_flags(monkeypatch):
    monkeypatch.delenv("DRIVER_POD_ENFORCED", raising=False)
    monkeypatch.delenv("DRIVER_DUTY_REQUIRED_FOR_COMPLETION", raising=False)


# ---- requirements ------------------------------------------------------------------------

def test_default_requires_photo_or_signature_only() -> None:
    req = pod_policy.requirements_for(MagicMock(), _order(), merchant=_merchant())
    assert req["enforced"] is True
    assert req["photo_or_signature"] is True
    assert (req["signature"], req["id_check"], req["otp"]) == (False, False, False)


def test_merchant_rules_add_signature_and_id() -> None:
    req = pod_policy.requirements_for(
        MagicMock(), _order(), merchant=_merchant({"signature_required": True, "id_required": True})
    )
    assert req["signature"] and req["id_check"]
    assert "merchant_signature_required" in req["reasons"]


@pytest.mark.parametrize(
    "merchant,order",
    [
        (_merchant(vertical="medical"), _order()),
        (_merchant(), _order(compliance_metadata={"vertical": "medical"})),
        (_merchant(), _order(compliance_metadata={"chain_of_custody": {"seal_number": "S1"}})),
    ],
)
def test_pharmacy_medical_requires_id_and_signature(merchant, order) -> None:
    req = pod_policy.requirements_for(MagicMock(), order, merchant=merchant)
    assert req["signature"] and req["id_check"]
    assert "pharmacy_medical" in req["reasons"]


def test_env_kill_switch(monkeypatch) -> None:
    monkeypatch.setenv("DRIVER_POD_ENFORCED", "false")
    assert pod_policy.pod_enforced() is False
    pod_policy.assert_pod_satisfied(MagicMock(), _order())  # no raise


# ---- missing -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "have,rules,vertical,expected",
    [
        (set(), None, None, ["photo_or_signature"]),
        ({"photo"}, None, None, []),
        ({"signature"}, None, None, []),
        ({"barcode"}, None, None, ["photo_or_signature"]),
        ({"photo"}, {"signature_required": True}, None, ["signature"]),
        ({"photo", "signature"}, None, "medical", ["id_check"]),
        (set(), None, "medical", ["signature", "id_check"]),
        ({"signature", "id_check"}, None, "medical", []),
    ],
)
def test_missing_for(have, rules, vertical, expected) -> None:
    order = _order()
    req = pod_policy.requirements_for(MagicMock(), order, merchant=_merchant(rules, vertical))
    with patch.object(pod_policy, "captured_types", return_value=have):
        assert pod_policy.missing_for(MagicMock(), order, requirements=req) == expected


def test_pod_missing_payload_is_human() -> None:
    exc = PodMissing(["signature", "id_check"])
    assert str(exc) == "pod_required"
    assert isinstance(exc, PermissionError)
    assert exc.payload["missing"] == ["signature", "id_check"]
    assert "receiver's signature" in exc.payload["message"]
    assert "ID check" in exc.payload["message"]


# ---- deliver_stop gates ------------------------------------------------------------------

def _stops_with(order):
    from porterchain_driver.stops import StopsService

    svc = StopsService()
    svc._order_for_stop = MagicMock(return_value=order)  # type: ignore[method-assign]
    svc._order_to_stop = MagicMock(return_value=SimpleNamespace(stop_id="x"))  # type: ignore[method-assign]
    return svc


def test_deliver_dropoff_blocked_when_off_duty() -> None:
    order = _order()
    svc = _stops_with(order)
    with (
        patch("porterchain_driver.stops._validate_stop_action"),
        patch.object(pod_policy, "is_on_duty", return_value=False),
        pytest.raises(DriverOffDuty),
    ):
        svc.deliver_stop(MagicMock(), SimpleNamespace(id="drv-1"), "ord-1-dropoff", enforce_sequence=False)


def test_deliver_dropoff_blocked_without_proof() -> None:
    order = _order()
    svc = _stops_with(order)
    with (
        patch("porterchain_driver.stops._validate_stop_action"),
        patch("porterchain_api.merchant_engine.scan_gate_service.ScanGateService.assert_complete"),
        patch.object(pod_policy, "is_on_duty", return_value=True),
        patch.object(pod_policy, "missing_for", return_value=["photo_or_signature"]),
        pytest.raises(PodMissing) as info,
    ):
        svc.deliver_stop(MagicMock(), SimpleNamespace(id="drv-1"), "ord-1-dropoff", enforce_sequence=False)
    assert info.value.missing == ["photo_or_signature"]


def test_admin_override_skips_pod_and_duty() -> None:
    order = _order()
    svc = _stops_with(order)
    with (
        patch("porterchain_driver.stops._validate_stop_action"),
        patch("porterchain_api.merchant_engine.scan_gate_service.ScanGateService.assert_complete"),
        patch.object(pod_policy, "is_on_duty", return_value=False) as duty,
        patch.object(pod_policy, "missing_for", return_value=["photo_or_signature"]) as missing,
        patch("porterchain_driver.stops._apply_state_chain") as chain,
        patch("porterchain_driver.stops._record_stop_completion"),
        patch("porterchain_driver.earnings.EarningsService.credit_delivery"),
    ):
        svc.deliver_stop(
            MagicMock(),
            SimpleNamespace(id="drv-1"),
            "ord-1-dropoff",
            enforce_sequence=False,
            pod_override=True,
            duty_override=True,
        )
    chain.assert_called_once()
    duty.assert_not_called()
    missing.assert_not_called()


def test_pickup_not_gated_by_pod_or_duty() -> None:
    order = _order(state="AT_PICKUP")
    svc = _stops_with(order)
    with (
        patch("porterchain_driver.stops._validate_stop_action"),
        patch("porterchain_api.merchant_engine.scan_gate_service.ScanGateService.assert_complete"),
        patch.object(pod_policy, "is_on_duty", return_value=False) as duty,
        patch("porterchain_driver.stops._apply_state_chain"),
        patch("porterchain_driver.stops._record_stop_completion"),
    ):
        svc.deliver_stop(MagicMock(), SimpleNamespace(id="drv-1"), "ord-1-pickup", enforce_sequence=False)
    duty.assert_not_called()


# ---- complete_pod + id check -------------------------------------------------------------

def test_complete_pod_reports_missing_and_off_duty() -> None:
    order = _order()
    pod = ProofOfDeliveryService()
    with (
        patch("porterchain_driver.pod._order_for_stop", return_value=order),
        patch.object(pod_policy, "is_on_duty", return_value=True),
        patch.object(pod_policy, "missing_for", return_value=["signature", "id_check"]),
    ):
        res = pod.complete_pod(MagicMock(), SimpleNamespace(id="drv-1"), "ord-1-dropoff")
    assert not res.success and res.message == "pod_required:signature,id_check"
    with (
        patch("porterchain_driver.pod._order_for_stop", return_value=order),
        patch.object(pod_policy, "is_on_duty", return_value=False),
    ):
        res = pod.complete_pod(MagicMock(), SimpleNamespace(id="drv-1"), "ord-1-dropoff")
    assert not res.success and res.message == "driver_off_duty"


def test_id_check_validates_and_stores_no_identifiers() -> None:
    pod = ProofOfDeliveryService()
    order = _order()
    with patch("porterchain_driver.pod._order_for_stop", return_value=order), patch.object(
        ProofOfDeliveryService, "_record_pod"
    ) as rec:
        with pytest.raises(ValueError, match="invalid_id_type"):
            pod.capture_id_check(MagicMock(), SimpleNamespace(id="d"), "ord-1-dropoff", id_type="selfie", name_matches=True)
        with pytest.raises(ValueError, match="id_name_mismatch"):
            pod.capture_id_check(MagicMock(), SimpleNamespace(id="d"), "ord-1-dropoff", id_type="health_card", name_matches=False)
        pod.capture_id_check(
            MagicMock(), SimpleNamespace(id="d"), "ord-1-dropoff", id_type="drivers_licence", name_matches=True, age_verified=True
        )
    args = rec.call_args.args
    assert args[3] == "id_check"
    assert args[4] == "type=drivers_licence;name_match=1;age_ok=1"


def test_route_detail_mapping() -> None:
    from porterchain_api.routers.driver.navigation_pod import (
        _pod_failure_detail,
        _pod_failure_status,
    )

    assert _pod_failure_status("pod_required:id_check") == 409
    assert _pod_failure_detail("pod_required:id_check")["missing"] == ["id_check"]
    assert _pod_failure_detail("driver_off_duty")["code"] == "driver_off_duty"
    assert _pod_failure_status("invalid_otp") == 400
    assert _pod_failure_detail("invalid_otp") == "invalid_otp"


# ---- admin override ----------------------------------------------------------------------

def _admin_ctx():
    from porterchain_api.domain.admin_states import AdminRole

    return SimpleNamespace(role=AdminRole.SUPER_ADMIN, user=SimpleNamespace(id="adm-1"))


def test_admin_override_requires_reason_and_is_audited() -> None:
    from porterchain_api.admin_engine import driver_ops_service as mod

    svc = mod.AdminDriverOpsService()
    order = _order(state="AT_DESTINATION", assigned_driver_id="drv-1")
    driver = SimpleNamespace(id="drv-1")
    db = MagicMock()
    with (
        patch.object(mod.AdminDriverOpsService, "_order", return_value=order),
        patch.object(mod.AdminDriverOpsService, "_driver", return_value=driver),
        patch.object(mod, "perform") as perform,
        patch.object(mod, "commit_admin_audit") as audit,
        patch.object(pod_policy, "missing_for", return_value=["photo_or_signature"]),
        patch.object(pod_policy, "is_on_duty", return_value=False),
        patch("porterchain_api.booking_engine._core.emit_event") as emit,
    ):
        with pytest.raises(ValueError, match="reason"):
            svc.run(db, MagicMock(), _admin_ctx(), "ord-1", "complete_delivery_without_proof", "  ")
        perform.assert_not_called()
        out = svc.run(
            db, MagicMock(), _admin_ctx(), "ord-1", "complete_delivery_without_proof", "Driver phone died at door"
        )
    assert out["ok"] is True
    perform.assert_called_once()
    assert perform.call_args.args[-1] == "complete_delivery_without_proof"
    kw = audit.call_args.kwargs
    assert kw["action"] == "ops.admin.delivery_override"
    assert kw["payload"]["reason"] == "Driver phone died at door"
    assert kw["payload"]["pod_missing"] == ["photo_or_signature"]
    assert kw["payload"]["driver_on_duty"] is False
    assert emit.call_args.kwargs["event_type"] == "delivery.completed_override"
    assert emit.call_args.kwargs["publish"] is False


def test_field_admin_maps_override_action() -> None:
    from porterchain_driver import field_admin

    stops = MagicMock()
    field_admin._perform(stops, MagicMock(), MagicMock(), SimpleNamespace(id="d"), _order(), "complete_delivery_without_proof")
    kw = stops.deliver_stop.call_args.kwargs
    assert kw["pod_override"] is True and kw["duty_override"] is True
