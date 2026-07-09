#!/usr/bin/env python3
"""§4.1–4.2 Phase 2 scaffolds — files present, flags default off."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INTEL_FILES = (
    "features.py",
    "eta_service.py",
    "dispatch_scorer.py",
    "copilot_service.py",
    "monitoring.py",
    "assignment_service.py",
    "pricing_model.py",
    "forecast_service.py",
)

PATHS = {
    "analytics etl": ROOT / "apps/api/src/porterchain_api/analytics_engine/etl_service.py",
    "analytics migration": ROOT / "apps/api/alembic/versions/s2t3u4v5w6x7_analytics_schema.py",
    "analytics events model": ROOT / "apps/api/src/porterchain_api/booking_models.py",
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
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    models = PATHS["analytics events model"].read_text(encoding="utf-8")
    for cls in ("class AnalyticsEvent", "class AnalyticsStopLeg"):
        if cls not in models:
            failures.append(f"booking_models missing {cls}")

    etl = PATHS["analytics etl"].read_text(encoding="utf-8")
    if "ingest_domain_event" not in etl or "ingest_stop_leg" not in etl:
        failures.append("etl_service incomplete")

    print("Phase 2 scaffold guard (§4.1–4.2)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — analytics + intelligence Phase 2 scaffolds present (not prod-trained)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
