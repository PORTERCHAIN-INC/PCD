"""Wave 4 Batch D: preferred vehicles, billing cycle, convert CRM status, delivery honesty, customer FK."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.notification_engine.delivery_service import DeliveryDeferred, DeliveryService


def test_preferred_vehicles_rejects_outside_catalog() -> None:
    db = MagicMock()
    with patch(
        "porterchain_api.admin_engine.settings_service.AdminSettingsService.enabled_retail_vehicle_ids",
        return_value={"sedan_suv", "cargo_van"},
    ):
        with pytest.raises(ValueError, match="preferred_vehicle_not_in_catalog:truck"):
            AdminMerchantService._validate_preferred_vehicles(db, ["sedan", "truck"])


def test_preferred_vehicles_accepts_catalog_subset() -> None:
    db = MagicMock()
    with patch(
        "porterchain_api.admin_engine.settings_service.AdminSettingsService.enabled_retail_vehicle_ids",
        return_value={"sedan", "cargoVan", "suv"},
    ):
        out = AdminMerchantService._validate_preferred_vehicles(db, [" sedan ", "cargoVan", "sedan"])
    assert out == ["sedan_suv", "cargo_van"]


def test_preferred_vehicles_empty_catalog_allows_any() -> None:
    db = MagicMock()
    with patch(
        "porterchain_api.admin_engine.settings_service.AdminSettingsService.enabled_retail_vehicle_ids",
        return_value=set(),
    ):
        out = AdminMerchantService._validate_preferred_vehicles(db, ["customClass"])
    assert out == ["customclass"]


def test_update_merchant_billing_cycle_invalid() -> None:
    svc = AdminMerchantService()
    merchant = SimpleNamespace(
        id="m1",
        payment_terms="NET_30",
        credit_limit_cents=0,
        pricing_config={},
        billing_cycle="MONTHLY",
        preferred_vehicles=[],
        parent_merchant_id=None,
        profile={},
        company_name="Acme",
        phone=None,
        hst_number=None,
    )
    db = MagicMock()
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))
    svc._get_or_raise = MagicMock(return_value=merchant)  # type: ignore[method-assign]
    svc._audit = MagicMock()  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="invalid_billing_cycle"):
        svc.update_merchant_terms(db, ctx, "m1", billing_cycle="DAILY")


def test_convert_company_sets_negotiating_not_active() -> None:
    from porterchain_api.collaboration_engine.crm_contracts import CrmContractsMixin
    from porterchain_api.domain.crm_states import CompanyMerchantStatus
    from porterchain_api.domain.merchant_states import MerchantStatus

    class _Svc(CrmContractsMixin):
        def log_activity(self, *a, **k):  # noqa: ANN001
            return None

    company = SimpleNamespace(
        id="co-1",
        merchant_id=None,
        operating_name="Ops Co",
        legal_name="Ops Co Ltd",
        email="ops@example.com",
        phone=None,
        hst_number=None,
        business_number=None,
        billing_details={},
        address={},
        preferred_vehicle="sedan",
        industry=None,
        service_area=None,
        estimated_deliveries_per_month=None,
        merchant_status=None,
    )
    contact = SimpleNamespace(email="ops@example.com", company_id="co-1", is_primary=True)
    db = MagicMock()
    db.get.return_value = company
    db.query.return_value.filter.return_value.first.return_value = contact

    with (
        patch(
            "porterchain_api.domain.retail_vehicles.validate_preferred_vehicles",
            return_value=["sedan"],
        ),
        patch(
            "porterchain_api.merchant_engine.team_service.ensure_merchant_seat",
            return_value=None,
        ),
    ):
        out = _Svc().convert_company_to_merchant(db, None, "co-1", settings=None)

    assert out["created"] is True
    assert company.merchant_status == CompanyMerchantStatus.NEGOTIATING.value
    added = db.add.call_args[0][0]
    assert added.status == MerchantStatus.ONBOARDING.value


def test_sms_disabled_raises_delivery_deferred() -> None:
    svc = DeliveryService()
    with patch(
        "porterchain_api.notification_engine.delivery_service.get_platform_settings",
        return_value=SimpleNamespace(sms_enabled=False),
    ), patch(
        "porterchain_api.notification_engine.delivery_service.render_template",
        return_value=("t", "body"),
    ):
        with pytest.raises(DeliveryDeferred, match="sms_disabled"):
            svc._send_sms("+15551234567", "tpl", {})


def test_push_log_only_raises_delivery_deferred() -> None:
    svc = DeliveryService()
    with (
        patch(
            "porterchain_api.notification_engine.delivery_service.get_platform_settings",
            return_value=SimpleNamespace(push_enabled=True, push_send=False),
        ),
        patch(
            "porterchain_api.notification_engine.fcm_service.firebase_credentials_configured",
            return_value=False,
        ),
        patch(
            "porterchain_api.notification_engine.delivery_service.render_template",
            return_value=("Title", "Body"),
        ),
    ):
        with pytest.raises(DeliveryDeferred, match="push_log_only"):
            svc._send_push("tok", "tpl", {}, recipient_type="driver", recipient_id="d1")


def test_customer_ensure_sets_porterchain_user_id() -> None:
    from porterchain_api.auth.ensure_user_service import EnsureUserService

    svc = EnsureUserService()
    user = SimpleNamespace(id="pc-user-1", role=None)
    customer = SimpleNamespace(
        porterchain_user_id=None,
        email="c@example.com",
        clerk_user_id="clerk_c",
    )
    bundle = SimpleNamespace(
        admin=None,
        driver=None,
        customer=customer,
        active_merchant_users=lambda: [],
    )
    db = MagicMock()

    with (
        patch("porterchain_api.auth.ensure_user_service.load_persona_bundle", return_value=bundle),
        patch("porterchain_api.auth.ensure_user_service.emails_match", return_value=True),
        patch("porterchain_api.auth.ensure_user_service.activate_pending_user"),
    ):
        svc._refresh_account_role_hint(db, user, "clerk_c", "c@example.com")

    assert customer.porterchain_user_id == "pc-user-1"
