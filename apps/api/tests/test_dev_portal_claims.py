"""Local Bearer-dev must not reuse staff email on merchant or customer."""

from porterchain_api.auth.clerk_identity_provider import _dev_claims
from porterchain_api.auth.dev import (
    DEV_CUSTOMER_EMAIL,
    DEV_CUSTOMER_SUBJECT,
    DEV_LEGACY_SUBJECT,
    DEV_MERCHANT_EMAIL,
    DEV_MERCHANT_SUBJECT,
    DEV_STAFF_EMAIL,
    dev_claims_for,
    is_dev_bypass_subject,
    resolve_dev_portal,
)


def test_staff_customer_merchant_are_distinct_personas() -> None:
    staff = dev_claims_for("admin")
    merchant = dev_claims_for("merchant")
    customer = dev_claims_for("customer")
    assert staff.email == DEV_STAFF_EMAIL
    assert staff.clerk_user_id == DEV_LEGACY_SUBJECT
    assert merchant.email == DEV_MERCHANT_EMAIL
    assert merchant.clerk_user_id == DEV_MERCHANT_SUBJECT
    assert customer.email == DEV_CUSTOMER_EMAIL
    assert customer.clerk_user_id == DEV_CUSTOMER_SUBJECT
    assert len({staff.clerk_user_id, merchant.clerk_user_id, customer.clerk_user_id}) == 3
    assert len({staff.email, merchant.email, customer.email}) == 3


def test_portal_header_wins_over_path() -> None:
    claims = _dev_claims(path="/v1/admin/orders", header="merchant")
    assert claims.email == DEV_MERCHANT_EMAIL
    assert claims.clerk_user_id == DEV_MERCHANT_SUBJECT


def test_session_context_path_is_staff_without_header() -> None:
    assert resolve_dev_portal(path="/v1/auth/session-context") == "admin"
    assert resolve_dev_portal(path="/v1/auth/session-context", header="customer") == "customer"
    assert resolve_dev_portal(path="/v1/auth/merchant/onboarding") == "merchant"
    assert resolve_dev_portal(path="/v1/auth/customer/onboarding") == "customer"
    assert resolve_dev_portal(path="/v1/bookings") == "customer"
    assert resolve_dev_portal(path="/v1/notifications/inbox", header="merchant") == "merchant"


def test_all_synthetic_subjects_are_bypass() -> None:
    assert is_dev_bypass_subject(DEV_LEGACY_SUBJECT)
    assert is_dev_bypass_subject(DEV_MERCHANT_SUBJECT)
    assert is_dev_bypass_subject(DEV_CUSTOMER_SUBJECT)
    assert not is_dev_bypass_subject("user_live_clerk")
