"""WA auto-reply unit tests (lead enrichment by scraping was removed, doc 78)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from porterchain_api.collaboration_engine.lead_agent import reply_inbound_whatsapp
from porterchain_api.crm_models import CrmLead


def test_no_contact_scraping_module() -> None:
    """Doc 78 §1: email discovery by scraping is removed (PIPEDA)."""
    import importlib.util

    assert importlib.util.find_spec("porterchain_api.collaboration_engine.lead_enrich") is None


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
