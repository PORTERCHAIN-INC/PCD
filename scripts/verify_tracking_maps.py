#!/usr/bin/env python3
"""Public + customer track pages: map route + ETA panel (§6.2.3 · DES-G3)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TRACK_PAGES = (
    ("retail website", ROOT / "website/src/app/[locale]/track/[tracking]/page.tsx"),
    ("customer portal", ROOT / "apps/customer/src/app/track/[trackingNumber]/page.tsx"),
)

REQUIRED = ("TrackRouteMap", "GoogleMapsProvider", "TrackEtaPanel")


def main() -> int:
    failures: list[str] = []
    for name, path in TRACK_PAGES:
        if not path.is_file():
            failures.append(f"{name}: missing {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in REQUIRED:
            if needle not in text:
                failures.append(f"{name}: track page missing {needle}")

    snapshot = ROOT / "apps/api/src/porterchain_api/booking_engine/public_tracking_snapshot.py"
    if not snapshot.is_file():
        failures.append("missing public_tracking_snapshot.py")
    else:
        snap_text = snapshot.read_text(encoding="utf-8")
        for needle in ('"eta":', "_osrm_eta", "_scheduled_eta"):
            if needle not in snap_text:
                failures.append(f"public snapshot missing {needle}")

    print("Tracking maps + ETA gate (§6.2.3 · DES-G3)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: retail + customer track pages render map + ETA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
