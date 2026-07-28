#!/usr/bin/env python3
"""Appendix E.6 + §0.6 — CTO audit P0/P1 closure and doc sprawl guards."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKLIST = ROOT / "docs/SILICON_VALLEY_READINESS_CHECKLIST.md"
CTO_REPORT = ROOT / "CTO_AUDIT_REPORT.md"
SECTION_06_HEADER = "### §0.6 CTO open issues — must close"


def section_06_rows(text: str) -> list[tuple[str, str]]:
    start = text.find(SECTION_06_HEADER)
    if start < 0:
        return []
    chunk = text[start : start + 4000]
    rows: list[tuple[str, str]] = []
    for line in chunk.splitlines():
        m = re.match(r"^\| (0\.6\.\d+) \|.*\| \[(.)\] ", line)
        if m:
            rows.append((m.group(1), m.group(2)))
        if line.startswith("### ") and "§0.6" not in line and rows:
            break
    return rows


def main() -> int:
    failures: list[str] = []

    if not CHECKLIST.is_file():
        failures.append("missing SILICON_VALLEY_READINESS_CHECKLIST.md")
    else:
        checklist = CHECKLIST.read_text(encoding="utf-8")
        rows = section_06_rows(checklist)
        if not rows:
            failures.append("§0.6 section not found in checklist")
        else:
            open_p0_p1 = [
                item_id
                for item_id, status in rows
                if status not in ("x", "~") and item_id in ("0.6.1", "0.6.2", "0.6.3")
            ]
            if open_p0_p1:
                failures.append(f"§0.6 P0–P1 still open: {', '.join(open_p0_p1)}")

    if not CTO_REPORT.is_file():
        failures.append("missing CTO_AUDIT_REPORT.md")
    else:
        cto = CTO_REPORT.read_text(encoding="utf-8")
        if "Remediation log" not in cto:
            failures.append("CTO_AUDIT_REPORT missing Remediation log")
        if "Open issue register" not in cto:
            failures.append("CTO_AUDIT_REPORT missing Open issue register")
        if "s2t3u4v5w6x7" not in cto and "v5w6x7y8z9a0" not in cto and "n2o3p4q5r6s7" in cto:
            failures.append("CTO_AUDIT_REPORT alembic head stale (expected v5w6x7y8z9a0)")

    pointer_script = ROOT / "scripts/verify_doc_pointer_stubs.py"
    if pointer_script.is_file():
        proc = subprocess.run(
            [sys.executable, str(pointer_script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            failures.append("E.2 pointer stub guard failed (run validate:doc-pointers)")
    else:
        failures.append("missing verify_doc_pointer_stubs.py")

    print("Doc governance guard (E.6 · §0.6 · §10.3)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — §0.6 P0–P1 closed, CTO report present, pointer stubs within limit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
