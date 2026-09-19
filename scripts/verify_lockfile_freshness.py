#!/usr/bin/env python3
"""DD-40 / §2.5.8 — lockfile freshness guard for pnpm + API requirements."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNPM_LOCK = ROOT / "pnpm-lock.yaml"
API_REQUIREMENTS = ROOT / "apps/api/requirements.txt"

REQUIREMENT_LINE = re.compile(
    r"^(?P<name>[a-zA-Z0-9][a-zA-Z0-9._-]*)(\[(?P<extras>[^\]]+)\])?(?P<op>>=|==|~=)(?P<ver>.+)$"
)


def _check_pnpm_lockfile() -> list[str]:
    if not PNPM_LOCK.is_file():
        return ["missing pnpm-lock.yaml"]

    before = PNPM_LOCK.read_text(encoding="utf-8")
    result = subprocess.run(
        ["pnpm", "install", "--lockfile-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or "pnpm install --lockfile-only failed").strip()
        return [f"pnpm lockfile refresh failed: {msg}"]

    after = PNPM_LOCK.read_text(encoding="utf-8")
    if before != after:
        return [
            "pnpm-lock.yaml is out of sync with package.json — run `pnpm install` and commit the lockfile"
        ]
    return []


def _check_api_requirements() -> list[str]:
    if not API_REQUIREMENTS.is_file():
        return ["missing apps/api/requirements.txt"]

    failures: list[str] = []
    for raw in API_REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-e"):
            continue
        if not REQUIREMENT_LINE.match(line):
            failures.append(f"apps/api/requirements.txt unpinned or invalid line: {line}")
    return failures


def main() -> int:
    failures = _check_pnpm_lockfile() + _check_api_requirements()
    if failures:
        print("Lockfile freshness guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("Lockfile freshness guard passed (pnpm-lock.yaml + API requirements).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
