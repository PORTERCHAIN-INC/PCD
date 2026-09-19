"""Lead ingest settings + Doppler write-through."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.lead_ingest_settings import (
    lead_ingest_settings_status,
    update_lead_ingest_settings,
)
from porterchain_api.config import Settings
from porterchain_api.integrations.doppler_secrets import set_secrets


def test_status_never_returns_secret_values() -> None:
    settings = Settings(
        public_ingest_api_key="super-secret-key",
        google_lead_webhook_secret="g-secret",
        referral_credit_cents=25000,
        lead_territory_map_json='{"DEFAULT":"u1"}',
        meta_pixel_id="pixel123",
    )
    with patch(
        "porterchain_api.admin_engine.lead_ingest_settings.list_secret_names",
        return_value=set(),
    ):
        out = lead_ingest_settings_status(settings)
    assert "super-secret-key" not in str(out)
    assert "g-secret" not in str(out)
    assert out["secrets"]["PUBLIC_INGEST_API_KEY"]["configured"] is True
    assert out["visible"]["META_PIXEL_ID"] == "pixel123"
    assert out["visible"]["REFERRAL_CREDIT_CENTS"] == 25000


def test_set_secrets_posts_to_doppler() -> None:
    settings = Settings(doppler_token="dp.st.test", doppler_project="pcd", doppler_config="prd")
    resp = MagicMock()
    resp.is_success = True
    with patch("porterchain_api.integrations.doppler_secrets.httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = resp
        out = set_secrets(settings, {"GOOGLE_LEAD_WEBHOOK_SECRET": "abc"})
    assert out["ok"] is True
    assert out["written"] == ["GOOGLE_LEAD_WEBHOOK_SECRET"]
    args, kwargs = client.post.call_args
    assert "configs/config/secrets" in args[0]
    assert kwargs["json"]["secrets"]["GOOGLE_LEAD_WEBHOOK_SECRET"] == "abc"


def test_update_requires_doppler_token() -> None:
    settings = Settings(doppler_token="")
    ctx = SimpleNamespace(user=SimpleNamespace(id="u1"))
    db = MagicMock()
    with pytest.raises(ValueError, match="doppler_token_missing"):
        update_lead_ingest_settings(
            db,
            ctx,  # type: ignore[arg-type]
            {"secrets": {"META_APP_SECRET": "x"}},
            settings=settings,
        )


def test_update_writes_and_audits() -> None:
    settings = Settings(doppler_token="dp.st.test")
    ctx = SimpleNamespace(user=SimpleNamespace(id="u1"))
    db = MagicMock()
    with (
        patch(
            "porterchain_api.admin_engine.lead_ingest_settings.set_secrets",
            return_value={"ok": True, "written": ["META_APP_SECRET"]},
        ) as set_sec,
        patch("porterchain_api.admin_engine.lead_ingest_settings.log_admin_audit") as audit,
        patch(
            "porterchain_api.admin_engine.lead_ingest_settings.list_secret_names",
            return_value={"META_APP_SECRET"},
        ),
    ):
        out = update_lead_ingest_settings(
            db,
            ctx,  # type: ignore[arg-type]
            {
                "secrets": {"META_APP_SECRET": "from-admin"},
                "visible": {"REFERRAL_CREDIT_CENTS": 30000},
            },
            settings=settings,
        )
    set_sec.assert_called_once()
    written = set_sec.call_args[0][1]
    assert written["META_APP_SECRET"] == "from-admin"
    assert written["REFERRAL_CREDIT_CENTS"] == "30000"
    audit.assert_called_once()
    assert out["save"]["ok"] is True
