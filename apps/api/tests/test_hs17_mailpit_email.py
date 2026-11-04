"""HS-17 — booking email lands in Mailpit (not Mailhog); local SMTP → :1025."""

from __future__ import annotations

import inspect
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import uuid4

import pytest

from porterchain_api.notification_engine.delivery_service import DeliveryDeferred, DeliveryService


def test_hs17_local_smtp_hardcodes_mailpit_not_mailhog() -> None:
    src = inspect.getsource(DeliveryService._send_email_smtp)
    assert 'host, port = "localhost", 1025' in src
    assert "mailhog" not in src.lower()
    assert "8025" not in src  # UI port is not SMTP


def test_hs17_repo_has_no_mailhog_compose_dependency() -> None:
    root = Path(__file__).resolve().parents[3]
    import re

    offenders: list[str] = []
    for path in root.rglob("*.yml"):
        if any(p in path.parts for p in ("node_modules", ".venv", "graphify-out", ".git")):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"image:\s*[^\n]*mailhog", text, re.I):
            offenders.append(str(path.relative_to(root)))
        if re.search(r"^\s+mailhog\s*:", text, re.I | re.M):
            offenders.append(str(path.relative_to(root)))
    for path in root.rglob("*.yaml"):
        if any(p in path.parts for p in ("node_modules", ".venv", "graphify-out", ".git")):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"image:\s*[^\n]*mailhog", text, re.I):
            offenders.append(str(path.relative_to(root)))
    assert not offenders, f"Mailhog still pinned: {offenders[:12]}"


def test_hs17_booking_email_appears_in_mailpit() -> None:
    marker = f"hs17-{uuid4().hex[:12]}"
    to = f"{marker}@test.porterchain.com"
    try:
        DeliveryService()._send_email(
            to,
            "booking_confirmed",
            {
                "tracking_number": f"PC-{marker}",
                "order_number": f"ORD-{marker}",
                "invoice_number": f"INV-{marker}",
                "booking_number": f"BK-{marker}",
            },
        )
    except (OSError, DeliveryDeferred) as exc:
        pytest.skip(f"SMTP/Mailpit unavailable: {exc}")

    query = urllib.parse.urlencode({"query": f"to:{to}"})
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:8025/api/v1/search?{query}", timeout=5) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError) as exc:
        pytest.skip(f"Mailpit API unavailable: {exc}")

    messages = data.get("messages") or []
    assert messages, f"expected Mailpit message for {to}"
    subject = (messages[0].get("Subject") or messages[0].get("subject") or "").lower()
    assert "confirmed" in subject or "porterchain" in subject


@pytest.mark.parametrize(
    ("host", "port", "expected"),
    [
        ("127.0.0.1", 51025, ("127.0.0.1", 51025)),  # explicit loopback catcher honoured
        ("smtp.zohocloud.ca", 465, ("localhost", 1025)),  # real SMTP never used locally
        ("", 587, ("localhost", 1025)),
    ],
)
def test_local_smtp_target(host, port, expected) -> None:
    from types import SimpleNamespace
    from unittest.mock import patch

    from porterchain_api.notification_engine.delivery_service import DeliveryService

    settings = SimpleNamespace(app_env="local", smtp_host=host, smtp_port=port, smtp_user="", smtp_password="")
    with patch("porterchain_api.notification_engine.delivery_service.smtplib.SMTP") as smtp:
        DeliveryService._send_email_smtp(
            DeliveryService.__new__(DeliveryService),
            recipient="r@example.test", subject="s", text_body="t", html_body="<p>t</p>",
            from_addr="f@example.test", from_name="PC", settings=settings,
        )
    assert smtp.call_args.args[:2] == expected


def test_local_docker_mailpit_host_is_honoured(monkeypatch) -> None:
    """Containerised local stack: MAIL_HOST=pcd-ls-mailpit must not be rewritten to localhost."""
    from types import SimpleNamespace
    from porterchain_api.notification_engine import delivery_service as ds

    seen = {}

    class FakeSMTP:
        def __init__(self, host, port, *a, **k):
            seen["hp"] = (host, port)
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def send_message(self, msg):
            seen["sent"] = True
        def starttls(self, *a, **k):
            pass
        def login(self, *a):
            pass

    monkeypatch.setattr(ds.smtplib, "SMTP", FakeSMTP)
    st = SimpleNamespace(smtp_host="pcd-ls-mailpit", smtp_port=1025, app_env="local", smtp_user="", smtp_password="")
    ds.DeliveryService()._send_email_smtp(
        recipient="a@b.c", subject="s", text_body="t", html_body="<p>t</p>", from_addr="n@local.test", from_name="P", settings=st
    )
    assert seen["hp"] == ("pcd-ls-mailpit", 1025) and seen["sent"]
