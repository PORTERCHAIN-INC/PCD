#!/usr/bin/env python3
"""§2.5.7 / DD-27 — rolling API deploy via compose scale + health gates."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_YML = ROOT / ".github/workflows/deploy.yml"
COMPOSE = ROOT / "infrastructure/deploy/docker-compose.prod.yml"
README = ROOT / "infrastructure/deploy/README.md"

_REQUIRED: tuple[str, ...] = (
    "--scale api=",
    "API_REPLICAS",
    "repair_and_migrate.py",
    "/health",
    "Rolling deploy",
)


def main() -> int:
    failures: list[str] = []

    if DEPLOY_YML.is_file():
        deploy = DEPLOY_YML.read_text(encoding="utf-8", errors="ignore")
        for snippet in ("--scale api=", "API_REPLICAS", "repair_and_migrate.py"):
            if snippet not in deploy:
                failures.append(f"§2.5.7 deploy.yml missing: {snippet}")
    else:
        failures.append("§2.5.7 missing deploy.yml")

    if COMPOSE.is_file():
        compose = COMPOSE.read_text(encoding="utf-8", errors="ignore")
        api_block = re.search(r"^  api:\n(.*?)(?=^  \w|\Z)", compose, re.MULTILINE | re.DOTALL)
        if not api_block:
            failures.append("§2.5.7 compose missing api service block")
        elif re.search(r"^\s+container_name:", api_block.group(1), re.MULTILINE):
            failures.append("§2.5.7 api service must not use container_name (scale)")
        if "pull_policy" not in compose:
            failures.append("§2.5.7 compose missing pull_policy for rolling image updates")
    else:
        failures.append("§2.5.7 missing docker-compose.prod.yml")

    if README.is_file():
        readme = README.read_text(encoding="utf-8", errors="ignore")
        for snippet in _REQUIRED:
            if snippet not in readme:
                failures.append(f"§2.5.7 deploy README missing: {snippet}")
    else:
        failures.append("§2.5.7 missing infrastructure/deploy/README.md")

    if failures:
        print("Rolling deploy guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Rolling deploy guard passed (§2.5.7 — scaled API replicas + health-gated deploy).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
