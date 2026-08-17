"""ZeptoMail HTTPS transport (DigitalOcean blocks outbound SMTP)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.notification_engine.delivery_service import DeliveryService
from porterchain_shared.config.settings import PlatformSettings


def test_resolve_mail_transport_auto_zeptomail_prod() -> None:
    s = PlatformSettings.model_construct(
        app_env="production",
        smtp_host="smtp.zeptomail.ca",
        mail_transport="auto",
    )
    assert s.resolve_mail_transport() == "https"


def test_resolve_mail_transport_local_uses_smtp() -> None:
    s = PlatformSettings.model_construct(
        app_env="local",
        smtp_host="smtp.zeptomail.ca",
        mail_transport="auto",
    )
    assert s.resolve_mail_transport() == "smtp"


def test_resolve_mail_transport_explicit_https() -> None:
    s = PlatformSettings.model_construct(
        app_env="local",
        smtp_host="localhost",
        mail_transport="https",
    )
    assert s.resolve_mail_transport() == "https"


def test_send_email_uses_zeptomail_https() -> None:
    svc = DeliveryService()
    settings = SimpleNamespace(
        smtp_host="smtp.zeptomail.ca",
        smtp_password="Zoho-enczapikey test-token",
        smtp_from="noreply@porterchain.com",
        smtp_from_name="Porterchain",
        smtp_from_sales="",
        smtp_from_personal="",
        mail_transport="https",
        zeptomail_api_url="https://api.zeptomail.ca/v1.1/email",
        app_env="production",
        resolve_mail_transport=lambda: "https",
        smtp_from_for=lambda alias=None: "noreply@porterchain.com",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.text = '{"message":"OK"}'

    with (
        patch(
            "porterchain_api.notification_engine.delivery_service.get_platform_settings",
            return_value=settings,
        ),
        patch(
            "porterchain_api.notification_engine.delivery_service.render_email",
            return_value=("Subj", "text", "<p>html</p>"),
        ),
        patch("httpx.post", return_value=mock_resp) as post,
    ):
        svc._send_email("ravi@porterchain.com", "staff_activate", {})

    assert post.call_args.args[0] == "https://api.zeptomail.ca/v1.1/email"
    assert post.call_args.kwargs["headers"]["authorization"] == "Zoho-enczapikey test-token"


def test_send_email_https_http_error() -> None:
    svc = DeliveryService()
    settings = SimpleNamespace(
        smtp_host="smtp.zeptomail.ca",
        smtp_password="token",
        smtp_from="noreply@porterchain.com",
        smtp_from_name="Porterchain",
        mail_transport="https",
        zeptomail_api_url="https://api.zeptomail.ca/v1.1/email",
        resolve_mail_transport=lambda: "https",
        smtp_from_for=lambda alias=None: "noreply@porterchain.com",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"error":"bad"}'
    with (
        patch(
            "porterchain_api.notification_engine.delivery_service.get_platform_settings",
            return_value=settings,
        ),
        patch(
            "porterchain_api.notification_engine.delivery_service.render_email",
            return_value=("Subj", "text", "<p>html</p>"),
        ),
        patch("httpx.post", return_value=mock_resp),
        pytest.raises(ValueError, match="zeptomail_http_401"),
    ):
        svc._send_email("ravi@porterchain.com", "staff_activate", {})


def test_send_email_https_rejects_non_https_url() -> None:
    svc = DeliveryService()
    settings = SimpleNamespace(
        smtp_host="smtp.zeptomail.ca",
        smtp_password="token",
        smtp_from="noreply@porterchain.com",
        smtp_from_name="Porterchain",
        mail_transport="https",
        zeptomail_api_url="file:///etc/passwd",
        resolve_mail_transport=lambda: "https",
        smtp_from_for=lambda alias=None: "noreply@porterchain.com",
    )
    with (
        patch(
            "porterchain_api.notification_engine.delivery_service.get_platform_settings",
            return_value=settings,
        ),
        patch(
            "porterchain_api.notification_engine.delivery_service.render_email",
            return_value=("Subj", "text", "<p>html</p>"),
        ),
        pytest.raises(ValueError, match="zeptomail_url_must_be_https"),
    ):
        svc._send_email("ravi@porterchain.com", "staff_activate", {})
