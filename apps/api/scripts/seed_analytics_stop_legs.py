#!/usr/bin/env python3
"""Seed analytics_stop_legs for dev/CI (§4.1.1 path — not prod 10k GPS)."""

from __future__ import annotations

import argparse
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
API_SRC = ROOT / "apps/api/src"
DEFAULT_COUNT = 10_000


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed analytics stop legs for Phase 2 dev")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--order-id", default=None, help="Attach all legs to one order (default: synthetic orders)")
    args = parser.parse_args()

    sys.path.insert(0, str(API_SRC))
    from porterchain_api.db import SessionLocal, init_db
    from porterchain_api.models import AnalyticsStopLeg

    init_db()
    db = SessionLocal()
    inserted = 0
    try:
        base = datetime.now(UTC) - timedelta(days=7)
        order_id = args.order_id or f"seed-{uuid4()}"
        for i in range(args.count):
            oid = order_id if args.order_id else f"seed-{i // 50}"
            db.add(
                AnalyticsStopLeg(
                    order_id=oid,
                    leg_index=i % 50,
                    lat=43.65 + random.uniform(-0.1, 0.1),
                    lng=-79.38 + random.uniform(-0.1, 0.1),
                    recorded_at=base + timedelta(seconds=i * 30),
                )
            )
            inserted += 1
            if inserted % 500 == 0:
                db.flush()
        db.commit()
    finally:
        db.close()

    print(f"Seeded {inserted} analytics_stop_legs rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
