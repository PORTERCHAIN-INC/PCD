"""Lead ingest settings: status hides values; saves validate and point at SOPS."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.lead_ingest_settings import (
    SECRETS_FILE,
    lead_ingest_settings_status,
    update_lead_ingest_settings,
)
from porterchain_api.config import Settings


def test_status_never_returns_secret_values() -> None:
    settings = Settings(
        public_ingest_api_key="super-secret-key",
        google_lead_webhook_secret="g-secret",
        referral_credit_cents=25000,
        lead_territory_map_json='{"DEFAULT":"u1"}',
        meta_pixel_id="pixel123",
    )
    out = lead_ingest_settings_status(settings)
    assert "super-secret-key" not in str(out)
    assert "g-secret" not in str(out)
    assert out["secrets"]["PUBLIC_INGEST_API_KEY"]["configured"] is True
    assert out["secrets_store"] == {"kind": "sops", "file": SECRETS_FILE, "writable": False}
    assert out["visible"]["META_PIXEL_ID"] == "pixel123"
    assert out["visible"]["REFERRAL_CREDIT_CENTS"] == 25000


def test_generate_is_rejected() -> None:
    ctx = SimpleNamespace(user=SimpleNamespace(id="u1"))
    with pytest.raises(ValueError, match="generate_unsupported_use_sops"):
        update_lead_ingest_settings(
            MagicMock(), ctx, {"generate": ["PUBLIC_INGEST_API_KEY"]}, settings=Settings()  # type: ignore[arg-type]
        )


def test_invalid_json_is_rejected() -> None:
    ctx = SimpleNamespace(user=SimpleNamespace(id="u1"))
    with pytest.raises(ValueError, match="lead_territory_map_json_invalid"):
        update_lead_ingest_settings(
            MagicMock(), ctx, {"visible": {"LEAD_TERRITORY_MAP_JSON": "{"}}, settings=Settings()  # type: ignore[arg-type]
        )


def test_update_lists_keys_audits_and_never_echoes_values() -> None:
    ctx = SimpleNamespace(user=SimpleNamespace(id="u1"))
    with patch("porterchain_api.admin_engine.lead_ingest_settings.log_admin_audit") as audit:
        out = update_lead_ingest_settings(
            MagicMock(),
            ctx,  # type: ignore[arg-type]
            {
                "secrets": {"META_APP_SECRET": "from-admin"},
                "visible": {"REFERRAL_CREDIT_CENTS": 30000},
            },
            settings=Settings(),
        )
    assert out["save"]["applied"] is False
    assert out["save"]["keys"] == ["META_APP_SECRET", "REFERRAL_CREDIT_CENTS"]
    assert SECRETS_FILE in out["save"]["how"]
    assert "from-admin" not in str(out)
    audit.assert_called_once()
    assert audit.call_args.kwargs["payload"] == {"keys": ["META_APP_SECRET", "REFERRAL_CREDIT_CENTS"]}
