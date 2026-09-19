#!/usr/bin/env python3
"""E.2 — Root-level POINTER doc stubs must be ≤5 (extras under docs/archive/)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_ROOT_POINTERS = 5
POINTER_RE = re.compile(r"^\*\*Type:\*\*\s*POINTER\s*$", re.MULTILINE)
ARCHIVE_INDEX = ROOT / "docs/POINTER_STUB_INDEX.md"
ARCHIVE_DIR = ROOT / "docs/archive/pointer-stubs"


def root_pointer_files() -> list[Path]:
    found: list[Path] = []
    for path in sorted(ROOT.glob("*.md")):
        if path.name == "masterrule.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if POINTER_RE.search(text):
            found.append(path)
    return found


def main() -> int:
    failures: list[str] = []
    pointers = root_pointer_files()

    if len(pointers) > MAX_ROOT_POINTERS:
        failures.append(
            f"{len(pointers)} root POINTER stubs (max {MAX_ROOT_POINTERS}); "
            f"move extras to {ARCHIVE_DIR.relative_to(ROOT)}/"
        )

    if not ARCHIVE_INDEX.is_file():
        failures.append(f"missing index {ARCHIVE_INDEX.relative_to(ROOT)}")
    if not ARCHIVE_DIR.is_dir():
        failures.append(f"missing archive dir {ARCHIVE_DIR.relative_to(ROOT)}")

    print("Doc pointer stub guard (E.2)")
    print(f"  root POINTER stubs: {len(pointers)} / {MAX_ROOT_POINTERS}")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
