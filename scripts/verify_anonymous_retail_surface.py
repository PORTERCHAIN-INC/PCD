#!/usr/bin/env python3
"""§1.4.1 — Website anonymous retail surface is quote + track only (book on :3004)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBSITE_APP = ROOT / "website/src/app/[locale]"
REDIRECT_MARKER = "portal-book-redirect"
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
        ("track/page.tsx", ("GuestTrackLookup",)),
        ("track/[tracking]/page.tsx", ("getOrderByTracking",)),
        ("book/page.tsx", ("portal-book-redirect",)),
        ("book/continue/page.tsx", ("portal-book-redirect",)),
        ("book/success/page.tsx", ("portal-book-redirect",)),
        # Legacy /quote is a capacity CTA → contact quote (not customer-portal book).
        ("quote/page.tsx", ("intent=quote", "portal-book-redirect")),
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

    api_ts = _read(ROOT / "website/src/lib/api.ts")
    if "createQuote" not in api_ts:
        failures.append("website api.ts missing createQuote for /v1/quotes")

    home = _read(WEBSITE_APP / "page.tsx")
    if "BookingWidget" in home:
        failures.append("homepage still imports BookingWidget")

    print("Anonymous retail surface guard (§1.4.1)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: website quote+track only; book/checkout → customer portal :3004")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
