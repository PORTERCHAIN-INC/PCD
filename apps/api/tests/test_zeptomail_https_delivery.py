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
    mock_resp.status = 201
    mock_resp.read.return_value = b'{"message":"OK"}'
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with (
        patch(
            "porterchain_api.notification_engine.delivery_service.get_platform_settings",
            return_value=settings,
        ),
        patch(
            "porterchain_api.notification_engine.delivery_service.render_email",
            return_value=("Subj", "text", "<p>html</p>"),
        ),
        patch("urllib.request.urlopen", return_value=mock_resp) as urlopen,
    ):
        svc._send_email("ravi@porterchain.com", "staff_activate", {})

    req = urlopen.call_args[0][0]
    assert req.full_url == "https://api.zeptomail.ca/v1.1/email"
    assert req.get_header("Authorization") == "Zoho-enczapikey test-token"


def test_send_email_https_http_error() -> None:
    import urllib.error

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
    err = urllib.error.HTTPError(
        url="https://api.zeptomail.ca/v1.1/email",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=MagicMock(read=lambda: b'{"error":"bad"}'),
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
        patch("urllib.request.urlopen", side_effect=err),
        pytest.raises(ValueError, match="zeptomail_http_401"),
    ):
        svc._send_email("ravi@porterchain.com", "staff_activate", {})
