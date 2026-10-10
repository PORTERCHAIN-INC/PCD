#!/usr/bin/env python3
"""§4.1–4.2 Phase 2 scaffolds — intelligence present; analytics dead weight removed."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INTEL_FILES = (
    "features.py",
    "copilot_service.py",
    "monitoring.py",
    "pricing_model.py",
    "forecast_service.py",
)

PATHS = {
    "analytics etl stub": ROOT / "apps/api/src/porterchain_api/analytics_engine/etl_service.py",
    "pen test doc": ROOT / "docs/compliance/PEN_TEST.md",
}


def main() -> int:
    failures: list[str] = []
    intel_dir = ROOT / "apps/api/src/porterchain_api/intelligence_engine"

    for name in INTEL_FILES:
        path = intel_dir / name
        if not path.is_file():
            failures.append(f"missing intelligence_engine/{name}")

    for label, path in PATHS.items():
        if path.suffix == ".md" and not path.is_file():
            continue
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    booking = (ROOT / "apps/api/src/porterchain_api/booking_models.py").read_text(encoding="utf-8")
    for cls in ("class AnalyticsEvent", "class AnalyticsStopLeg"):
        if cls in booking:
            failures.append(f"booking_models still defines {cls} (one-SoT: drop dead scaffold)")

    etl = PATHS["analytics etl stub"].read_text(encoding="utf-8")
    if "analytics_tables_removed" not in etl:
        failures.append("etl_service must stub-skip (analytics tables removed)")

    print("Phase 2 scaffold guard (§4.1–4.2)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — intelligence scaffolds present; analytics scaffold removed (one-SoT)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
