"""Lead agent + NBA — zero-human welcome matrix."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from porterchain_api.collaboration_engine.lead_agent import run_lead_agent
from porterchain_api.collaboration_engine.lead_nba import lead_next_best_action
from porterchain_api.crm_models import CrmLead


def test_nba_vendor_phone_only_enrich(db) -> None:
    lead = CrmLead(
        company_name=f"Vendor {uuid.uuid4().hex[:6]}",
        phone="+14165550100",
        source="vendor_import",
        channel="manual",
        status="new",
        consent={},
        tags=["vendor_import"],
    )
    db.add(lead)
    db.commit()
    nba = lead_next_best_action(db, lead)
    assert nba["class"] == "outbound_cold"
    assert nba["primary"]["action"] == "enrich_email"
    assert "no_cold" not in str(nba)  # blast blocked at agent layer


def test_nba_inbound_marketing_email(db) -> None:
    lead = CrmLead(
        company_name=f"Hot {uuid.uuid4().hex[:6]}",
        email=f"hot-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
        status="new",
        consent={"marketing": True},
    )
    db.add(lead)
    db.commit()
    nba = lead_next_best_action(db, lead)
    assert nba["primary"]["action"] == "email_template"
    assert nba["primary"]["template_key"] == "lead_nurture_intro"


def test_agent_sends_email_when_consented(db) -> None:
    lead = CrmLead(
        company_name=f"Agent {uuid.uuid4().hex[:6]}",
        email=f"agent-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
        status="new",
        consent={"marketing": True},
        tags=[],
    )
    db.add(lead)
    db.commit()
    with patch("porterchain_shared.queue.publisher.get_queue_publisher") as gp:
        pub = MagicMock()
        gp.return_value = pub
        with patch(
            "porterchain_api.collaboration_engine.lead_agent._agent_enabled",
            return_value=True,
        ):
            result = run_lead_agent(db, lead, trigger="test", website_url="https://example.com")
        db.commit()
        assert result["channels"]["email"]["status"] == "sent"
        pub.enqueue.assert_called_once()
    db.refresh(lead)
    assert "agent_welcomed" in (lead.tags or [])


def test_agent_blocks_without_marketing(db) -> None:
    lead = CrmLead(
        company_name=f"NoMkt {uuid.uuid4().hex[:6]}",
        email=f"nomkt-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
        status="new",
        consent={"marketing": False},
        tags=[],
    )
    db.add(lead)
    db.commit()
    with patch("porterchain_shared.queue.publisher.get_queue_publisher") as gp:
        result = run_lead_agent(db, lead, trigger="test")
        gp.return_value.enqueue.assert_not_called()
    assert result["channels"]["agent"]["status"] == "skipped"
    assert "marketing_consent_required" in (result["nba"].get("blocks") or [])


def test_agent_vendor_no_whatsapp_blast(db) -> None:
    lead = CrmLead(
        company_name=f"Cold {uuid.uuid4().hex[:6]}",
        phone="+14165550999",
        source="vendor_import",
        channel="manual",
        status="new",
        consent={},
        tags=["vendor_import"],
    )
    db.add(lead)
    db.commit()
    # force=True exercises the gates; auto-send itself is off by default now.
    result = run_lead_agent(db, lead, trigger="test", force=True)
    enrich = result["channels"]["enrich"]
    assert enrich["status"] in ("queued", "skipped", "not_found", "no_website") or enrich.get(
        "reason"
    ) in ("no_website", "phone_only_cold_vendor")
    assert result["channels"]["whatsapp"]["reason"] == "no_cold_whatsapp_blast"
