#!/usr/bin/env python3
"""Public + customer track pages: map route + ETA panel (§6.2.3 · DES-G3)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TRACK_PAGES = (
    ("retail website", ROOT / "website/src/app/[locale]/track/[tracking]/track-view.tsx"),
)
# Customer fast-book: one tracking page. The portal /track routes redirect to the website page.
PORTAL_REDIRECT = ROOT / "apps/customer/src/app/track/[trackingNumber]/page.tsx"
ENGINE_WORDS = ("OSRM)", "(Valhalla)", "Corridor (", "GPS (polled)")

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

    redirect_text = PORTAL_REDIRECT.read_text(encoding="utf-8") if PORTAL_REDIRECT.is_file() else ""
    if "redirect(" not in redirect_text or "websiteUrl" not in redirect_text:
        failures.append("customer portal /track/[n] must redirect to the website tracking page")
    eta_panel = (ROOT / "packages/maps/src/TrackEtaPanel.tsx").read_text(encoding="utf-8")
    for word in ENGINE_WORDS:
        if word in eta_panel:
            failures.append(f"customer-facing ETA label leaks engine name {word!r}")

    snapshot = ROOT / "apps/api/src/porterchain_api/booking_engine/public_tracking_snapshot.py"
    if not snapshot.is_file():
        failures.append("missing public_tracking_snapshot.py")
    else:
        snap_text = snapshot.read_text(encoding="utf-8")
        for needle in ('"eta":', "_road_eta", "_scheduled_eta"):
            if needle not in snap_text:
                failures.append(f"public snapshot missing {needle}")

    print("Tracking maps + ETA gate (§6.2.3 · DES-G3)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: one tracking page (website) renders map + ETA; portal redirects; no engine labels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
