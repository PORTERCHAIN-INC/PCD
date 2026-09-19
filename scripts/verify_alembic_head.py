#!/usr/bin/env python3
"""Dev-layer Alembic head guard — §0.1.13 local."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "apps/api/alembic/versions"
EXPECTED_HEAD = "c1d2e3f4a5b6"

# Migrations declare identifiers both bare (`revision = "x"`) and annotated
# (`revision: str = "x"`). Matching only the bare form silently drops the
# annotated files' edges and splits the graph into phantom heads.
_REVISION_RE = re.compile(r'^revision(?:\s*:[^=]+)?\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_DOWN_REVISION_RE = re.compile(r'^down_revision(?:\s*:[^=]+)?\s*=\s*(.+)$', re.MULTILINE)


def find_head_revision() -> str | None:
    revisions: dict[str, str | None] = {}
    for path in VERSIONS.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        rev_m = _REVISION_RE.search(text)
        down_m = _DOWN_REVISION_RE.search(text)
        if not rev_m:
            continue
        rev = rev_m.group(1)
        down_raw = down_m.group(1).strip() if down_m else "None"
        if down_raw in ("None", "null"):
            down: str | None = None
        else:
            down = down_raw.strip("\"'")
        revisions[rev] = down

    if not revisions:
        return None

    referenced = {d for d in revisions.values() if d}
    heads = [r for r in revisions if r not in referenced]
    if len(heads) != 1:
        return None
    return heads[0]


def main() -> int:
    failures: list[str] = []

    head = find_head_revision()
    if head is None:
        failures.append("could not determine single Alembic head from versions/")
    elif head != EXPECTED_HEAD:
        failures.append(f"Alembic head is {head!r}, expected {EXPECTED_HEAD!r}")

    if not any(VERSIONS.glob(f"{EXPECTED_HEAD}_*.py")):
        failures.append(f"missing migration file for head {EXPECTED_HEAD}")

    print(f"Alembic head guard (§0.1.13 dev · head={EXPECTED_HEAD})")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — migration chain head matches dev expectation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
