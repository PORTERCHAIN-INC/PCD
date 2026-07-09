#!/usr/bin/env python3
"""Mobile Maestro smoke guard (§2.1.10) — flow structure + testID wiring."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

APPS = (
    ("customer", ROOT / "apps/mobile-customer"),
    ("driver", ROOT / "apps/mobile-driver"),
)

REQUIRED_TEST_IDS = ("mobile-sign-in", "dev-sign-in", "mobile-track")
REQUIRED_FLOW_STEPS = ("launchApp", "mobile-sign-in", "dev-sign-in", "mobile-track")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []

    for name, app_dir in APPS:
        flow = app_dir / "maestro/login-and-track.yaml"
        app_tsx = app_dir / "App.tsx"

        if not flow.is_file():
            failures.append(f"{name}: missing {flow.relative_to(ROOT)}")
            continue
        if not app_tsx.is_file():
            failures.append(f"{name}: missing App.tsx")
            continue

        flow_text = _read(flow)
        app_text = _read(app_tsx)

        for step in REQUIRED_FLOW_STEPS:
            if step not in flow_text:
                failures.append(f"{name}: flow missing step {step!r}")

        for test_id in REQUIRED_TEST_IDS:
            if f'testID="{test_id}"' not in app_text and f"testID='{test_id}'" not in app_text:
                failures.append(f"{name}: App.tsx missing testID {test_id!r}")

        app_id = "com.porterchain.customer" if name == "customer" else "com.porterchain.driver"
        if f"appId: {app_id}" not in flow_text:
            failures.append(f"{name}: flow appId must be {app_id}")

    print("Mobile smoke (§2.1.10)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1

    print("  PASS: Maestro flows + testIDs for customer + driver")

    if shutil.which("maestro") and __import__("os").environ.get("MAESTRO_RUN") == "1":
        for name, app_dir in APPS:
            flow = app_dir / "maestro/login-and-track.yaml"
            print(f"  RUN: maestro test {flow.relative_to(ROOT)}")
            result = subprocess.run(["maestro", "test", str(flow)], cwd=ROOT, check=False)
            if result.returncode != 0:
                failures.append(f"{name}: maestro run failed")
        if failures:
            for item in failures:
                print(f"  FAIL: {item}")
            return 1
        print("  PASS: maestro execution")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
