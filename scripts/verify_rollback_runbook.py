#!/usr/bin/env python3
"""§5.1.9 — rollback documented <15 min via pinned image + compose scale."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_README = ROOT / "infrastructure/deploy/README.md"
DEPLOY_YML = ROOT / ".github/workflows/deploy.yml"


def main() -> int:
    failures: list[str] = []

    if DEPLOY_README.is_file():
        text = DEPLOY_README.read_text(encoding="utf-8", errors="ignore")
        for needle in ("Rollback", "Rolling deploy", "IMAGE_TAG", "15"):
            if needle not in text:
                failures.append(f"§5.1.9 deploy README missing: {needle}")
    else:
        failures.append("§5.1.9 missing infrastructure/deploy/README.md")

    if DEPLOY_YML.is_file():
        if "repair_and_migrate" not in DEPLOY_YML.read_text(encoding="utf-8", errors="ignore"):
            failures.append("§5.1.9 deploy.yml missing migration gate")
    else:
        failures.append("§5.1.9 missing deploy.yml")

    if failures:
        print("Rollback runbook guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Rollback runbook guard passed (§5.1.9 — pin image + compose up <15 min).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
