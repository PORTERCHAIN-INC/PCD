"""Lead CAPI Meta + LinkedIn emission."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.collaboration_engine.lead_capi import emit_lead_conversion_events
from porterchain_api.config import Settings


def test_linkedin_capi_posts_when_configured() -> None:
    lead = SimpleNamespace(
        id="lead_1",
        email="Ops@Example.COM",
        phone="+14165550100",
        custom_fields={},
    )
    settings = Settings(
        linkedin_capi_token="li-token",
        linkedin_conversion_urn="urn:lla:llaPartnerConversion:99",
        meta_capi_access_token="",
        meta_pixel_id="",
    )
    resp = MagicMock()
    resp.is_success = True
    with patch("porterchain_api.collaboration_engine.lead_capi.httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = resp
        out = emit_lead_conversion_events(MagicMock(), lead, settings=settings)  # type: ignore[arg-type]
    assert out["linkedin"] == "ok"
    assert out["meta"] == "skipped"
    args, kwargs = client.post.call_args
    assert args[0] == "https://api.linkedin.com/rest/conversionEvents"
    assert kwargs["headers"]["Authorization"] == "Bearer li-token"
    assert kwargs["json"]["conversion"] == "urn:lla:llaPartnerConversion:99"
    assert kwargs["json"]["user"]["userIds"][0]["idType"] == "SHA256_EMAIL"


def test_lead_ingest_config_status_booleans() -> None:
    from porterchain_api.collaboration_engine.lead_ops import lead_ingest_config_status
    from porterchain_api.config import Settings

    empty = lead_ingest_config_status(Settings())
    assert empty["meta_webhooks"] is False
    assert empty["linkedin_capi"] is False
    assert empty["referral_credits"] is True  # default 25000

    ready = lead_ingest_config_status(
        Settings(
            public_ingest_api_key="k",
            meta_app_secret="s",
            meta_webhook_verify_token="t",
            google_lead_webhook_secret="g",
            social_lead_webhook_secret="soc",
            meta_capi_access_token="m",
            meta_pixel_id="p",
            linkedin_capi_token="li",
            linkedin_conversion_urn="urn:lla:llaPartnerConversion:1",
            lead_territory_map_json='{"DEFAULT":"u1"}',
            lead_round_robin_json='["u1","u2"]',
            lead_sla_minutes_json='{"default":60}',
        )
    )
    assert all(ready[k] is True for k in ready)
