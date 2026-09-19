"""Company file SSOT — merchants row is source of truth; CRM is a projection."""

from __future__ import annotations

from datetime import UTC, datetime

from porterchain_api.crm_models import CrmCompany
from porterchain_api.merchant_engine.booking_flow_service import MerchantBookingFlowService
from porterchain_api.merchant_engine.contacts_service import MerchantContactsService
from porterchain_api.merchant_engine.organization_sync import project_merchant_company
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.settings_service import MerchantSettingsService
from porterchain_api.schemas_merchant import (
    AddressInput,
    MerchantBookDeliveryRequest,
    MerchantProfileUpdateRequest,
    RecipientUpdateRequest,
    SavedAddressUpdateRequest,
)


def test_profile_patch_syncs_crm_website_and_email(db, merchant_ctx) -> None:
    MerchantContactsService().ensure_company(db, merchant_ctx.merchant)
    db.commit()

    updated = MerchantProfileService().update_profile(
        db,
        merchant_ctx,
        MerchantProfileUpdateRequest(
            company_name="Northyard Logistics",
            email="ap@northyard.test",
            website="https://northyard.test",
            industry="wholesale",
        ),
    )
    assert updated.email == "ap@northyard.test"
    assert updated.company_name == "Northyard Logistics"
    assert updated.website == "https://northyard.test"
    assert "website" not in (updated.profile or {})
    assert updated.profile["identity_meta"]["updated_by"] == "merchant"

    company = db.query(CrmCompany).filter(CrmCompany.merchant_id == updated.id).one()
    assert company.email == "ap@northyard.test"
    assert company.website == "https://northyard.test"
    assert company.industry == "wholesale"
    assert company.operating_name == "Northyard Logistics"


def test_address_patch_and_set_default(db, merchant_ctx) -> None:
    svc = MerchantProfileService()
    first = svc.create_saved_address(
        db,
        merchant_ctx,
        label="HQ",
        address_type="pickup",
        formatted="100 King St W, Toronto",
        postal="M5X 1A1",
        is_default=True,
    )
    second = svc.create_saved_address(
        db,
        merchant_ctx,
        label="Dock",
        address_type="pickup",
        formatted="200 Bay St, Toronto",
        postal="M5J 2J2",
        is_default=False,
    )
    patched = svc.update_saved_address(
        db,
        merchant_ctx,
        second.id,
        SavedAddressUpdateRequest(label="Bay Street dock", postal="M5J 2J3"),
    )
    assert patched.label == "Bay Street dock"
    assert patched.postal == "M5J 2J3"

    defaulted = svc.set_default_saved_address(db, merchant_ctx, second.id)
    assert defaulted.is_default is True
    db.refresh(first)
    assert first.is_default is False


def test_recipient_patch_and_delete(db, merchant_ctx) -> None:
    svc = MerchantProfileService()
    rec = svc.create_recipient(db, merchant_ctx, name="Jane Doe", email="jane@example.com")
    updated = svc.update_recipient(
        db,
        merchant_ctx,
        rec.id,
        RecipientUpdateRequest(phone="+1 416-555-0100", company="Northyard"),
    )
    assert updated.phone == "+1 416-555-0100"
    assert updated.company == "Northyard"
    svc.delete_recipient(db, merchant_ctx, rec.id)
    assert svc.list_recipients(db, merchant_ctx) == []


def test_merchant_cannot_change_payment_terms_via_profile(db, merchant_ctx) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()
    body = MerchantProfileUpdateRequest.model_validate(
        {"company_name": "Still Net 30", "payment_terms": "IMMEDIATE"}
    )
    updated = MerchantProfileService().update_profile(db, merchant_ctx, body)
    assert updated.payment_terms == "NET_30"
    assert updated.company_name == "Still Net 30"


def test_primary_billing_contact_designation(db, merchant_ctx) -> None:
    svc = MerchantSettingsService()
    first = svc.save_billing_contact(db, merchant_ctx, name="AP", email="ap@example.com")
    second = svc.save_billing_contact(db, merchant_ctx, name="Controller", email="ctrl@example.com")
    assert first["is_primary"] is True
    assert second["is_primary"] is False
    patched = svc.patch_billing_contact(db, merchant_ctx, second["id"], is_primary=True)
    assert patched["is_primary"] is True
    contacts = {c["id"]: c for c in svc.list_billing_contacts(merchant_ctx)}
    assert contacts[first["id"]]["is_primary"] is False
    assert contacts[second["id"]]["is_primary"] is True


def test_ontario_portal_preview_rejects_vancouver(db, settings, merchant_ctx) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()
    preview = MerchantBookingFlowService().preview(
        db,
        settings,
        merchant_ctx,
        MerchantBookDeliveryRequest(
            pickup=AddressInput(formatted="100 King St W, Toronto", postal="M5X 1A1", lat=43.65, lng=-79.38),
            dropoff=AddressInput(formatted="Vancouver", postal="V6B 1A1", lat=49.28, lng=-123.12),
            scheduled_at=datetime.now(UTC),
        ),
    )
    assert preview["valid"] is False
    assert preview["error"] == "out_of_service_area"


def test_project_merchant_company_copies_billing_address(db, merchant_ctx) -> None:
    merchant_ctx.merchant.billing_address = {"formatted": "1 King St W", "city": "Toronto", "province": "ON"}
    merchant_ctx.merchant.legal_name = "Northyard Logistics Inc."
    db.flush()
    company = project_merchant_company(db, merchant_ctx.merchant)
    assert company.legal_name == "Northyard Logistics Inc."
    assert company.address["city"] == "Toronto"


def test_admin_context_writes_same_address_and_contact_stores(db, admin_ctx, merchant_ctx) -> None:
    from porterchain_api.admin_engine.merchant_org import admin_merchant_context

    seat = admin_merchant_context(db, merchant_ctx.merchant.id, admin_ctx)
    assert seat.merchant.id == merchant_ctx.merchant.id
    assert seat.user.id == merchant_ctx.user.id

    profile = MerchantProfileService()
    dock = profile.create_saved_address(
        db,
        seat,
        label="Admin dock",
        address_type="pickup",
        formatted="100 King St W, Toronto",
        postal="M5X 1A1",
        is_default=True,
    )
    rec = profile.create_recipient(db, seat, name="Site receiver", email="dock@example.com")
    contact = MerchantContactsService().create_contact(
        db,
        seat,
        {"first_name": "Avery", "last_name": "Payables", "email": "ap@example.com", "roles": ["accounts_payable"]},
    )
    bill = MerchantSettingsService().save_billing_contact(
        db, seat, name="Controller", email="ap@example.com", is_primary=True
    )

    assert dock.merchant_id == merchant_ctx.merchant.id
    assert rec.merchant_id == merchant_ctx.merchant.id
    assert contact["source"] == "manual"
    assert contact["can_delete"] is True
    assert bill["is_primary"] is True
    assert profile.list_saved_addresses(db, merchant_ctx)[0].label == "Admin dock"
    assert MerchantContactsService().list_contacts(db, merchant_ctx)[-1]["email"] == "ap@example.com"
