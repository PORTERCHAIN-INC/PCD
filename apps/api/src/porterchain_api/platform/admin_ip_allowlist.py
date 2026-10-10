"""Optional admin IP allowlist (Settings > Admin access). Off by default.

Enforced on every /v1/admin request before the session is resolved. Safety:
an enabled list with no entries is treated as off, and ADMIN_IP_ALLOWLIST_BREAK_GLASS=true
in the server env disables it (recovery if you lock yourselves out).
"""

from __future__ import annotations

import ipaddress
import os
import time
from typing import Any

from fastapi import HTTPException

_CACHE: dict[str, Any] = {"at": 0.0, "value": None}
_TTL = 30.0


def default_admin_access() -> dict[str, Any]:
    return {"ip_allowlist_enabled": False, "ip_allowlist": []}


def normalize_admin_access(raw: Any) -> dict[str, Any]:
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("admin_access must be an object")
    src = raw or {}
    entries = src.get("ip_allowlist") or []
    if isinstance(entries, str):
        entries = [e for e in entries.replace("\n", ",").split(",")]
    nets: list[str] = []
    for e in entries:
        e = str(e).strip()
        if not e:
            continue
        try:
            nets.append(str(ipaddress.ip_network(e, strict=False)))
        except ValueError as exc:
            raise ValueError(f"invalid IP or CIDR: {e}") from exc
    _CACHE["at"] = 0.0
    return {"ip_allowlist_enabled": bool(src.get("ip_allowlist_enabled", False)),
            "ip_allowlist": sorted(set(nets))[:100]}


def _policy(db: Any) -> dict[str, Any]:
    now = time.monotonic()
    if _CACHE["value"] is not None and now - _CACHE["at"] < _TTL:
        return _CACHE["value"]
    from porterchain_api.admin_models import SystemConfig

    row = db.get(SystemConfig, "admin_access")
    value = normalize_admin_access(row.value if row is not None and isinstance(row.value, dict) else None)
    _CACHE.update(at=now, value=value)
    return value


def ip_allowed(ip: str, policy: dict[str, Any]) -> bool:
    if os.environ.get("ADMIN_IP_ALLOWLIST_BREAK_GLASS", "").lower() == "true":
        return True
    if not policy.get("ip_allowlist_enabled") or not policy.get("ip_allowlist"):
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in ipaddress.ip_network(n) for n in policy["ip_allowlist"])


def enforce(request: Any, db: Any) -> None:
    from porterchain_api.platform.client_ip import client_ip

    try:
        policy = _policy(db)
    except Exception:  # noqa: BLE001 - never lock admins out on a settings read error
        return
    if not ip_allowed(client_ip(request), policy):
        raise HTTPException(status_code=403, detail="admin_ip_not_allowed")
