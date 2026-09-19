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


def _tsx_blob(app_dir: Path) -> str:
    parts: list[str] = []
    for path in app_dir.rglob("*.tsx"):
        if "node_modules" in path.parts:
            continue
        parts.append(_read(path))
    for path in app_dir.rglob("*.ts"):
        if "node_modules" in path.parts or path.name.endswith(".d.ts"):
            continue
        parts.append(_read(path))
    return "\n".join(parts)


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
        app_text = _tsx_blob(app_dir)

        for step in REQUIRED_FLOW_STEPS:
            if step not in flow_text:
                failures.append(f"{name}: flow missing step {step!r}")

        for test_id in REQUIRED_TEST_IDS:
            if f'testID="{test_id}"' not in app_text and f"testID='{test_id}'" not in app_text:
                failures.append(f"{name}: App.tsx missing testID {test_id!r}")

        app_id = "com.porterchain.customer" if name == "customer" else "com.porterchain.PCD"
        if f"appId: {app_id}" not in flow_text:
            failures.append(f"{name}: flow appId must be {app_id}")

        if name == "driver":
            if "canEnterRoute" not in app_text:
                failures.append("driver: fail-closed canEnterRoute missing")
            if "development-device" not in (app_dir / "eas.json").read_text(encoding="utf-8"):
                failures.append("driver: eas.json missing development-device (iOS FCM)")

            # HS-22 — handshake types + PorterChain API :8001 only (never Fleetbase :8000 / SocketCluster).
            handshake = app_dir / "src/handshake.ts"
            types = app_dir / "src/types.ts"
            config = app_dir / "src/config.ts"
            api = app_dir / "src/api.ts"
            for path in (handshake, types, config, api):
                if not path.is_file():
                    failures.append(f"driver: missing {path.relative_to(ROOT)}")
            if types.is_file():
                types_text = _read(types)
                for needle in ("export type Handshake", "api: LinkState", "auth: LinkState"):
                    if needle not in types_text:
                        failures.append(f"driver: Handshake type missing {needle!r}")
            if handshake.is_file():
                hs = _read(handshake)
                if "runHandshake" not in hs or "idleHandshake" not in hs:
                    failures.append("driver: handshake.ts missing runHandshake/idleHandshake")
                if ":8001" not in hs:
                    failures.append("driver: handshake must point operators at :8001 on API down")
            if config.is_file():
                cfg = _read(config)
                if ":8001" not in cfg:
                    failures.append("driver: config.ts default API must be :8001")
                if ":8000" in cfg:
                    failures.append("driver: config.ts must not default to Fleetbase :8000")
            for path in sorted(app_dir.rglob("*")):
                if path.suffix not in {".ts", ".tsx"} or "node_modules" in path.parts:
                    continue
                text = _read(path)
                if ":8000" in text:
                    failures.append(f"driver: Fleetbase :8000 reference in {path.relative_to(ROOT)}")
                if "socketcluster" in text.lower():
                    failures.append(f"driver: SocketCluster reference in {path.relative_to(ROOT)}")
            if api.is_file() and "/driver-api/v1" not in _read(api):
                failures.append("driver: api.ts must call /driver-api/v1 on PorterChain API")

    print("Mobile smoke (§2.1.10 / HS-22)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1

    print("  PASS: Maestro flows + testIDs + driver handshake → :8001 (no :8000/SocketCluster)")

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
