"""Keycloak SMTP → ZeptoMail HTTPS relay.

DigitalOcean Droplets block outbound SMTP (25/465/587). Keycloak only speaks SMTP,
so this tiny listener accepts mail on the Docker network (localhost-equivalent) and
forwards each message to ZeptoMail's HTTPS Send Mail API on port 443 — the same path
the PorterChain API already uses via MAIL_TRANSPORT=https.

Env (never log values):
  ZEPTOMAIL_API_URL   default https://api.zeptomail.ca/v1.1/email
  MAIL_PASSWORD       Zoho-enczapikey … token (or bare token)
  MAIL_FROM_ADDRESS   fallback From if the SMTP envelope lacks one
  MAIL_FROM_NAME      default Porterchain
  RELAY_BIND          default 0.0.0.0
  RELAY_PORT          default 1025
"""
from __future__ import annotations

import email
import email.policy
import logging
import os
import sys
from email.message import Message
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from aiosmtpd.controller import Controller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s kc-zeptomail-relay %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("kc-zeptomail-relay")


def _api_url() -> str:
    url = (os.environ.get("ZEPTOMAIL_API_URL") or "https://api.zeptomail.ca/v1.1/email").strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("ZEPTOMAIL_API_URL must be https://…")
    return url


def _auth_header() -> str:
    token = (os.environ.get("MAIL_PASSWORD") or os.environ.get("ZEPTOMAIL_TOKEN") or "").strip()
    if not token:
        raise SystemExit("MAIL_PASSWORD (ZeptoMail send-mail token) is required")
    return token if token.startswith("Zoho-enczapikey") else f"Zoho-enczapikey {token}"


def _fallback_from() -> tuple[str, str]:
    addr = (os.environ.get("MAIL_FROM_ADDRESS") or "no-reply@porterchain.com").strip()
    name = (os.environ.get("MAIL_FROM_NAME") or "Porterchain").strip()
    return addr, name


def _addr(value: str | None) -> str:
    if not value:
        return ""
    _, addr = parseaddr(value)
    return (addr or value).strip()


def _parts(msg: Message) -> tuple[str, str]:
    text, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and not text:
                try:
                    text = part.get_content()
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    text = payload.decode(part.get_content_charset() or "utf-8", "replace")
            elif ctype == "text/html" and not html:
                try:
                    html = part.get_content()
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    html = payload.decode(part.get_content_charset() or "utf-8", "replace")
    else:
        ctype = msg.get_content_type()
        try:
            body = msg.get_content()
        except Exception:
            payload = msg.get_payload(decode=True) or b""
            body = payload.decode(msg.get_content_charset() or "utf-8", "replace")
        if ctype == "text/html":
            html = body if isinstance(body, str) else str(body)
        else:
            text = body if isinstance(body, str) else str(body)
    return text or "", html or ""


def send_zeptomail(*, to: str, subject: str, text: str, html: str, from_addr: str, from_name: str) -> None:
    import json

    from_obj: dict[str, str] = {"address": from_addr}
    if from_name:
        from_obj["name"] = from_name
    payload = {
        "from": from_obj,
        "to": [{"email_address": {"address": to}}],
        "subject": subject or "(no subject)",
        "htmlbody": html or text or "",
        "textbody": text or "",
    }
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        _api_url(),
        data=data,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": _auth_header(),
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            status = getattr(resp, "status", 200)
            body = resp.read()[:200]
    except HTTPError as exc:
        detail = exc.read()[:400].decode("utf-8", "replace")
        raise RuntimeError(f"zeptomail_http_{exc.code}:{detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"zeptomail_http_error:{exc}") from exc
    if status not in (200, 201):
        raise RuntimeError(f"zeptomail_http_{status}:{body!r}")
    log.info("forwarded to=%s subject_len=%s status=%s", to, len(subject or ""), status)


class Handler:
    async def handle_DATA(self, server, session, envelope):  # noqa: N802
        try:
            msg = email.message_from_bytes(envelope.content, policy=email.policy.default)
            subject = str(msg.get("subject") or "")
            text, html = _parts(msg)
            from_header = _addr(msg.get("from"))
            fb_addr, fb_name = _fallback_from()
            from_addr = from_header or fb_addr
            from_name = fb_name
            # Prefer envelope recipients (Keycloak sets RCPT TO)
            recipients = [_addr(r) for r in (envelope.rcpt_tos or []) if _addr(r)]
            if not recipients:
                to_hdr = msg.get_all("to", [])
                recipients = [_addr(x) for x in to_hdr if _addr(x)]
            if not recipients:
                log.error("reject: no recipients")
                return "550 no recipients"
            for to in recipients:
                send_zeptomail(
                    to=to,
                    subject=subject,
                    text=text,
                    html=html,
                    from_addr=from_addr,
                    from_name=from_name,
                )
            return "250 OK"
        except Exception as exc:
            log.exception("forward_failed: %s", type(exc).__name__)
            # 4xx so Keycloak can retry; avoid leaking details to SMTP client
            return "451 temporary failure forwarding mail"


def main() -> None:
    # Fail fast if misconfigured (token presence + https URL) without printing secrets
    _ = _auth_header()
    _ = _api_url()
    bind = (os.environ.get("RELAY_BIND") or "0.0.0.0").strip()
    port = int((os.environ.get("RELAY_PORT") or "1025").strip())
    controller = Controller(Handler(), hostname=bind, port=port)
    controller.start()
    log.info("listening on %s:%s → ZeptoMail HTTPS", bind, port)
    try:
        import asyncio

        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()


if __name__ == "__main__":
    main()
