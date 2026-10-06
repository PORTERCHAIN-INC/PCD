"""Phase 2 feature flags — default off until Phase 1 loop is boring (masterrule §21.4)."""

from __future__ import annotations

from dataclasses import dataclass

PHASE2_FLAG_ENV_KEYS: tuple[str, ...] = (
    "PORTERCHAIN_PHASE2_CRM",
    "PORTERCHAIN_PHASE2_ROUTE_CENTER",
    "PORTERCHAIN_PHASE2_AI_DISPATCH",
    "PORTERCHAIN_PHASE2_ANALYTICS",
    "PORTERCHAIN_PHASE2_INTELLIGENCE",
)


def _env_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Phase2Flags:
    crm: bool = False
    # RETIRED — Route Center / VROOM removed; always False in as_dict.
    route_center: bool = False
    ai_dispatch: bool = False
    analytics: bool = False
    intelligence: bool = False

    def as_dict(self) -> dict[str, bool]:
        return {
            "crm": self.crm,
            "route_center": False,  # retired — ignore env
            "ai_dispatch": self.ai_dispatch,
            "analytics": self.analytics,
            "intelligence": self.intelligence,
        }

    def any_enabled(self) -> bool:
        return any(self.as_dict().values())


def phase2_flags_from_mapping(values: dict[str, object]) -> Phase2Flags:
    return Phase2Flags(
        crm=_env_bool(values.get("phase2_crm") or values.get("PORTERCHAIN_PHASE2_CRM")),
        route_center=_env_bool(
            values.get("phase2_route_center") or values.get("PORTERCHAIN_PHASE2_ROUTE_CENTER")
        ),
        ai_dispatch=_env_bool(
            values.get("phase2_ai_dispatch") or values.get("PORTERCHAIN_PHASE2_AI_DISPATCH")
        ),
        analytics=_env_bool(
            values.get("phase2_analytics") or values.get("PORTERCHAIN_PHASE2_ANALYTICS")
        ),
        intelligence=_env_bool(
            values.get("phase2_intelligence") or values.get("PORTERCHAIN_PHASE2_INTELLIGENCE")
        ),
    )
