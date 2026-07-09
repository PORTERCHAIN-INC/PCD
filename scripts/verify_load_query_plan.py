#!/usr/bin/env python3
"""§5.4.4 — DB query plan review documented for load-test hot paths."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "tests/load/QUERY_PLANS.md"
README = ROOT / "tests/load/README.md"
OUTPUT_DIR = ROOT / "tests/load/output"
SCRIPT = ROOT / "apps/api/scripts/explain_load_hot_paths.py"

_REQUIRED_SNIPPETS: tuple[str, ...] = (
    "EXPLAIN",
    "pg_stat_statements",
    "POST /v1/quotes",
    "orders",
    "k6",
)


def main() -> int:
    failures: list[str] = []

    if not DOC.is_file():
        failures.append("§5.4.4 missing tests/load/QUERY_PLANS.md")
    else:
        text = DOC.read_text(encoding="utf-8", errors="ignore")
        for snippet in _REQUIRED_SNIPPETS:
            if snippet not in text:
                failures.append(f"§5.4.4 QUERY_PLANS.md missing: {snippet}")

    if README.is_file():
        readme = README.read_text(encoding="utf-8", errors="ignore")
        if "QUERY_PLANS.md" not in readme:
            failures.append("§5.4.4 tests/load/README.md must link QUERY_PLANS.md")
    else:
        failures.append("§5.4.4 missing tests/load/README.md")

    if not OUTPUT_DIR.is_dir():
        failures.append("§5.4.4 missing tests/load/output/ directory")

    if not SCRIPT.is_file():
        failures.append("§5.4.4 missing apps/api/scripts/explain_load_hot_paths.py")

    if failures:
        print("Load query plan guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Load query plan guard passed (§5.4.4 — EXPLAIN workflow for quote/order paths).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
