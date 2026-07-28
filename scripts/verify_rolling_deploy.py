#!/usr/bin/env python3
"""§2.5.7 / DD-27 — rolling API deploy via compose scale + health gates."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_YML = ROOT / ".github/workflows/deploy.yml"
RECOVER = ROOT / "infrastructure/deploy/scripts/recover-prod-stack.sh"
COMPOSE = ROOT / "infrastructure/deploy/docker-compose.prod.yml"
README = ROOT / "infrastructure/deploy/README.md"

_REQUIRED_README: tuple[str, ...] = (
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
        for snippet in ("API_REPLICAS", "repair_and_migrate.py", "recover-prod-stack.sh"):
            if snippet not in deploy:
                failures.append(f"§2.5.7 deploy.yml missing: {snippet}")
        # Scale may live in recover-prod-stack.sh (called by Deploy) — require one of the two.
        if "--scale api=" not in deploy:
            if not RECOVER.is_file() or "--scale api=" not in RECOVER.read_text(
                encoding="utf-8", errors="ignore"
            ):
                failures.append(
                    "§2.5.7 missing --scale api= in deploy.yml or recover-prod-stack.sh"
                )
    else:
        failures.append("§2.5.7 missing deploy.yml")

    if RECOVER.is_file():
        recover = RECOVER.read_text(encoding="utf-8", errors="ignore")
        if "--scale api=" not in recover:
            failures.append("§2.5.7 recover-prod-stack.sh missing: --scale api=")
        if "API_REPLICAS" not in recover:
            failures.append("§2.5.7 recover-prod-stack.sh missing: API_REPLICAS")
    else:
        failures.append("§2.5.7 missing recover-prod-stack.sh")

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
        for snippet in _REQUIRED_README:
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
