#!/usr/bin/env python3
"""Appendix C — mobile shell + Maestro smoke guards."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

APPS = (
    ("mobile-customer", ROOT / "apps/mobile-customer"),
    ("mobile-driver", ROOT / "apps/mobile-driver"),
)


def main() -> int:
    failures: list[str] = []

    for name, app_dir in APPS:
        for rel in ("package.json", "App.tsx", "maestro/login-and-track.yaml"):
            if not (app_dir / rel).is_file():
                failures.append(f"{name} missing {rel}")

        pkg = (app_dir / "package.json").read_text(encoding="utf-8")
        if '"expo"' not in pkg:
            failures.append(f"{name} package.json missing expo dependency")

        eas = app_dir / "eas.json"
        if not eas.is_file():
            failures.append(f"{name} missing eas.json (C.7)")
        else:
            eas_text = eas.read_text(encoding="utf-8")
            if "build" not in eas_text:
                failures.append(f"{name} eas.json missing build profile")

    smoke = ROOT / "scripts/verify_mobile_smoke.py"
    if smoke.is_file():
        proc = subprocess.run([sys.executable, str(smoke)], cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            failures.append("verify_mobile_smoke.py failed")
            if proc.stdout:
                print(proc.stdout)
            if proc.stderr:
                print(proc.stderr)
    else:
        failures.append("missing verify_mobile_smoke.py")

    field = ROOT / "scripts/verify_mobile_field_proof.py"
    if field.is_file():
        proc = subprocess.run([sys.executable, str(field)], cwd=ROOT, capture_output=True, text=True)
        print(proc.stdout or "", end="")
        if proc.returncode != 0:
            failures.append("verify_mobile_field_proof.py failed")
            if proc.stderr:
                print(proc.stderr)
    else:
        failures.append("missing verify_mobile_field_proof.py")

    gate = ROOT / "scripts/verify_mobile_gate.py"
    if gate.is_file():
        proc = subprocess.run([sys.executable, str(gate)], cwd=ROOT, capture_output=True, text=True)
        print(proc.stdout or "", end="")
        if proc.returncode != 0:
            failures.append("verify_mobile_gate.py failed")
            if proc.stderr:
                print(proc.stderr)
    else:
        failures.append("missing verify_mobile_gate.py")

    if __import__("os").environ.get("DRIVER_API_LIVE") == "1":
        live = ROOT / "scripts/verify_driver_api_live.py"
        if live.is_file():
            proc = subprocess.run([sys.executable, str(live)], cwd=ROOT, capture_output=True, text=True)
            print(proc.stdout or "", end="")
            if proc.returncode != 0:
                failures.append("verify_driver_api_live.py failed")
                if proc.stderr:
                    print(proc.stderr)
        else:
            failures.append("missing verify_driver_api_live.py")

    if __import__("os").environ.get("DRIVER_FIELD_LIVE") == "1":
        field_live = ROOT / "scripts/verify_driver_field_live.py"
        if field_live.is_file():
            proc = subprocess.run([sys.executable, str(field_live)], cwd=ROOT, capture_output=True, text=True)
            print(proc.stdout or "", end="")
            if proc.returncode != 0:
                failures.append("verify_driver_field_live.py failed")
                if proc.stderr:
                    print(proc.stderr)
        else:
            failures.append("missing verify_driver_field_live.py")

    print("Mobile appendix guard (Appendix C)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — Expo shells, Maestro flows, EAS config present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
