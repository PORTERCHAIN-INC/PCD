#!/usr/bin/env python3
"""Verify *_service.py coverage floor (§2.1.11). Target 60%; CI enforces regression floor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COVERAGE_JSON = ROOT / "coverage.json"

# Raised as tests land; target remains 60% per checklist.
MIN_SERVICE_COVERAGE = 60.0
TARGET_SERVICE_COVERAGE = 60.0

# New Platform auth + admin 360 services — exclude until dedicated coverage lands (go-live).
_EXCLUDED_SERVICE_PATH_PARTS = (
    "/auth/ensure_user_service.py",
    "/auth/principal_resolution_service.py",
    "/auth/clerk_webhook_service.py",
    "/admin_engine/order_assist_service.py",
    "/admin_engine/utilization_service.py",
    "/admin_engine/customer_booking_admin_service.py",
    "/admin_engine/dispatcher_copilot_service.py",
    "/admin_engine/staff_idp_service.py",
    "/admin_engine/order_builder_service.py",
    "/admin_engine/booking_draft_admin_service.py",
    "/admin_engine/customer_admin_service.py",
    "/admin_engine/scheduled_batches_service.py",
    "/admin_engine/dispatch_suggestions_service.py",
    "/booking_engine/invoice_service.py",
)


def _aggregate_service_coverage(data: dict) -> tuple[float, int, int, list[tuple[float, int, int, str]]]:
    statements = missing = 0
    per_file: list[tuple[float, int, int, str]] = []
    for path, info in data.get("files", {}).items():
        if "_service.py" not in path:
            continue
        norm = path.replace("\\", "/")
        if any(part in norm for part in _EXCLUDED_SERVICE_PATH_PARTS):
            continue
        file_stmts = info["summary"]["num_statements"]
        file_miss = info["summary"]["missing_lines"]
        file_cov = file_stmts - file_miss
        statements += file_stmts
        missing += file_miss
        pct_file = (file_cov / file_stmts * 100) if file_stmts else 100.0
        per_file.append((pct_file, file_cov, file_stmts, norm.rsplit("/", 1)[-1]))
    covered = statements - missing
    pct = (covered / statements * 100) if statements else 0.0
    per_file.sort()
    return pct, covered, statements, per_file


def main() -> int:
    if not COVERAGE_JSON.is_file():
        print("FAIL: run pytest with --cov-report=json first")
        return 1

    pct, covered, total, per_file = _aggregate_service_coverage(json.loads(COVERAGE_JSON.read_text()))
    print(f"Service coverage: {pct:.1f}% ({covered}/{total} stmts on *_service.py)")
    print(f"  floor: {MIN_SERVICE_COVERAGE:.0f}%  target: {TARGET_SERVICE_COVERAGE:.0f}%")

    if pct + 1e-9 < MIN_SERVICE_COVERAGE:
        print(f"FAIL: below floor {MIN_SERVICE_COVERAGE:.0f}%")
        print("  lowest-coverage included services:")
        for file_pct, file_cov, file_stmts, name in per_file[:12]:
            print(f"    {file_pct:5.1f}%  {file_cov}/{file_stmts}  {name}")
        return 1
    if pct + 1e-9 < TARGET_SERVICE_COVERAGE:
        print(f"WARN: below target {TARGET_SERVICE_COVERAGE:.0f}% — add service integration tests")
    else:
        print("PASS: target met")
    print("PASS: service coverage floor OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
