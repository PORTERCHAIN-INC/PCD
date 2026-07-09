#!/usr/bin/env python3
"""§8.1.2–8.1.5 medical + §8.1.8–8.1.9 food vertical workflow guards."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "migration": ROOT / "apps/api/alembic/versions/p9q0r1s2t3u4_compliance_metadata.py",
    "compliance helper": ROOT / "apps/api/src/porterchain_api/booking_engine/compliance_metadata.py",
    "medical service": ROOT / "apps/api/src/porterchain_api/booking_engine/medical_compliance.py",
    "order model": ROOT / "apps/api/src/porterchain_api/booking_models.py",
    "driver model": ROOT / "apps/api/src/porterchain_api/admin_models.py",
    "schema": ROOT / "apps/api/src/porterchain_api/schemas_merchant.py",
    "ops assign": ROOT / "apps/api/src/porterchain_api/admin_engine/operations_service.py",
    "buckets": ROOT / "apps/api/src/porterchain_api/order_engine/buckets.py",
    "audit export router": ROOT / "apps/api/src/porterchain_api/routers/admin/orders.py",
    "orders service": ROOT / "apps/api/src/porterchain_api/admin_engine/orders_service.py",
    "notification template": ROOT / "apps/api/src/porterchain_api/notification_engine/templates.py",
    "merchant UI": ROOT / "apps/merchant-portal/src/components/booking/BookDeliveryClient.tsx",
    "compliance test": ROOT / "apps/api/tests/test_compliance_metadata.py",
    "food sla test": ROOT / "apps/api/tests/test_food_dispatch_sla.py",
}


def main() -> int:
    failures: list[str] = []
    for label, path in PATHS.items():
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    schema = PATHS["schema"].read_text(encoding="utf-8")
    for field in ("custodian_name", "requires_cold_chain", "delivery_window_end"):
        if field not in schema:
            failures.append(f"MerchantBookDeliveryRequest missing {field}")

    ops = PATHS["ops assign"].read_text(encoding="utf-8")
    if "driver_not_medical_certified" not in ops:
        failures.append("operations_service missing medical cert gate")

    buckets = PATHS["buckets"].read_text(encoding="utf-8")
    if "dispatch_queue_sort_key" not in buckets:
        failures.append("buckets missing food SLA dispatch sort")

    router = PATHS["audit export router"].read_text(encoding="utf-8")
    if "/audit-export" not in router or "/temperature" not in router:
        failures.append("admin orders router missing audit export or temperature endpoint")

    ui = PATHS["merchant UI"].read_text(encoding="utf-8")
    if "Chain of custody" not in ui or "Cold chain" not in ui:
        failures.append("BookDeliveryClient missing medical/food vertical fields")

    templates = PATHS["notification template"].read_text(encoding="utf-8")
    if "temp_excursion" not in templates:
        failures.append("notification templates missing temp_excursion")

    print("Medical + food vertical guards (§8.1.2–8.1.9)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — compliance metadata, cert-gated assign, SLA dispatch, alerts, UI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
