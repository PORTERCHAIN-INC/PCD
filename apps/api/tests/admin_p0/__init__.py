"""Admin / Super Admin P0 automation helpers.

SSOT IDs: ``docs/testing/admin_p0_registry.json``
Human suite: ``docs/ADMIN_SUPERADMIN_DEV_TESTCASES.md``
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
REGISTRY_PATH = REPO_ROOT / "docs" / "testing" / "admin_p0_registry.json"


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def cases(*, runner: str | None = None, status: str | None = None, layer: str | None = None) -> list[dict[str, Any]]:
    rows = list(load_registry()["cases"])
    if runner:
        rows = [c for c in rows if c.get("runner") == runner]
    if status:
        rows = [c for c in rows if c.get("status") == status]
    if layer:
        rows = [c for c in rows if c.get("layer") == layer]
    return rows


def case_ids(**kwargs: Any) -> list[str]:
    return [c["id"] for c in cases(**kwargs)]


def case_by_id(case_id: str) -> dict[str, Any]:
    for row in load_registry()["cases"]:
        if row["id"] == case_id:
            return row
    raise KeyError(case_id)
