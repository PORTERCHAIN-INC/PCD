#!/usr/bin/env python3
"""Driver mobile field-proof checklist — static wiring for FCM, GPS, POD pad/scan.

Does not replace a real device run. Prints PASS when native wiring + Maestro
hooks are present so #19 can be closed once a human confirms on-device once.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "apps/mobile-driver"


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
    app_json_path = DRIVER / "app.json"
    eas_path = DRIVER / "eas.json"
    blob = _tsx_blob(DRIVER)

    if not app_json_path.is_file():
        print("FAIL: missing apps/mobile-driver/app.json")
        return 1

    app = json.loads(_read(app_json_path))
    expo = app.get("expo") or {}
    ios = expo.get("ios") or {}
    android = expo.get("android") or {}
    plugins = expo.get("plugins") or []
    plugin_names: list[str] = []
    for p in plugins:
        if isinstance(p, str):
            plugin_names.append(p)
        elif isinstance(p, list) and p:
            plugin_names.append(str(p[0]))

    # --- FCM / push ---
    if "expo-notifications" not in plugin_names:
        failures.append("app.json missing expo-notifications plugin")
    info = ios.get("infoPlist") or {}
    bg = info.get("UIBackgroundModes") or []
    if "remote-notification" not in bg:
        failures.append("iOS UIBackgroundModes missing remote-notification")
    if not ios.get("googleServicesFile"):
        failures.append("iOS googleServicesFile missing")
    if not android.get("googleServicesFile"):
        failures.append("Android googleServicesFile missing")
    perms = android.get("permissions") or []
    if "android.permission.POST_NOTIFICATIONS" not in perms:
        failures.append("Android POST_NOTIFICATIONS missing")
    if "collectPush" not in blob and "registerPush" not in blob:
        failures.append("push collect/register not wired in TS")
    if "unregisterPush" not in blob and "unregisterRememberedPush" not in blob:
        failures.append("push unregister on sign-out missing")
    if "AppErrorBoundary" not in blob or 'testID="error-boundary"' not in blob:
        failures.append("AppErrorBoundary missing")
    if 'testID="offline-banner"' not in blob:
        failures.append("offline-banner missing on StatusRail")
    if 'kind: "fcm"' not in blob and 'PushKind = "fcm"' not in blob and 'type PushKind' not in blob:
        failures.append("FCM push kind typing missing")

    if not eas_path.is_file():
        failures.append("eas.json missing")
    else:
        eas = _read(eas_path)
        if "development-device" not in eas:
            failures.append("eas.json missing development-device (iOS FCM)")

    # --- Background GPS ---
    if "location" not in bg:
        failures.append("iOS UIBackgroundModes missing location")
    if "expo-location" not in plugin_names:
        failures.append("app.json missing expo-location plugin")
    if "android.permission.ACCESS_BACKGROUND_LOCATION" not in perms:
        failures.append("Android ACCESS_BACKGROUND_LOCATION missing")
    if "startBackgroundLocation" not in blob:
        failures.append("startBackgroundLocation missing")
    if "porterchain-driver-location" not in blob:
        failures.append("DRIVER_LOCATION_TASK name missing")
    if "expo-task-manager" not in _read(DRIVER / "package.json"):
        failures.append("expo-task-manager dependency missing")

    # --- POD signature pad + camera barcode ---
    if "SignaturePad" not in blob or 'testID="signature-pad"' not in blob:
        failures.append("SignaturePad UI / testID missing")
    if "BarcodeScannerModal" not in blob or 'testID="barcode-scanner"' not in blob:
        failures.append("BarcodeScannerModal / testID missing")
    if "expo-camera" not in plugin_names:
        failures.append("app.json missing expo-camera plugin")
    if "expo-camera" not in _read(DRIVER / "package.json"):
        failures.append("expo-camera dependency missing")
    if 'testID="pod-barcode-scan"' not in blob:
        failures.append("POD Scan with camera button missing")
    if 'testID="scan-camera"' not in blob:
        failures.append("FieldOps camera scan button missing")

    # --- Maestro hooks ---
    pod_flow = DRIVER / "maestro/pod-capture.yaml"
    if not pod_flow.is_file():
        failures.append("maestro/pod-capture.yaml missing")
    else:
        flow = _read(pod_flow)
        for needle in ("pod-capture", "signature-pad", "pod-barcode-scan"):
            if needle not in flow:
                failures.append(f"pod-capture.yaml missing {needle!r}")

    print("Driver mobile field-proof checklist")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        print("  NOTE: After PASS, still run one real-device FCM + bg-GPS smoke.")
        return 1

    print("  PASS: FCM/GPS/POD pad+scan wiring present")
    print("  NEXT: on-device — push from admin + confirm bg location while screen locked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
