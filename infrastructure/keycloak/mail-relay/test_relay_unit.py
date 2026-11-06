"""Offline unit checks for the Keycloak→ZeptoMail relay (no network)."""
from __future__ import annotations

import email
import os
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import relay  # noqa: E402


def test_parts_multipart_html_and_text() -> None:
    raw = (
        b"From: no-reply@porterchain.com\r\n"
        b"To: user@example.com\r\n"
        b"Subject: Reset\r\n"
        b"MIME-Version: 1.0\r\n"
        b'Content-Type: multipart/alternative; boundary="b"\r\n\r\n'
        b"--b\r\nContent-Type: text/plain\r\n\r\nplain-code\r\n"
        b"--b\r\nContent-Type: text/html\r\n\r\n<p>html-code</p>\r\n"
        b"--b--\r\n"
    )
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    text, html = relay._parts(msg)
    assert "plain-code" in text
    assert "html-code" in html


def test_send_zeptomail_posts_https(monkeypatch_env: None = None) -> None:
    os.environ["MAIL_PASSWORD"] = "Zoho-enczapikey test-token"
    os.environ["ZEPTOMAIL_API_URL"] = "https://api.zeptomail.ca/v1.1/email"
    captured: dict = {}

    class Resp:
        status = 201

        def read(self):
            return b'{"ok":true}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=30):
        captured["url"] = req.full_url
        captured["auth"] = req.headers.get("Authorization") or req.headers.get("authorization")
        import json

        captured["body"] = json.loads(req.data.decode())
        return Resp()

    with mock.patch.object(relay, "urlopen", fake_urlopen):
        # urlopen is imported inside? it's module-level from urllib.request
        with mock.patch("relay.urlopen", fake_urlopen):
            relay.send_zeptomail(
                to="user@example.com",
                subject="Reset",
                text="hi",
                html="<p>hi</p>",
                from_addr="no-reply@porterchain.com",
                from_name="Porterchain",
            )
    assert captured["url"] == "https://api.zeptomail.ca/v1.1/email"
    assert captured["body"]["to"][0]["email_address"]["address"] == "user@example.com"
    assert captured["auth"].startswith("Zoho-enczapikey")


if __name__ == "__main__":
    test_parts_multipart_html_and_text()
    test_send_zeptomail_posts_https()
    print("ok")
