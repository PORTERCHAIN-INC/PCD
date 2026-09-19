#!/usr/bin/env python3
"""Living doc set — canonical files present, pointer stubs within cap."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CANONICAL = (
    ROOT / "ARCHITECTURE.md",
    ROOT / "AGENTS.md",
    ROOT / "FLEETBASE_MODULES.md",
    ROOT / "INTEGRATIONS.md",
    ROOT / "docs/PORTERCHAIN_CHARTER.md",
    ROOT / "docs/POINTER_STUB_INDEX.md",
    ROOT / "docs/api/PARTNER_GUIDE.md",
    ROOT / "graphify-out/GRAPH_REPORT.md",
)


def main() -> int:
    failures: list[str] = []

    for path in CANONICAL:
        if not path.is_file():
            failures.append(f"missing living doc {path.relative_to(ROOT)}")

    pointer_script = ROOT / "scripts/verify_doc_pointer_stubs.py"
    if not pointer_script.is_file():
        failures.append("missing verify_doc_pointer_stubs.py")
    else:
        proc = subprocess.run(
            [sys.executable, str(pointer_script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            failures.append("E.2 pointer stub guard failed (run validate:doc-pointers)")

    print("Doc governance guard (living canonical set)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — living docs present, pointer stubs within limit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
