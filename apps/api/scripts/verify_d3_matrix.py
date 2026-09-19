#!/usr/bin/env python3
"""D3 Phase 1 feature matrix — essential paths exist and (optionally) E2E phases pass.

Fowler post-D2: prove the monolith delivers value through thin clients before expanding.

Usage:
    pnpm validate:d3
    cd apps/api && PYTHONPATH=src python scripts/verify_d3_matrix.py --e2e
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API_SRC = ROOT / "apps/api/src/porterchain_api"
ROUTERS = API_SRC / "routers"


@dataclass
class Row:
    feature: str
    engine: str
    api_needles: tuple[str, ...]
    client_checks: tuple[tuple[Path, str], ...] = ()
    extra_paths: tuple[Path, ...] = ()
    e2e_phases: tuple[str, ...] = ()

    results: list[str] = field(default_factory=list)

    def check_static(self) -> bool:
        router_text = _router_corpus()
        for needle in self.api_needles:
            if needle not in router_text and needle not in _read(API_SRC / "services"):
                self.results.append(f"missing API route needle: {needle}")
                return False
        for path, needle in self.client_checks:
            full = ROOT / path
            if not full.is_file():
                self.results.append(f"missing client file: {path}")
                return False
            if needle not in full.read_text():
                self.results.append(f"{path} missing {needle}")
                return False
        for path in self.extra_paths:
            if not path.is_file() and not path.is_dir():
                self.results.append(f"missing path: {path.relative_to(ROOT)}")
                return False
        return True

    def check_e2e(self, phases: dict) -> bool:
        if not self.e2e_phases:
            return True
        ok = True
        for key in self.e2e_phases:
            phase = phases.get(key, {})
            overall = phase.get("overall", "FAIL")
            if overall not in ("PASS", "WARNING"):
                self.results.append(f"E2E {key}: {overall}")
                ok = False
        return ok


def _read(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    if path.is_dir():
        return "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in sorted(path.rglob("*.py"))
            if p.is_file()
        )
    return ""


def _router_corpus() -> str:
    return _read(ROUTERS)


MATRIX: tuple[Row, ...] = (
    Row(
        feature="Merchant dashboard",
        engine="merchant_engine",
        api_needles=('/dashboard", response_model=MerchantDashboardResponse',),
        client_checks=(
            (Path("apps/merchant-portal/src/lib/api.ts"), "/v1/merchant/dashboard"),
        ),
        e2e_phases=("phase_3_merchant",),
    ),
    Row(
        feature="Driver web portal",
        engine="driver_engine",
        api_needles=(
            'prefix="/driver-api/v1"',
            "/dashboard",
            "/jobs",
            "pod-photo",
        ),
        client_checks=(
            (Path("apps/driver-portal/src/lib/api.ts"), "/v1/dashboard"),
            (Path("apps/driver-portal/src/app/api/driver/[...path]/route.ts"), "/driver-api/v1"),
        ),
        extra_paths=(ROOT / "apps/driver-portal/src/app/jobs/[orderId]/page.tsx",),
        e2e_phases=("phase_2_forward_logistics",),
    ),
    Row(
        feature="Customer web portal",
        engine="booking_engine",
        api_needles=('/me/dashboard", response_model=CustomerDashboardResponse',),
        client_checks=(
            (Path("apps/customer/src/lib/api.ts"), "/v1/customers/me/dashboard"),
        ),
        e2e_phases=("phase_2_forward_logistics",),
    ),
    Row(
        feature="Dispatch",
        engine="fleetbase_engine + admin operations",
        api_needles=(
            'prefix="/v1/admin/operations"',
            "/sync/health",
            "/dispatch/orders/{order_id}/assign",
        ),
        client_checks=(
            (Path("apps/admin/src/lib/operations.ts"), "/v1/admin/operations"),
        ),
        extra_paths=(API_SRC / "fleetbase_engine",),
        e2e_phases=("phase_2_forward_logistics",),
    ),
    Row(
        feature="Routing",
        engine="Valhalla/OSRM + Fleetbase",
        api_needles=(),
        extra_paths=(
            API_SRC / "services/routing.py",
            ROOT / "services/python/porterchain_services/maps",
        ),
        e2e_phases=("phase_1_system_layer",),
    ),
    Row(
        feature="Tracking",
        engine="public orders + websockets",
        api_needles=(
            '/orders/{tracking_number}/tracking"',
            'websocket("/ws")',
        ),
        client_checks=(
            (Path("website/src/lib/api.ts"), "/v1/orders/"),
        ),
        e2e_phases=("phase_2_forward_logistics",),
    ),
    Row(
        feature="Proof of delivery",
        engine="driver_engine + Fleetbase webhook",
        api_needles=("pod-complete", 'prefix="/webhooks"', '@router.post("/fleetbase")'),
        extra_paths=(API_SRC / "driver_engine", API_SRC / "fleetbase_engine/webhook_ingress_service.py"),
        e2e_phases=("phase_2_forward_logistics",),
    ),
    Row(
        feature="Billing",
        engine="billing_engine + Stripe",
        api_needles=(
            "/billing/overview",
            'prefix="/webhooks"',
            '@router.post("/stripe")',
        ),
        client_checks=(
            (Path("apps/merchant-portal/src/lib/billing.ts"), "/v1/merchant/billing/overview"),
        ),
        e2e_phases=("phase_2_forward_logistics", "phase_3_merchant"),
    ),
    Row(
        feature="Public / partner API",
        engine="/v1/merchant-api/*",
        api_needles=(
            'prefix="/v1/merchant-api"',
            "/bookings",
            "/orders/{order_id}",
        ),
        extra_paths=(ROUTERS / "merchant_api.py",),
        e2e_phases=("phase_3_merchant",),
    ),
    Row(
        feature="Driver mobile shell",
        engine="apps/mobile-driver + mobile-theme",
        api_needles=(),
        client_checks=(
            (Path("apps/mobile-driver/src/ui/Screen.tsx"), "@porterchain/mobile-theme"),
            (Path("apps/mobile-driver/package.json"), "@porterchain/mobile-theme"),
        ),
        extra_paths=(ROOT / "packages/mobile-theme/src/tokens.ts",),
    ),
    Row(
        feature="Customer mobile shell",
        engine="apps/mobile-customer + mobile-theme",
        api_needles=(),
        client_checks=(
            (Path("apps/mobile-customer/src/ui/Screen.tsx"), "@porterchain/mobile-theme"),
            (Path("apps/mobile-customer/package.json"), "@porterchain/mobile-theme"),
        ),
        extra_paths=(ROOT / "packages/mobile-theme/src/tokens.ts",),
    ),
)


def _routing_row_ok(row: Row) -> bool:
    """Routing row uses engine files instead of route needles."""
    routing = API_SRC / "services/routing.py"
    maps = ROOT / "services/python/porterchain_services/maps"
    if not routing.is_file():
        row.results.append("missing services/routing.py")
        return False
    text = routing.read_text(encoding="utf-8")
    if "valhalla" not in text.lower() and "osrm" not in text.lower():
        row.results.append("routing.py missing valhalla/osrm integration")
        return False
    if not maps.is_dir():
        row.results.append("missing porterchain_services/maps")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify masterrule D3 Phase 1 matrix")
    parser.add_argument("--e2e", action="store_true", help="Run E2EValidationService and map phases")
    args = parser.parse_args()

    phases: dict = {}
    if args.e2e:
        sys.path.insert(0, str(ROOT / "apps/api/src"))
        from porterchain_api.admin_engine.e2e_validation_service import E2EValidationService
        from porterchain_api.config import get_settings
        from porterchain_api.db import SessionLocal

        settings = get_settings()
        with SessionLocal() as db:
            result = E2EValidationService().run_full(db, settings, cleanup=True, merchant_order_count=3)
        phases = result.get("phases", {})
        print(f"E2E overall: {result.get('overall')} (production_ready={result.get('production_ready')})")
        for key, phase in phases.items():
            overall = phase.get("overall", "?")
            if overall in ("PASS", "WARNING"):
                continue
            print(f"  {key}: {overall}")
            for step in phase.get("steps") or []:
                if step.get("status") in ("FAIL", "BLOCKER"):
                    cause = step.get("root_cause") or step.get("error") or ""
                    print(f"    - {step.get('step')}: {step.get('status')} {cause}")
            if phase.get("error"):
                print(f"    - error: {phase['error']}")

    print("D3 Phase 1 feature matrix")
    print("=" * 72)

    failures: list[str] = []
    for row in MATRIX:
        if row.feature == "Routing":
            static_ok = _routing_row_ok(row)
        else:
            static_ok = row.check_static()
        e2e_ok = row.check_e2e(phases) if args.e2e else True
        ok = static_ok and e2e_ok
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {row.feature} ({row.engine})")
        for detail in row.results:
            print(f"         {detail}")
        if not ok:
            failures.append(row.feature)

    print("=" * 72)
    if args.e2e:
        print("Mode: static + E2E phase mapping")
    else:
        print("Mode: static contracts only (add --e2e for behavioral proof)")
    if failures:
        print(f"FAIL: {len(failures)} row(s): {', '.join(failures)}")
        return 1
    print(f"PASS: all {len(MATRIX)} Phase 1 features wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
