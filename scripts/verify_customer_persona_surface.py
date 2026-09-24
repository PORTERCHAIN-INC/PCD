#!/usr/bin/env python3
"""Customer persona UI/API surface smoke (dev) — substitutes Playwright until added.

Mirrors scripts/verify_anonymous_retail_surface.py. Exit 0 = green.
Catalog: docs/CUSTOMER_PERSONA_DEV_TEST_CASES.md §2–3, §19.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUSTOMER = ROOT / "apps/customer/src"
ADMIN = ROOT / "apps/admin/src"
MOBILE = ROOT / "apps/mobile-customer/src"
API_ROUTERS = ROOT / "apps/api/src/porterchain_api/routers"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _glob_text(root: Path, pattern: str) -> str:
    if not root.exists():
        return ""
    parts: list[str] = []
    for path in root.rglob(pattern):
        if "node_modules" in path.parts:
            continue
        parts.append(_read(path))
    return "\n".join(parts)


def main() -> int:
    failures: list[str] = []

    customer_pages = (
        "app/page.tsx",
        "app/dashboard/page.tsx",
        "app/book/page.tsx",
        "app/book/success/page.tsx",
        "app/track/page.tsx",
        "app/track/[trackingNumber]/page.tsx",
        "app/account/page.tsx",
        "app/notifications/page.tsx",
        "app/onboarding/page.tsx",
        "app/sign-in/[[...sign-in]]/page.tsx",
        "app/sign-up/[[...sign-up]]/page.tsx",
    )
    for rel in customer_pages:
        if not (CUSTOMER / rel).is_file():
            failures.append(f"missing customer page {rel}")

    admin_pages = (
        "app/(ops)/customers/page.tsx",
        "app/(ops)/customers/[id]/page.tsx",
        "components/customers/CustomerAddOrderModal.tsx",
        "components/customers/CustomerCreateModal.tsx",
        "lib/customers.ts",
    )
    for rel in admin_pages:
        if not (ADMIN / rel).is_file():
            failures.append(f"missing admin customers file {rel}")

    detail = _read(ADMIN / "app/(ops)/customers/[id]/page.tsx")
    for tab in ("overview", "orders", "care", "billing", "trust", "activity", "tasks"):
        if tab not in detail:
            failures.append(f"admin customer detail missing tab {tab}")

    list_page = _read(ADMIN / "app/(ops)/customers/page.tsx")
    if "Add customer" not in list_page or "CustomerCreateModal" not in list_page:
        failures.append("admin customers list should expose Add customer / CustomerCreateModal")

    lib_customers = _read(ADMIN / "lib/customers.ts")
    if "create:" not in lib_customers and 'create: (t:' not in lib_customers:
        # customersApi.create must exist for Admin mint
        if "create:" not in lib_customers:
            failures.append("admin lib/customers.ts missing create()")
    booking = _read(CUSTOMER / "lib/booking.ts")
    for needle in ("/v1/quotes", "/v1/bookings", "/v1/orders/", 'checkout_channel: "customer"'):
        if needle not in booking:
            failures.append(f"customer booking.ts missing {needle}")

    book_ui = _read(CUSTOMER / "components/booking/CustomerBookDelivery.tsx")
    for needle in ("createQuote", "isClerkConfigured"):
        if needle not in book_ui:
            failures.append(f"CustomerBookDelivery missing {needle}")
    if "mockCompleteCheckout" not in book_ui and "syncBookingCheckout" not in book_ui:
        failures.append("CustomerBookDelivery missing checkout complete path")

    modal = _read(ADMIN / "components/customers/CustomerAddOrderModal.tsx")
    if "send_payment_link" not in modal or "checkout_url" not in modal:
        failures.append("CustomerAddOrderModal missing Stripe payment-link wiring")

    api = _read(CUSTOMER / "lib/api.ts")
    for needle in (
        "/v1/customers/me/dashboard",
        "/v1/customers/me/support",
        "/v1/customers/me/privacy/export",
    ):
        if needle not in api:
            failures.append(f"customer api.ts missing {needle}")

    customers_router = _read(API_ROUTERS / "customers.py")
    admin_router = _read(API_ROUTERS / "customers_admin.py")
    if 'prefix="/v1/customers"' not in customers_router:
        failures.append("customers.py prefix drift")
    if 'prefix="/v1/admin/customers"' not in admin_router:
        failures.append("customers_admin.py prefix drift")
    if '@router.post(""' not in admin_router or "def create_customer" not in admin_router:
        failures.append("admin customers must POST create_customer")
    if "/invite" not in admin_router and 'invite"' not in admin_router:
        failures.append("admin customers must POST invite")
    if "booking-drafts" not in admin_router:
        failures.append("admin customers missing booking-drafts")

    forbidden_blob = (
        _glob_text(CUSTOMER, "*.ts")
        + _glob_text(CUSTOMER, "*.tsx")
        + _glob_text(MOBILE, "*.ts")
        + _glob_text(MOBILE, "*.tsx")
    ).lower()
    for needle in ("socketcluster", "fleetbase.io", "localhost:8000"):
        if needle in forbidden_blob:
            failures.append(f"customer apps contain forbidden {needle}")

    mobile_screens = (
        "screens/SignInScreen.tsx",
        "screens/TrackScreen.tsx",
    )
    for rel in mobile_screens:
        if not (MOBILE / rel).is_file():
            failures.append(f"missing mobile-customer {rel}")

    print("Customer persona surface smoke")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: customer + admin Customers pages, APIs, and no Fleetbase/SC/:8000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
