"""Per-engine import smoke tests (§2.1.7)."""

from __future__ import annotations

import importlib

import pytest

# Twelve bounded contexts — one smoke import each.
ENGINE_SMOKE = (
    ("booking_engine", "BookingService"),
    ("merchant_engine.billing_service", "MerchantBillingService"),
    ("driver_engine.api_service", "DriverApiService"),
    ("booking_engine.stripe_webhook_service", "StripeWebhookService"),
    ("notification_engine.engine", "NotificationEngine"),
    ("dispatch_engine.sequencer", "solve_day"),
    ("order_engine.platform_service", "OrderPlatformService"),
    ("pricing_engine.repository", "SqlAlchemyPricingRepository"),
    ("collaboration_engine.crm_service", "CrmSalesService"),
    ("support_engine.support_service", "AdminSupportService"),
    ("support_engine.claims_service", "AdminClaimsService"),
    ("gateway_engine.merchant_api", "MERCHANT_API_EVENTS"),
)


@pytest.mark.parametrize("module_path,symbol", ENGINE_SMOKE)
def test_engine_symbol_importable(module_path: str, symbol: str) -> None:
    mod = importlib.import_module(f"porterchain_api.{module_path}")
    assert hasattr(mod, symbol), f"{module_path} missing {symbol}"
