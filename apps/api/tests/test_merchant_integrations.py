"""Shopify, keys, and webhooks — no ERP marketplace theater."""

from __future__ import annotations

from uuid import uuid4

import pytest

from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.gateway_engine.merchant_api import ERP_READINESS
from porterchain_api.merchant_engine.integration_copy import integration_error_message
from porterchain_api.merchant_engine.integrations_service import (
    MerchantIntegrationsService,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.shopify_service import connect_custom_app
from porterchain_api.merchant_models import Merchant, MerchantUser, SavedAddress


def _merchant_ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Integrations Co {suffix}",
        email=f"int-{suffix}@test.local",
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


def test_integration_errors_are_english():
    assert "API key" in integration_error_message("api_key_not_found")
    assert "webhook" in integration_error_message("webhook_not_found").lower()
    assert "myshopify.com" in integration_error_message("shop_domain_invalid")
    assert "pickup" in integration_error_message("pickup_address_required").lower()


def test_erp_catalog_does_not_sell_netsuite_or_woocommerce():
    ready = {row["id"] for row in ERP_READINESS if row["status"] == "ready"}
    assert ready == {"shopify"}
    assert all(row["status"] == "not_offered" for row in ERP_READINESS if row["id"] != "shopify")


def test_overview_hides_erp_marketplace(db, settings):
    ctx = _merchant_ctx(db)
    db.commit()
    overview = MerchantIntegrationsService().overview(db, ctx, api_base_url=settings.porterchain_api_url)
    assert overview["erp_platforms"] == []
    assert overview["erp_marketplace"] is False
    assert overview["available_integrations"] == ["shopify", "merchant-api"]


def test_shopify_connect_requires_pickup(db, settings):
    ctx = _merchant_ctx(db)
    db.commit()
    with pytest.raises(ValueError, match="pickup_address_required"):
        connect_custom_app(
            db,
            ctx,
            settings,
            shop_domain="demo.myshopify.com",
            admin_access_token="shpat_test",
        )


def test_shopify_connect_with_pickup(db, settings):
    ctx = _merchant_ctx(db)
    suffix = uuid4().hex[:8]
    addr = SavedAddress(
        merchant_id=ctx.merchant.id,
        label="Dock 1",
        formatted="1 King St W, Toronto",
        is_default=True,
    )
    db.add(addr)
    db.flush()
    shop_domain = f"pc-int-{suffix}.myshopify.com"
    shop = connect_custom_app(
        db,
        ctx,
        settings,
        shop_domain=shop_domain,
        admin_access_token="shpat_test",
        default_pickup_address_id=addr.id,
    )
    db.commit()
    assert shop.shop_domain == shop_domain
    assert shop.default_pickup_address_id == addr.id
