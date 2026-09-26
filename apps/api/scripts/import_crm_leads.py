"""Import LEADS/CRM monorepo companies+dials into PCD CrmLead (sole SSOT).

Reads the local CRM Postgres (default: sibling repo ../CRM DATABASE_URL on :5433).
Idempotent: provider=crm_db + external_event_id=crm:{company_id}.
Quiet bulk — no nurture auto-email (cold outbound; almost no marketing consent).

Usage:
    cd apps/api && PYTHONPATH=src python scripts/import_crm_leads.py
    CRM_DATABASE_URL=postgresql://... PYTHONPATH=src python scripts/import_crm_leads.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg

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
BATCH_COMMIT = 100

_TIER_PRIORITY = {
    "A+": LeadPriority.HIGH.value,
    "A": LeadPriority.HIGH.value,
    "B": LeadPriority.MEDIUM.value,
    "C": LeadPriority.LOW.value,
    "D": LeadPriority.LOW.value,
}

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


def _crm_database_url() -> str:
    env_url = (os.environ.get("CRM_DATABASE_URL") or "").strip()
    if env_url:
        return env_url
    crm_env = Path(__file__).resolve().parents[3].parent / "CRM" / ".env"
    # Also try absolute sibling of PCD
    if not crm_env.is_file():
        crm_env = Path("/Users/ravi/Documents/GitHub/CRM/.env")
    if not crm_env.is_file():
        raise SystemExit(
            "Set CRM_DATABASE_URL or place CRM repo at ../CRM with DATABASE_URL in .env"
        )
    for line in crm_env.read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"No DATABASE_URL in {crm_env}")


def _psycopg_url(url: str) -> str:
    u = urlparse(url)
    return urlunparse((u.scheme, u.netloc, u.path, "", "", ""))


def _usable_phone(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    e164 = normalize_phone_e164(str(raw))
    if e164:
        return e164
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) >= 10:
        return str(raw).strip()[:32]
    return None


def _fetch_rows(conn: psycopg.Connection) -> list[dict]:
    sql = """
    SELECT
      c.id AS company_id,
      c.name,
      c.phone,
      c.email,
      c.city,
      c.website,
      c.industry,
      c."linkedinUrl" AS linkedin,
      d."leadStatus" AS dial_status,
      d.priority AS dial_tier,
      d.score AS dial_score,
      d.rank AS dial_rank,
      d.address AS dial_address,
      d."postalCode" AS postal_code,
      d.province,
      d."callResult" AS call_result,
      d."nextAction" AS next_action,
      d."followUpAt" AS follow_up_at,
      d."lastContactedAt" AS last_contacted_at,
      d."sourceLeadId" AS source_lead_id,
      d."sourceRowNumber" AS source_row,
      pc."firstName" AS contact_first,
      pc."lastName" AS contact_last,
      pc.email AS contact_email,
      pc.phone AS contact_phone
    FROM company c
    LEFT JOIN "companyDial" d ON d."companyId" = c.id
    LEFT JOIN contact pc ON pc.id = c."primaryContactId"
    ORDER BY d.rank ASC NULLS LAST, c."createdAt" ASC
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def main() -> None:
    raw_url = _crm_database_url()
    u = urlparse(raw_url)
    print(f"Reading CRM DB {u.hostname}:{u.port}{u.path} …")
    init_db()
    ingest = LeadIngestService()
    created = skipped = 0

    with psycopg.connect(_psycopg_url(raw_url)) as crm:
        rows = _fetch_rows(crm)
    print(f"  companies: {len(rows)}")

    db = SessionLocal()
    try:
        for i, row in enumerate(rows, start=1):
            name = (row.get("name") or "").strip()
            if not name:
                continue
            company_id = str(row["company_id"])
            phone = _usable_phone(row.get("phone") or row.get("contact_phone"))
            email = (row.get("email") or row.get("contact_email") or "").strip() or None
            city = (row.get("city") or "").strip()
            tier = (row.get("dial_tier") or "").strip().upper() or None
            dial_status = (row.get("dial_status") or "NEW").strip()
            score = row.get("dial_score")
            gta = city.lower() in GTA if city else False

            tags = ["crm_import", f"dial:{dial_status.lower()}"]
            if tier:
                tags.append(f"tier:{tier.lower()}")
            if gta:
                tags.append("cohort:gta")
            elif city:
                tags.append("cohort:ontario")
            if not phone:
                tags.append("needs_phone")
            if dial_status == "READY_TO_CALL" and phone:
                tags.append("call_queue")

            if tier in ("A+", "A") and phone:
                priority = LeadPriority.HIGH.value
            elif phone and tier == "B":
                priority = LeadPriority.MEDIUM.value
            else:
                priority = _TIER_PRIORITY.get(tier or "", LeadPriority.LOW.value)

            contact_name = " ".join(
                p
                for p in [(row.get("contact_first") or "").strip(), (row.get("contact_last") or "").strip()]
                if p
            ) or None

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
                primary_contact_name=contact_name,
                email=email,
                phone=phone,
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
            if (created + skipped) % BATCH_COMMIT == 0:
                db.commit()
                print(f"  …processed {created + skipped}")

        db.commit()
        print("CRM → PCD import complete:")
        print(f"  created : {created}")
        print(f"  skipped : {skipped} (idempotent / merged)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
