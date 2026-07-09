#!/usr/bin/env python3
"""B.17 — POD media retention documented."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOC = ROOT / "docs/compliance/POD_MEDIA_RETENTION.md"
POD_SERVICE = ROOT / "services/driver-platform/porterchain_driver/pod.py"
NAV_ROUTER = ROOT / "apps/api/src/porterchain_api/routers/driver/navigation_pod.py"


def main() -> int:
    failures: list[str] = []

    for label, path in (("doc", DOC), ("pod service", POD_SERVICE), ("nav router", NAV_ROUTER)):
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    doc = DOC.read_text(encoding="utf-8")
    for needle in ("retention", "capture_photo", "Phase 2"):
        if needle not in doc:
            failures.append(f"POD_MEDIA_RETENTION.md missing {needle!r}")

    pod = POD_SERVICE.read_text(encoding="utf-8")
    if "capture_photo" not in pod:
        failures.append("pod.py missing capture_photo")

    print("POD media guard (B.17)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — POD capture code + retention doc")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
