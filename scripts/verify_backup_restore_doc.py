#!/usr/bin/env python3
"""§5.1.7 / §5.1.15 / DD-28 — Postgres backup + quarterly restore drill documented."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/BACKUP_RESTORE.md"
BACKUP = ROOT / "infrastructure/deploy/scripts/backup-porterchain-postgres.sh"
RESTORE = ROOT / "infrastructure/deploy/scripts/restore-porterchain-postgres.sh"
RUNBOOK = ROOT / "RUNBOOK.md"
GITIGNORE = ROOT / ".gitignore"


def main() -> int:
    failures: list[str] = []

    for path in (DOC, BACKUP, RESTORE):
        if not path.is_file():
            failures.append(f"§5.1.7 missing {path.relative_to(ROOT)}")

    if DOC.is_file():
        text = DOC.read_text(encoding="utf-8", errors="ignore")
        for needle in (
            "Quarterly restore drill",
            "CONFIRM_RESTORE",
            "pg_dump",
            "DD-28",
        ):
            if needle not in text:
                failures.append(f"§5.1.7 BACKUP_RESTORE.md missing: {needle}")

    if RUNBOOK.is_file():
        rb = RUNBOOK.read_text(encoding="utf-8", errors="ignore")
        if "BACKUP_RESTORE.md" not in rb:
            failures.append("§5.1.7 RUNBOOK must link BACKUP_RESTORE.md")
        if "Porterchain Postgres" not in rb and "porterchain-postgres" not in rb:
            failures.append("§5.1.7 RUNBOOK missing Porterchain Postgres backup section")
    else:
        failures.append("§5.1.7 missing RUNBOOK.md")

    if GITIGNORE.is_file() and "backups/" not in GITIGNORE.read_text(encoding="utf-8", errors="ignore"):
        failures.append("§5.1.7 .gitignore should ignore backups/")

    for script in (BACKUP, RESTORE):
        if script.is_file():
            result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
            if result.returncode != 0:
                failures.append(f"§5.1.7 bash -n failed for {script.name}: {result.stderr}")

    if failures:
        print("Backup/restore guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Backup/restore guard passed (§5.1.7/5.1.15 — scripts + quarterly drill doc).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
