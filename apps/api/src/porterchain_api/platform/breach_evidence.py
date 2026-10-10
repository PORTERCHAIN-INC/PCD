"""One-click breach evidence pack for OPC (PIPEDA) / police: everything in one JSON file.

Contents: the breach record (PIPEDA record of breaches + RROSH assessment), timeline,
actions taken, notifications, the tamper-evident audit entries for the incident window
(with chain verification + signed checkpoints so integrity can be proven), the change
history of the breach record itself, and a mapping to the OPC breach report form.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

OPC_FORM = {
    "organization": "PorterChain Inc. (Ravi Chauhan, Owner, accountable for privacy: privacy@porterchain.com)",
    "description_of_circumstances": "description",
    "cause_if_known": "cause",
    "date_or_period_of_breach": ("occurred_from", "occurred_to"),
    "personal_information_involved": ("data_types", "records_affected"),
    "number_of_individuals_affected": "subjects_affected",
    "steps_taken_to_reduce_risk_of_harm": "measures",
    "steps_taken_or_intended_to_notify_individuals": "notifications",
    "real_risk_of_significant_harm_assessment": "rrosh",
    "contact_person": "Ravi Chauhan - privacy@porterchain.com / sales@porterchain.com",
}


def _dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s))
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    except ValueError:
        return None


def evidence_pack(db: Any, breach_id: str) -> dict[str, Any]:
    from porterchain_api.admin_models import AdminAuditLog, SystemConfig
    from porterchain_api.platform import forensics
    from porterchain_api.platform.compliance import (
        BREACH_KEY,
        breach_clock,
        normalize_breaches,
    )

    row = db.get(SystemConfig, BREACH_KEY)
    breaches = normalize_breaches(row.value if row is not None else [])
    b = next((x for x in breaches if x["id"] == breach_id), None)
    if b is None:
        raise LookupError("breach_not_found")
    start = _dt(b.get("occurred_from")) or (_dt(b["detected_at"]) - timedelta(days=30))
    end = max(_dt(b.get("occurred_to")) or datetime.now(UTC), datetime.now(UTC))
    audit = forensics.export(db, since=start - timedelta(days=1), until=end)
    history = [
        {"at": r.created_at.isoformat() if r.created_at else None, "actor": r.actor_user_id, "action": r.action}
        for r in db.query(AdminAuditLog).filter(AdminAuditLog.resource_id == BREACH_KEY)
        .order_by(AdminAuditLog.created_at).all()
    ]
    form = {k: (v if not isinstance(v, (str, tuple)) or k in ("organization", "contact_person")
                else ({f: b.get(f) for f in v} if isinstance(v, tuple) else b.get(v)))
            for k, v in OPC_FORM.items()}
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "notice": "Evidence pack generated from PorterChain systems. Times are UTC. Audit entries are "
                  "hash-chained; verify with the hash rule and the Ed25519 public key included.",
        "breach": breach_clock(b),
        "opc_report_fields": form,
        "record_change_history": history,
        "audit_window": {"from": start.isoformat(), "to": end.isoformat()},
        "audit_trail": audit,
    }
