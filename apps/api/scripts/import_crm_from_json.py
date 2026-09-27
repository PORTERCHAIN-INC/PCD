"""One-shot: ingest crm_leads_export.json into CrmLead (prod/local).

Mirrors apps/api/scripts/import_crm_leads.py (quiet, idempotent).

Usage (inside API container):
  cd /app/apps/api && PYTHONPATH=src python /tmp/import_crm_from_json.py /tmp/crm_leads_export.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from porterchain_api.collaboration_engine.lead_ingest_service import (
    CanonicalLeadEvent,
    LeadIngestService,
    normalize_phone_e164,
)
from porterchain_api.db import SessionLocal, init_db
from porterchain_api.domain.crm_states import (
    LeadIntentType,
    LeadPriority,
    LeadSourceChannel,
    LeadStatus,
)

PROVIDER = "crm_db"
SOURCE = "crm_import"
BATCH = 100
GTA = frozenset(
    {
        "toronto",
        "mississauga",
        "markham",
        "brampton",
        "etobicoke",
        "vaughan",
        "scarborough",
        "concord",
        "oakville",
        "woodbridge",
        "richmond hill",
        "north york",
        "burlington",
        "ajax",
        "pickering",
        "oshawa",
    }
)
_TIER = {
    "A+": LeadPriority.HIGH.value,
    "A": LeadPriority.HIGH.value,
    "B": LeadPriority.MEDIUM.value,
    "C": LeadPriority.LOW.value,
    "D": LeadPriority.LOW.value,
}


def _phone(raw: object) -> str | None:
    if not raw:
        return None
    return normalize_phone_e164(str(raw)) or None


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/crm_leads_export.json")
    rows = json.loads(path.read_text())
    print(f"CRM JSON rows: {len(rows)}")
    init_db()
    ingest = LeadIngestService()
    db = SessionLocal()
    created = skipped = 0
    try:
        for i, row in enumerate(rows, 1):
            name = (row.get("name") or "").strip()
            if not name:
                continue
            company_id = str(row["company_id"])
            ph = _phone(row.get("phone") or row.get("contact_phone"))
            email = (row.get("email") or row.get("contact_email") or "").strip() or None
            city = (row.get("city") or "").strip()
            tier = (row.get("dial_tier") or "").strip().upper() or None
            dial_status = (row.get("dial_status") or "NEW").strip()
            score = row.get("dial_score")
            tags = ["crm_import", f"dial:{dial_status.lower()}"]
            if tier:
                tags.append(f"tier:{tier.lower()}")
            if city.lower() in GTA:
                tags.append("cohort:gta")
            elif city:
                tags.append("cohort:ontario")
            if not ph:
                tags.append("needs_phone")
            if dial_status == "READY_TO_CALL" and ph:
                tags.append("call_queue")
            if tier in ("A+", "A") and ph:
                priority = LeadPriority.HIGH.value
            elif ph and tier == "B":
                priority = LeadPriority.MEDIUM.value
            else:
                priority = _TIER.get(tier or "", LeadPriority.LOW.value)
            contact = (
                " ".join(
                    p
                    for p in [
                        (row.get("contact_first") or "").strip(),
                        (row.get("contact_last") or "").strip(),
                    ]
                    if p
                )
                or None
            )
            address = {
                k: v
                for k, v in {
                    "line1": (row.get("dial_address") or "").strip() or None,
                    "city": city or None,
                    "province": (row.get("province") or "").strip() or None,
                    "postal_code": (row.get("postal_code") or "").strip() or None,
                    "country": "CA",
                }.items()
                if v
            }
            event = CanonicalLeadEvent(
                channel=LeadSourceChannel.MANUAL.value,
                source=SOURCE,
                provider=PROVIDER,
                external_event_id=f"crm:{company_id}",
                company_name=name[:255],
                primary_contact_name=contact,
                email=email,
                phone=ph,
                intent_type=LeadIntentType.MERCHANT.value,
                priority=priority,
                status=LeadStatus.NEW.value,
                tags=tags,
                custom_fields={
                    "crm_company_id": company_id,
                    "dial_status": dial_status,
                    "dial_tier": tier,
                    "dial_score": float(score) if score is not None else None,
                    "dial_rank": row.get("dial_rank"),
                    "industry": (row.get("industry") or "").strip() or None,
                    "website": (row.get("website") or "").strip() or None,
                    "call_result": row.get("call_result"),
                    "next_action": row.get("next_action"),
                    "source_lead_id": row.get("source_lead_id"),
                    "source_row": row.get("source_row"),
                },
                external_ids={"crm_company_id": company_id},
                seed_conversation=False,
                sla_first_response_minutes=0,
                quiet=True,
            )
            result = ingest.ingest(db, event)
            lead = result.lead
            if address:
                lead.address = address
                lead.service_area = city or lead.service_area
            if row.get("industry"):
                lead.industry = str(row["industry"])[:128]
            if row.get("website"):
                lead.website = str(row["website"])[:512]
            if score is not None:
                try:
                    lead.lead_score = max(int(lead.lead_score or 0), int(float(score)))
                except (TypeError, ValueError):
                    pass
            db.flush()
            if result.created:
                created += 1
            else:
                skipped += 1
            if (created + skipped) % BATCH == 0:
                db.commit()
                print(f"  …processed {created + skipped}")
        db.commit()
        print("CRM → PCD prod import complete:")
        print(f"  created : {created}")
        print(f"  skipped : {skipped} (idempotent / merged)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
