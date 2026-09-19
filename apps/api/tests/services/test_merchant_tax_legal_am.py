"""AM — last writer on shared tax/legal fields."""

from __future__ import annotations

from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.collaboration_engine.crm_service import CrmSalesService
from porterchain_api.merchant_engine.contacts_service import MerchantContactsService
from porterchain_api.merchant_engine.organization_sync import tax_legal_snapshot
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.settings_service import MerchantSettingsService
from porterchain_api.schemas_merchant import MerchantProfileUpdateRequest


def test_tax_patch_does_not_wipe_legal_name(db, merchant_ctx) -> None:
    MerchantProfileService().update_profile(
        db,
        merchant_ctx,
        MerchantProfileUpdateRequest(legal_name="Northyard Logistics Inc."),
    )
    MerchantSettingsService().update_tax(
        db,
        merchant_ctx,
        MerchantProfileUpdateRequest(hst_number="123456789RT0001", tax_exempt=True, tax_region="ON"),
    )
    snap = tax_legal_snapshot(merchant_ctx.merchant)
    assert snap["legal_name"] == "Northyard Logistics Inc."
    assert snap["hst_number"] == "123456789RT0001"
    assert snap["tax_exempt"] is True
    assert snap["tax_legal_meta"]["updated_by"] == "merchant"
    assert "hst_number" in snap["tax_legal_meta"]["fields"]


def test_admin_legal_name_does_not_wipe_merchant_hst(db, admin_ctx, merchant_ctx) -> None:
    MerchantProfileService().update_profile(
        db,
        merchant_ctx,
        MerchantProfileUpdateRequest(hst_number="111111111RT0001", business_number="111111111"),
    )
    AdminMerchantService().update_merchant_terms(
        db,
        admin_ctx,
        merchant_ctx.merchant.id,
        legal_name="Admin Legal Inc.",
        tax_exempt=True,
        tax_region="ON",
    )
    db.refresh(merchant_ctx.merchant)
    snap = tax_legal_snapshot(merchant_ctx.merchant)
    assert snap["legal_name"] == "Admin Legal Inc."
    assert snap["hst_number"] == "111111111RT0001"
    assert snap["business_number"] == "111111111"
    assert snap["tax_exempt"] is True
    assert snap["tax_legal_meta"]["updated_by"] == "admin"
    assert "legal_name" in snap["tax_legal_meta"]["fields"]
    assert "hst_number" not in snap["tax_legal_meta"]["fields"]


def test_empty_string_clears_hst(db, merchant_ctx) -> None:
    MerchantProfileService().update_profile(
        db,
        merchant_ctx,
        MerchantProfileUpdateRequest(hst_number="222222222RT0001"),
    )
    MerchantProfileService().update_profile(
        db,
        merchant_ctx,
        MerchantProfileUpdateRequest(hst_number=""),
    )
    assert merchant_ctx.merchant.hst_number is None


def test_crm_write_on_linked_company_updates_merchant(db, merchant_ctx) -> None:
    company = MerchantContactsService().ensure_company(db, merchant_ctx.merchant)
    db.commit()
    CrmSalesService().update_company(
        db,
        company.id,
        {"hst_number": "333333333RT0001", "legal_name": "CRM Legal Inc."},
    )
    db.refresh(merchant_ctx.merchant)
    snap = tax_legal_snapshot(merchant_ctx.merchant)
    assert snap["hst_number"] == "333333333RT0001"
    assert snap["legal_name"] == "CRM Legal Inc."
    assert snap["tax_legal_meta"]["updated_by"] == "admin"
    db.refresh(company)
    assert company.hst_number == "333333333RT0001"
    assert company.legal_name == "CRM Legal Inc."
