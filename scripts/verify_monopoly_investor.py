#!/usr/bin/env python3
"""§9.2 monopoly metrics + §10.1 investor metrics + §10.2 materials — dev-layer guards."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "monopoly reporting": ROOT / "apps/api/src/porterchain_api/reporting/monopoly_metrics.py",
    "monopoly service": ROOT / "apps/api/src/porterchain_api/admin_engine/monopoly_metrics_service.py",
    "monopoly router": ROOT / "apps/api/src/porterchain_api/routers/admin/monopoly_metrics.py",
    "investor service": ROOT / "apps/api/src/porterchain_api/admin_engine/investor_metrics_service.py",
    "investor router": ROOT / "apps/api/src/porterchain_api/routers/admin/investor_metrics.py",
    "white label doc": ROOT / "docs/3PL_WHITE_LABEL.md",
    "carrier pool doc": ROOT / "docs/legal/CARRIER_POOL_MODEL.md",
    "data room index": ROOT / "docs/investor/DATA_ROOM_INDEX.md",
    "tech diligence pack": ROOT / "docs/investor/TECH_DILIGENCE_PACK.md",
    "deck outline": ROOT / "docs/investor/DECK_OUTLINE.md",
    "demo video guide": ROOT / "docs/investor/DEMO_VIDEO.md",
    "test file": ROOT / "apps/api/tests/test_monopoly_investor.py",
}


def main() -> int:
    failures: list[str] = []
    for label, path in PATHS.items():
        if path.suffix == ".md" and not path.is_file():
            continue
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    monopoly = PATHS["monopoly reporting"].read_text(encoding="utf-8")
    for fn in (
        "route_density_optimization",
        "icp_geo_share",
        "white_label_adoption",
        "carrier_pool_legal_model",
        "monopoly_snapshot",
    ):
        if fn not in monopoly:
            failures.append(f"monopoly_metrics missing {fn}")

    investor = PATHS["investor service"].read_text(encoding="utf-8")
    for key in ("arr_cents", "yoy_growth_multiplier", "software_gross_margin_pct", "icp_logos"):
        if key not in investor:
            failures.append(f"investor metrics missing {key}")

    mono_router = PATHS["monopoly router"].read_text(encoding="utf-8")
    if "/monopoly-metrics" not in mono_router:
        failures.append("monopoly router missing /monopoly-metrics")

    inv_router = PATHS["investor router"].read_text(encoding="utf-8")
    if "/investor-metrics" not in inv_router:
        failures.append("investor router missing /investor-metrics")

    admin_init = (ROOT / "apps/api/src/porterchain_api/routers/admin/__init__.py").read_text(encoding="utf-8")
    for mod in ("monopoly_metrics", "investor_metrics"):
        if mod not in admin_init:
            failures.append(f"admin __init__ missing {mod} import")

    settings = (ROOT / "apps/api/src/porterchain_api/merchant_engine/settings_service.py").read_text(
        encoding="utf-8"
    )
    if "white_label_enabled" not in settings or "tracking_domain" not in settings:
        failures.append("merchant settings missing white-label branding fields")

    print("Monopoly + investor guard (§9.2 · §10.1 · §10.2)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — monopoly metrics, investor snapshot, diligence docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
