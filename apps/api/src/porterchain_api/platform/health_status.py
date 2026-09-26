"""Normalize probe/readiness tokens → Jeff Dean health triad.

Health-dashboard component statuses must stay in ``healthy | warning | critical``
so ``_health_to_validation`` / ``phase_1_system_layer`` keep working.
"""

from __future__ import annotations

from typing import Literal

HealthStatus = Literal["healthy", "warning", "critical"]

_HEALTHY_EXACT = frozenset(
    {
        "healthy",
        "ok",
        "pass",
        "configured",
        "bridge_enabled",
        "enabled",
        "ready",
        "local",
        "operational",
        "legacy_ok",
    }
)

_WARNING_EXACT = frozenset(
    {
        "warning",
        "degraded",
        "mock",
        "mock_or_unconfigured",
        "bypass",
        "dev_bypass",
        "disabled",
        "bridge_disabled",
        "unconfigured",
        "not_configured",
        "unavailable",
        "log_only",
        "dry_run",
        "push_disabled",
        "sdk_missing",
        "no_heartbeat",
        "skipped",
        "shadow",
        "unknown",
    }
)

_WARNING_SUBSTRINGS = (
    "warning",
    "degraded",
    "mock",
    "bypass",
    "disabled",
    "unconfigured",
    "unavailable",
    "below_slo",
    "missing_secret",
    "dry_run",
    "legacy",
)

_CRITICAL_SUBSTRINGS = (
    "error",
    "critical",
    "unreachable",
    "unbonded",
    "fail",
)


def normalize_check_status(raw: str | None) -> HealthStatus:
    """Map a readiness/integration probe token to the Jeff Dean triad."""
    if raw is None:
        return "warning"
    s = str(raw).strip().lower()
    if not s:
        return "warning"
    if s in _HEALTHY_EXACT:
        return "healthy"
    if s in _WARNING_EXACT:
        return "warning"
    if any(x in s for x in _CRITICAL_SUBSTRINGS):
        return "critical"
    if any(x in s for x in _WARNING_SUBSTRINGS):
        return "warning"
    # Ambiguous leftovers → warning (not FAIL via Jeff Dean else-branch).
    return "warning"


def component_status_value(value: object) -> HealthStatus | None:
    """Extract a triad status from a string or ``{status: ...}`` component."""
    if value is None:
        return None
    if isinstance(value, dict) and "status" in value:
        return normalize_check_status(str(value.get("status")))
    if isinstance(value, str):
        return normalize_check_status(value)
    return None
