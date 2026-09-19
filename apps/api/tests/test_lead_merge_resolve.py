"""Merge accept/reject for soft duplicate queue."""

from __future__ import annotations

import uuid

from porterchain_api.collaboration_engine.lead_ops import resolve_merge_candidate
from porterchain_api.crm_models import CrmLead


def test_merge_reject_clears_link(db) -> None:
    target = CrmLead(
        company_name=f"Target {uuid.uuid4().hex[:6]}",
        email=f"t-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
    )
    db.add(target)
    db.flush()
    cand = CrmLead(
        company_name=target.company_name,
        email=f"c-{uuid.uuid4().hex[:6]}@t.test",
        source="phone_call",
        channel="phone_call",
        merge_candidate_of=target.id,
    )
    db.add(cand)
    db.commit()
    db.refresh(cand)
    out = resolve_merge_candidate(db, lead_id=cand.id, action="reject", actor_id="staff-1")
    assert out.merge_candidate_of is None


def test_merge_accept_folds_into_target(db) -> None:
    target = CrmLead(
        company_name=f"Keep {uuid.uuid4().hex[:6]}",
        email=None,
        phone=None,
        source="website",
        channel="website",
    )
    db.add(target)
    db.flush()
    cand = CrmLead(
        company_name=target.company_name,
        email=f"merge-{uuid.uuid4().hex[:6]}@t.test",
        phone="+14165550199",
        source="whatsapp",
        channel="whatsapp",
        merge_candidate_of=target.id,
        internal_notes="from wa",
    )
    db.add(cand)
    db.commit()
    db.refresh(cand)
    kept = resolve_merge_candidate(db, lead_id=cand.id, action="accept", actor_id="staff-1")
    assert kept.id == target.id
    assert kept.email == cand.email or kept.email is not None
    db.refresh(cand)
    assert "merged_away" in (cand.tags or [])
