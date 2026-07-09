#!/usr/bin/env python3
"""Export §10.1 investor metrics snapshot JSON for monthly tracking (INV-G2)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API_SRC = ROOT / "apps/api/src"
SNAPSHOT_DIR = ROOT / "docs/investor/snapshots"


def main() -> int:
    sys.path.insert(0, str(API_SRC))
    from porterchain_api.db import SessionLocal, init_db
    from porterchain_api.admin_engine.investor_metrics_service import investor_metrics

    init_db()
    db = SessionLocal()
    try:
        payload = investor_metrics(db)
    finally:
        db.close()

    month = datetime.now(UTC).strftime("%Y-%m")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAPSHOT_DIR / f"{month}.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote investor snapshot → {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
