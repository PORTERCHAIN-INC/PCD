#!/usr/bin/env python3
"""§5.3.5 — deploy frequency ≥2/week policy in deploy.yml + RUNBOOK."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / ".github/workflows/deploy.yml"
RUNBOOK = ROOT / "RUNBOOK.md"
METRICS = ROOT / "docs/EXECUTION_METRICS.md"


def main() -> int:
    failures: list[str] = []

    if DEPLOY.is_file():
        text = DEPLOY.read_text(encoding="utf-8", errors="ignore")
        for needle in ("workflow_run:", "workflow_dispatch:", "workflows: [CI]"):
            if needle not in text:
                failures.append(f"§5.3.5 deploy.yml missing {needle}")
    else:
        failures.append("§5.3.5 missing deploy.yml")

    for path, needles in (
        (RUNBOOK, ("≥2/week", "Deploy workflow")),
        (METRICS, ("Deploy frequency", "target_per_week")),
    ):
        if not path.is_file():
            failures.append(f"§5.3.5 missing {path.relative_to(ROOT)}")
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for needle in needles:
                if needle not in text:
                    failures.append(f"§5.3.5 {path.name} missing: {needle}")

    if failures:
        print("Deploy frequency guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Deploy frequency guard passed (§5.3.5 — CI-on-main + manual deploy, ≥2/week target).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
