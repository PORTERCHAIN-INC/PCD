"""Re-ingest archived vendors.csv into PCD CrmLead (sole SSOT) via LeadIngestService.

Live outbound state lives only on CrmLead (source=vendor_import). The CSV under
docs/archive/vendor-leads/ is archive-only — not a parallel lead store.
CRM/LEADS patterns inspired Dial UX; no fork.

Idempotent: provider=vendor_csv + external_event_id=vendor:{index}.
Quiet bulk ingest (no nurture seed — cold outbound; no consent).

Usage:
    cd apps/api && PYTHONPATH=src python scripts/import_vendors.py [path/to/vendors.csv]
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from porterchain_api.collaboration_engine.crm_helpers import province_from_postal
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

# Repo root = parents[3] from apps/api/scripts/
DEFAULT_CSV = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "archive"
    / "vendor-leads"
    / "vendors.csv"
)
PROVIDER = "vendor_csv"
SOURCE = "vendor_import"
BATCH_COMMIT = 100

GTA_CITIES = frozenset(
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
        "richmondhill",
        "north york",
        "ajax",
        "pickering",
        "burlington",
        "milton",
        "newmarket",
        "aurora",
        "north york",
        "york",
        "peel",
        "caledon",
        "whitby",
        "oshawa",
        "thornhill",
    }
)

NOISE_SUBSTR = (
    "MINISTER OF FINANCE",
    "RECEIVER GENERAL",
    "WORKPLACE SAFETY & INSURANCE",
    "407 ETR",
)


def build_address(row: dict[str, str]) -> dict[str, str]:
    address: dict[str, str] = {}
    if street := (row.get("address") or "").strip():
        address["street"] = street
    if city := (row.get("city") or "").strip():
        address["city"] = city.title()
    postal = (row.get("postal_code") or "").strip()
    if postal:
        address["postal_code"] = postal
    if province := province_from_postal(postal):
        address["province"] = province
    if address:
        address["country"] = "Canada"
    return address


def _is_gta(city: str) -> bool:
    c = city.strip().lower().replace("–", "-")
    if c in GTA_CITIES:
        return True
    return any(g in c for g in GTA_CITIES)


def _is_noise(name: str) -> bool:
    upper = name.upper()
    return any(s in upper for s in NOISE_SUBSTR)


def _usable_phone(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    digits = re.sub(r"\D", "", str(raw).strip())
    if not digits or set(digits) <= {"0"}:
        return None
    return normalize_phone_e164(raw)


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    init_db()
    db = SessionLocal()
    ingest = LeadIngestService()
    created = skipped = blank = noise_n = 0
    try:
        with csv_path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for i, row in enumerate(reader, start=1):
                name = (row.get("vendor_name") or "").strip()
                if not name:
                    blank += 1
                    continue

                idx = (row.get("index") or "").strip() or str(i)
                phone = _usable_phone(row.get("phone"))
                address = build_address(row)
                city = address.get("city") or ""
                gta = _is_gta(city)
                is_noise = _is_noise(name)

                tags = ["vendor_import"]
                if gta:
                    tags.append("cohort:gta")
                else:
                    tags.append("cohort:ontario")
                if not phone:
                    tags.append("needs_phone")
                if is_noise:
                    tags.append("noise")

                if phone and gta and not is_noise:
                    priority = LeadPriority.HIGH.value
                elif phone and not is_noise:
                    priority = LeadPriority.MEDIUM.value
                else:
                    priority = LeadPriority.LOW.value

                status = LeadStatus.UNQUALIFIED.value if is_noise else LeadStatus.NEW.value
                if is_noise:
                    noise_n += 1

                event = CanonicalLeadEvent(
                    channel=LeadSourceChannel.MANUAL.value,
                    source=SOURCE,
                    provider=PROVIDER,
                    external_event_id=f"vendor:{idx}",
                    company_name=name[:255],
                    phone=phone,
                    intent_type=LeadIntentType.MERCHANT.value,
                    priority=priority,
                    status=status,
                    tags=tags,
                    custom_fields={
                        "vendor_index": idx,
                        "phone_raw": (row.get("phone") or "").strip() or None,
                    },
                    external_ids={"vendor_csv_index": idx},
                    seed_conversation=False,
                    sla_first_response_minutes=0,
                    quiet=True,
                )
                result = ingest.ingest(db, event)
                lead = result.lead
                if address:
                    lead.address = address
                    lead.service_area = city or lead.service_area
                    db.flush()
                if result.created:
                    created += 1
                else:
                    skipped += 1

                if (created + skipped) % BATCH_COMMIT == 0:
                    db.commit()
                    print(f"  …processed {created + skipped}")

        db.commit()
        print("Vendor import complete:")
        print(f"  created  : {created}")
        print(f"  skipped  : {skipped} (idempotent / merged)")
        print(f"  blank    : {blank}")
        print(f"  noise    : {noise_n} (tagged unqualified)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
