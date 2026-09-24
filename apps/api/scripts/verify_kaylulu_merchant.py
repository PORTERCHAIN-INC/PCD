#!/usr/bin/env python3
"""
Read-only check: Kaylulu merchant schedule + A3 size_tiers + FSA tier sample.

Usage (API venv + DATABASE_URL pointing at local / staging / prod):

  cd apps/api && PYTHONPATH=src python scripts/verify_kaylulu_merchant.py

Optional: MERCHANT_ID=… (defaults to prod Kaylulu id).
Does not write. Exit 0 when model=fsa, schedule present, and size_tiers ≥ 3.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import create_engine, text  # noqa: E402

from porterchain_api.merchant_engine.kaylulu_template import (  # noqa: E402
    DEFAULT_KAYLULU_MERCHANT_ID,
    KAYLULU_SCHEDULE,
)


def _url() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("PORTERCHAIN_DATABASE_URL")
    if not url:
        url = "postgresql+psycopg://porterchain:porterchain@127.0.0.1:5432/porterchain"
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def main() -> int:
    mid = os.environ.get("MERCHANT_ID") or DEFAULT_KAYLULU_MERCHANT_ID
    eng = create_engine(_url(), connect_args={"connect_timeout": 5})
    with eng.connect() as c:
        row = c.execute(
            text(
                "select id, company_name, pricing_model, pricing_config "
                "from merchants where id=:id"
            ),
            {"id": mid},
        ).mappings().first()
        if not row:
            row = c.execute(
                text(
                    "select id, company_name, pricing_model, pricing_config "
                    "from merchants where lower(company_name) like '%kaylulu%' "
                    "order by created_at desc nulls last limit 1"
                )
            ).mappings().first()
        if not row:
            print("FAIL: Kaylulu merchant not found (set MERCHANT_ID or run against prod/staging)")
            print(f"looked_for_id={mid}")
            return 2

        cfg = row["pricing_config"]
        if isinstance(cfg, str):
            cfg = json.loads(cfg)
        cfg = cfg or {}
        schedule = cfg.get("schedule") or {}
        tiers = cfg.get("size_tiers") or []
        fsa = c.execute(
            text(
                "select flat_cents, count(*) as n, "
                "count(*) filter (where (config->>'tier') is not null) as tagged "
                "from pricing_fsa_rates where merchant_id=:id and is_active is true "
                "group by flat_cents order by flat_cents"
            ),
            {"id": row["id"]},
        ).mappings().all()

        print(
            json.dumps(
                {
                    "merchant_id": row["id"],
                    "company_name": row["company_name"],
                    "pricing_model": row["pricing_model"],
                    "schedule_keys": sorted(schedule.keys()),
                    "fsa_miss": schedule.get("fsa_miss"),
                    "origin_pickup_cents": schedule.get("origin_pickup_cents"),
                    "route_minimums_cents": schedule.get("route_minimums_cents"),
                    "size_match": schedule.get("size_match"),
                    "size_tier_labels": [t.get("label") for t in tiers if isinstance(t, dict)],
                    "size_tier_count": len(tiers),
                    "fsa_by_flat_cents": {str(r["flat_cents"]): {"n": r["n"], "tagged": r["tagged"]} for r in fsa},
                    "expected_schedule_fsa_miss": KAYLULU_SCHEDULE["fsa_miss"],
                },
                indent=2,
                default=str,
            )
        )

        ok = (
            row["pricing_model"] == "fsa"
            and schedule.get("fsa_miss") == "refuse"
            and len(tiers) >= 3
            and int(schedule.get("origin_pickup_cents") or 0) == 4000
        )
        if ok:
            print("OK: Kaylulu schedule + A3 size_tiers look applied")
            return 0
        print("WARN: merchant found but schedule/A3 incomplete — run apply_kaylulu_schedule.py")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
