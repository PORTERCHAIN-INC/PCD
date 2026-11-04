"""Quote validity is 72 h (doc 72 §§, 98 U-QT-1; was 30 min)."""

from __future__ import annotations

from porterchain_api.config import Settings
from porterchain_api.admin_engine import settings_service


def test_default_quote_ttl_is_72_hours() -> None:
    assert Settings(_env_file=None).quote_ttl_minutes == 72 * 60


def test_env_can_override_quote_ttl(monkeypatch) -> None:
    monkeypatch.setenv("QUOTE_TTL_MINUTES", "30")
    assert Settings(_env_file=None).quote_ttl_minutes == 30


def test_admin_settings_default_matches() -> None:
    src = open(settings_service.__file__).read()
    assert '"quote_ttl_minutes": 72 * 60' in src
