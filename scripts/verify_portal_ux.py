#!/usr/bin/env python3
"""Portal UX guard — empty states + loading skeletons (§6.3.2–6.3.3)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

UI_EXPORTS = ROOT / "packages/ui/package.json"
PORTALS = (
    "apps/merchant-portal",
    "apps/driver-portal",
    "apps/customer",
    "apps/admin",
)

REQUIRED_UI_EXPORTS = ("./empty-state", "./loading")
REQUIRED_IMPORTS = (
    "@porterchain/ui/empty-state",
    "@porterchain/ui/loading",
)

# Paths that must import shared loading or empty-state (hydrated shells / list UIs).
PORTAL_WIRING: dict[str, tuple[str, ...]] = {
    "apps/merchant-portal": (
        "src/components/portal/ModuleGate.tsx",
        "src/components/orders/OrdersTable.tsx",
        "src/components/reports/ReportsClient.tsx",
        "src/app/(portal)/loading.tsx",
    ),
    "apps/driver-portal": (
        "src/components/DriverShell.tsx",
        "src/components/dashboard/DashboardClient.tsx",
        "src/components/jobs/JobsListClient.tsx",
        "src/app/loading.tsx",
    ),
    "apps/customer": (
        "src/components/orders/OrdersClient.tsx",
        "src/components/notifications/NotificationsClient.tsx",
        "src/app/loading.tsx",
    ),
    "apps/admin": (
        "src/app/(ops)/loading.tsx",
        "src/components/operations/OpsTowerFallback.tsx",
    ),
}


def main() -> int:
    failures: list[str] = []

    ui_pkg = UI_EXPORTS.read_text(encoding="utf-8")
    for export in REQUIRED_UI_EXPORTS:
        if export not in ui_pkg:
            failures.append(f"packages/ui missing export {export}")

    for portal in PORTALS:
        pkg = ROOT / portal / "package.json"
        if not pkg.is_file():
            failures.append(f"{portal}: missing package.json")
            continue
        text = pkg.read_text(encoding="utf-8")
        if "@porterchain/ui" not in text:
            failures.append(f"{portal}: missing @porterchain/ui dependency")

        for rel in PORTAL_WIRING.get(portal, ()):
            path = ROOT / portal / rel
            if not path.is_file():
                failures.append(f"{portal}: missing {rel}")
                continue
            src = path.read_text(encoding="utf-8")
            if not any(imp in src for imp in REQUIRED_IMPORTS):
                failures.append(f"{portal}/{rel}: must import @porterchain/ui empty-state or loading")

    print("Portal UX (§6.3.2–6.3.3)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: shared EmptyState + skeletons wired in merchant, driver, customer, admin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
