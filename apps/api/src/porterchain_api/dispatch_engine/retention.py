"""GPS / POD retention policy (``system_config['dispatch_retention']``).

GPS breadcrumbs: kept ``gps_days`` (default 30), then deleted.
POD (photo / signature / ID-check references): kept ``pod_days`` (default 365, the
claims window) after the order closes, then the reference is redacted to its type.
Purges run daily in the worker and can be dry-run from Dispatch → Fleet.
"""

from __future__ import annotations

from typing import Any

STORAGE_KEY = "dispatch_retention"
LIMITS = {"gps_days": (7, 365), "pod_days": (90, 2555)}


def default_retention() -> dict[str, Any]:
    return {"gps_days": 30, "pod_days": 365, "enabled": True}


def normalize_retention(raw: Any) -> dict[str, Any]:
    base = default_retention()
    src = raw if isinstance(raw, dict) else {}
    out: dict[str, Any] = {"enabled": bool(src.get("enabled", base["enabled"]))}
    for key, (lo, hi) in LIMITS.items():
        try:
            val = int(src.get(key, base[key]))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key}_must_be_integer") from exc
        if not lo <= val <= hi:
            raise ValueError(f"{key}_out_of_range_{lo}_{hi}")
        out[key] = val
    return out


def load_retention(db: Any) -> dict[str, Any]:
    from porterchain_api.admin_models import SystemConfig

    row = db.get(SystemConfig, STORAGE_KEY)
    try:
        return normalize_retention(row.value if row is not None else None)
    except ValueError:
        return default_retention()
