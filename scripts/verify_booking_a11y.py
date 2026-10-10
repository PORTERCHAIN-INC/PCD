#!/usr/bin/env python3
"""Booking flow WCAG AA structure guard (§6.3.5)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FLOWS = (
    ROOT / "apps/merchant-portal/src/components/booking/BookDeliveryClient.tsx",
    ROOT / "apps/customer/src/components/send/SendClient.tsx",
)

REQUIRED = (
    'role="alert"',
    "aria-live",
    "aria-current",
    "focus-visible:ring",
)


def main() -> int:
    failures: list[str] = []
    for path in FLOWS:
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        for needle in REQUIRED:
            if needle not in text:
                failures.append(f"{rel} missing {needle!r}")

    print("Booking WCAG AA (§6.3.5)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: merchant + customer booking flows have a11y hooks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
