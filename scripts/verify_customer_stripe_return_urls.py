#!/usr/bin/env python3
"""Customer portal Stripe return URLs — §0.6.5 dev guard."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("apps/api/src/porterchain_api/config.py", "customer_checkout_success_url"),
    ("apps/api/src/porterchain_api/services/stripe_service.py", 'checkout_channel == "customer"'),
    ("apps/api/src/porterchain_api/schemas_booking.py", 'checkout_channel: Literal["retail", "customer"]'),
    ("apps/customer/src/lib/booking.ts", 'checkout_channel: "customer"'),
    ("apps/customer/src/app/book/success/page.tsx", "syncBookingCheckout"),
    ("apps/api/.env.example", "CUSTOMER_CHECKOUT_SUCCESS_URL=http://localhost:3004/book/success"),
    ("env/production.env.example", "CUSTOMER_CHECKOUT_SUCCESS_URL=https://customer.porterchain.com/book/success"),
    (
        "infrastructure/deploy/docker-compose.prod.yml",
        "CUSTOMER_CHECKOUT_SUCCESS_URL: https://customer.porterchain.com/book/success",
    ),
)


def main() -> int:
    failures: list[str] = []
    for rel, needle in CHECKS:
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"missing {rel}")
            continue
        if needle not in path.read_text(encoding="utf-8"):
            failures.append(f"{rel} missing {needle!r}")

    print("Customer Stripe return URL guard (§0.6.5)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: customer portal checkout returns to /book/success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
