#!/usr/bin/env python3
"""§1.4.1 (v2, customer fast-book) — website guest booking is express-only.

Guests book on the website with no account: /book renders ExpressBook (live price →
/v1/express/checkout → Stripe Checkout). The heavy legacy widget/draft flow stays off the
website; signed-in customers keep the full portal on :3004.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBSITE_APP = ROOT / "website/src/app/[locale]"
FORBIDDEN_IN_APP = (
    "startBooking",
    "syncBookingCheckout",
    "mockCompleteCheckout",
    "BookingWidget",
    "getActiveBookingDraft",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def main() -> int:
    failures: list[str] = []

    required = (
        ("track/page.tsx", ("TrackLookupForm",)),
        ("track/[tracking]/page.tsx", ("getOrderByTracking",)),
        ("book/page.tsx", ("ExpressBook",)),
        ("book/continue/page.tsx", ("/book",)),
        ("book/success/page.tsx", ("BookSuccess",)),
        # Legacy /quote → guest express booking.
        ("quote/page.tsx", ("/book",)),
        ("email-preferences/page.tsx", ("EmailPreferencesView",)),
    )
    for rel, needles in required:
        path = WEBSITE_APP / rel
        if not path.is_file():
            failures.append(f"missing {rel}")
            continue
        text = _read(path)
        if not any(needle in text for needle in needles):
            failures.append(f"{rel} missing one of {needles!r}")

    portal_links = ROOT / "website/src/data/portal-links.ts"
    if "customerPortalBookUrl" not in _read(portal_links):
        failures.append("portal-links.ts missing customerPortalBookUrl")

    for path in WEBSITE_APP.rglob("*.tsx"):
        rel = path.relative_to(ROOT)
        text = _read(path)
        for forbidden in FORBIDDEN_IN_APP:
            if forbidden in text:
                failures.append(f"{rel} still imports retail booking flow ({forbidden})")

    track_detail = _read(WEBSITE_APP / "track/[tracking]/page.tsx")
    if "/v1/" not in track_detail and "getOrderByTracking" not in track_detail:
        failures.append("track detail page must call public /v1 tracking API")

    customer_booking = _read(ROOT / "apps/customer/src/lib/booking.ts")
    if "createQuote" not in customer_booking or "/v1/quotes" not in customer_booking:
        failures.append("customer portal booking.ts missing createQuote for /v1/quotes")
    website_api = _read(ROOT / "website/src/lib/api.ts")
    if "/v1/express/checkout" not in website_api:
        failures.append("website api.ts missing guest /v1/express/checkout")
    if "/v1/bookings\"" in website_api or "\"/v1/bookings\"" in website_api:
        failures.append("website must not call Clerk-bound POST /v1/bookings (use /v1/express/checkout)")
    express = _read(ROOT / "website/src/components/book/ExpressBook.tsx")
    for needle in ("website", "form_elapsed_ms"):
        if needle not in express:
            failures.append(f"ExpressBook missing abuse signal {needle!r} (honeypot / fill time)")

    home = _read(WEBSITE_APP / "page.tsx")
    if "BookingWidget" in home:
        failures.append("homepage still imports BookingWidget")

    print("Anonymous retail surface guard (§1.4.1)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: website guest express book + track; no legacy widget; abuse signals present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
