"""`system_config.marketing_site` — website marketing switches (JSON, no migration).

Customer-facing experiments are OFF by default: the hero A/B test only runs once
ops enable it. The calculator itself is on (it only shows a price).
"""

from __future__ import annotations

import copy
from typing import Any

from sqlalchemy.orm import Session

CONFIG_KEY = "marketing_site"

_DEFAULT: dict[str, Any] = {
    "schema": 1,
    "hero_ab": {
        "enabled": False,
        "experiment": "hero_copy_v1",
        # Share of visitors (0-100) who see variant "b".
        "split_percent": 50,
    },
    "calculator": {
        "enabled": True,
        "estimates_per_minute": 12,
        "leads_per_minute": 3,
        # Seconds a human needs at least to fill the lead form.
        "min_fill_seconds": 2,
        # Calculator leads never trigger the automatic welcome email / nurture.
        "auto_outreach": False,
    },
}


def default_marketing_site() -> dict[str, Any]:
    return copy.deepcopy(_DEFAULT)


def _int(value: Any, *, lo: int, hi: int, path: str) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"marketing_site_invalid:{path}") from exc
    if n < lo or n > hi:
        raise ValueError(f"marketing_site_invalid:{path}")
    return n


def normalize_marketing_site(raw: Any) -> dict[str, Any]:
    """Validate and fill defaults. Raises ValueError('marketing_site_invalid:<path>')."""
    out = default_marketing_site()
    if raw is None:
        return out
    if not isinstance(raw, dict):
        raise ValueError("marketing_site_invalid:root")
    hero = raw.get("hero_ab")
    if hero is not None:
        if not isinstance(hero, dict):
            raise ValueError("marketing_site_invalid:hero_ab")
        if "enabled" in hero:
            out["hero_ab"]["enabled"] = bool(hero["enabled"])
        if hero.get("experiment"):
            exp = "".join(ch for ch in str(hero["experiment"]).lower() if ch.isalnum() or ch == "_")
            if not exp:
                raise ValueError("marketing_site_invalid:hero_ab.experiment")
            out["hero_ab"]["experiment"] = exp[:40]
        if "split_percent" in hero:
            out["hero_ab"]["split_percent"] = _int(
                hero["split_percent"], lo=0, hi=100, path="hero_ab.split_percent"
            )
    calc = raw.get("calculator")
    if calc is not None:
        if not isinstance(calc, dict):
            raise ValueError("marketing_site_invalid:calculator")
        if "enabled" in calc:
            out["calculator"]["enabled"] = bool(calc["enabled"])
        if "auto_outreach" in calc:
            out["calculator"]["auto_outreach"] = bool(calc["auto_outreach"])
        for key, hi in (("estimates_per_minute", 600), ("leads_per_minute", 60)):
            if key in calc:
                out["calculator"][key] = _int(calc[key], lo=1, hi=hi, path=f"calculator.{key}")
        if "min_fill_seconds" in calc:
            out["calculator"]["min_fill_seconds"] = _int(
                calc["min_fill_seconds"], lo=0, hi=60, path="calculator.min_fill_seconds"
            )
    return out


def get_marketing_site(db: Session) -> dict[str, Any]:
    from porterchain_api.admin_engine.settings_service import AdminSettingsService

    try:
        raw = AdminSettingsService().get_config_value(db, CONFIG_KEY)
    except Exception:
        raw = None
    try:
        return normalize_marketing_site(raw if isinstance(raw, dict) else None)
    except ValueError:
        return default_marketing_site()


def public_marketing_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Only what the website needs — never limits or internal switches."""
    hero = cfg.get("hero_ab") or {}
    calc = cfg.get("calculator") or {}
    return {
        "hero_ab": {
            "enabled": bool(hero.get("enabled")),
            "experiment": hero.get("experiment") or "hero_copy_v1",
            "split_percent": int(hero.get("split_percent") or 0),
        },
        "calculator": {"enabled": bool(calc.get("enabled", True))},
    }
