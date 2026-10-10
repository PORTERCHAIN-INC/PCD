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

from porterchain_api.notification_engine.delivery_service import (
    DeliveryDeferred,
    DeliveryService,
)


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
        if re.search(r"image:\s*[^\n]*mailhog", text, re.IGNORECASE):
            offenders.append(str(path.relative_to(root)))
        if re.search(r"^\s+mailhog\s*:", text, re.IGNORECASE | re.MULTILINE):
            offenders.append(str(path.relative_to(root)))
    for path in root.rglob("*.yaml"):
        if any(p in path.parts for p in ("node_modules", ".venv", "graphify-out", ".git")):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"image:\s*[^\n]*mailhog", text, re.IGNORECASE):
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
