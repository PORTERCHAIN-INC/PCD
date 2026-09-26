"""Lead enrich + WA auto-reply unit tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from porterchain_api.collaboration_engine.lead_agent import reply_inbound_whatsapp
from porterchain_api.collaboration_engine.lead_enrich import (
    enrich_lead_email,
    extract_emails_from_html,
)
from porterchain_api.crm_models import CrmLead


def test_extract_emails_prefers_info() -> None:
    html = """
    <a href="mailto:noreply@example.com">x</a>
    <a href="mailto:info@acmecorp.ca">info</a>
    Contact sales@acmecorp.ca today
    """
    emails = extract_emails_from_html(html, company="Acme Corp")
    assert emails[0] == "info@acmecorp.ca"


def test_enrich_lead_from_website(db) -> None:
    lead = CrmLead(
        company_name=f"Acme {uuid.uuid4().hex[:6]}",
        phone="+14165550001",
        website="https://example-does-not-matter.test",
        source="vendor_import",
        channel="manual",
        status="new",
        consent={},
        tags=["vendor_import"],
    )
    db.add(lead)
    db.commit()
    html = '<html><a href="mailto:hello@acmewidgets.ca">Email</a></html>'
    with patch("porterchain_api.collaboration_engine.lead_enrich.httpx.Client") as Client:
        client = MagicMock()
        Client.return_value.__enter__.return_value = client
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html
        client.get.return_value = resp
        result = enrich_lead_email(db, lead)
        db.commit()
    assert result["status"] == "found"
    assert lead.email == "hello@acmewidgets.ca"
    assert (lead.consent or {}).get("legal_basis") == "legitimate_interest"
    assert not (lead.consent or {}).get("marketing")


def test_wa_auto_reply_care_window(db) -> None:
    lead = CrmLead(
        company_name=f"WA {uuid.uuid4().hex[:6]}",
        phone="14165550999",
        source="whatsapp",
        channel="whatsapp",
        status="new",
        tags=["meta", "dm", "whatsapp"],
        last_touch_at=datetime.now(UTC),
        consent={},
    )
    db.add(lead)
    db.commit()
    with patch(
        "porterchain_api.collaboration_engine.lead_whatsapp_cloud.whatsapp_cloud_configured",
        return_value=True,
    ), patch(
        "porterchain_api.collaboration_engine.lead_whatsapp_cloud.send_whatsapp_text",
        return_value={"status": "sent", "message_id": "wamid.1"},
    ), patch(
        "porterchain_api.collaboration_engine.lead_agent._agent_enabled",
        return_value=True,
    ):
        result = reply_inbound_whatsapp(db, lead, inbound_text="Need a quote for Mississauga")
        db.commit()
    assert result["status"] == "sent"
    assert "agent_welcomed" in (lead.tags or [])
