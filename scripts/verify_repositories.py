#!/usr/bin/env python3
"""§3.2.8 — repository modules exist per bounded context."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src/porterchain_api"

_REQUIRED_REPOS: dict[str, tuple[str, ...]] = {
    "booking_engine/repositories": (
        "order_repository.py",
        "quote_repository.py",
        "booking_draft_repository.py",
    ),
    "merchant_engine/repositories": ("merchant_repository.py",),
    "admin_engine/repositories": ("driver_repository.py",),
    "collaboration_engine/repositories": ("crm_repository.py",),
}


def main() -> int:
    failures: list[str] = []
    for rel_dir, files in _REQUIRED_REPOS.items():
        repo_dir = API_SRC / rel_dir
        if not repo_dir.is_dir():
            failures.append(f"§3.2.8 missing repository package: {rel_dir}")
            continue
        init_file = repo_dir / "__init__.py"
        if not init_file.is_file():
            failures.append(f"§3.2.8 missing __init__.py: {rel_dir}")
        for name in files:
            if not (repo_dir / name).is_file():
                failures.append(f"§3.2.8 missing repository: {rel_dir}/{name}")

    if failures:
        print("Repository guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    total = sum(len(v) for v in _REQUIRED_REPOS.values())
    print(f"Repository guard passed (§3.2.8 — {len(_REQUIRED_REPOS)} contexts, {total} modules).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
