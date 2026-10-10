"""ZeptoMail Send Mail HTTP API — used when DigitalOcean blocks outbound SMTP."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def send_zeptomail(
    *,
    recipient: str,
    subject: str,
    text_body: str,
    html_body: str,
    from_addr: str,
    from_name: str,
    settings: Any,
    headers: dict[str, str] | None = None,
    reference: str | None = None,
    reply_to: str | None = None,
) -> None:
    """``reference`` (our notification id) comes back as client_reference on webhooks."""
    import httpx

    token = (settings.smtp_password or "").strip()
    if not token:
        raise ValueError("zeptomail_token_missing")
    auth = token if token.startswith("Zoho-enczapikey") else f"Zoho-enczapikey {token}"
    api_url = (getattr(settings, "zeptomail_api_url", None) or "https://api.zeptomail.ca/v1.1/email").strip()
    parsed = urlparse(api_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("zeptomail_url_must_be_https")
    from_obj: dict[str, str] = {"address": from_addr}
    if from_name:
        from_obj["name"] = from_name
    payload: dict[str, Any] = {
        "from": from_obj,
        "to": [{"email_address": {"address": recipient}}],
        "subject": subject,
        "htmlbody": html_body or text_body,
        "textbody": text_body or "",
    }
    if headers:
        payload["mime_headers"] = dict(headers)
    if reference:
        payload["client_reference"] = str(reference)[:128]
    if reply_to and "@" in reply_to:
        payload["reply_to"] = [{"address": reply_to.strip()}]
    try:
        resp = httpx.post(
            api_url,
            json=payload,
            headers={"accept": "application/json", "authorization": auth},
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        raise ValueError(f"zeptomail_http_error:{exc}") from exc
    if resp.status_code not in (200, 201):
        raise ValueError(f"zeptomail_http_{resp.status_code}:{resp.text[:400]}")
    logger.info("email (zeptomail https): to=%s status=%s", recipient, resp.status_code)
