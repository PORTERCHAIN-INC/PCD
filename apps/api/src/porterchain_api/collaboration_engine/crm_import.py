"""CRM CSV import."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.domain.crm_states import DealStage
from porterchain_api.collaboration_engine.crm_helpers import _to_int



class CrmImportMixin:
    def import_rows(
        self, db: Session, ctx: AdminContext | None, entity: str, rows: list[dict], dedupe: bool = True
    ) -> dict[str, Any]:
        imported = 0
        duplicates = 0
        errors: list[dict] = []

        for index, row in enumerate(rows):
            try:
                if entity == "companies":
                    name = (row.get("legal_name") or row.get("company_name") or "").strip()
                    if not name:
                        raise ValueError("legal_name is required")
                    if dedupe and self.find_company_duplicate(db, legal_name=name, email=row.get("email")):
                        duplicates += 1
                        continue
                    self.create_company(
                        db,
                        ctx,
                        {
                            "legal_name": name,
                            "operating_name": row.get("operating_name"),
                            "industry": row.get("industry"),
                            "website": row.get("website"),
                            "phone": row.get("phone"),
                            "email": row.get("email"),
                            "service_area": row.get("service_area"),
                            "estimated_deliveries_per_month": _to_int(row.get("estimated_deliveries_per_month")),
                            "merchant_status": row.get("merchant_status") or "lead",
                        },
                    )
                    imported += 1
                elif entity == "contacts":
                    first = (row.get("first_name") or "").strip()
                    if not first:
                        raise ValueError("first_name is required")
                    self.create_contact(
                        db,
                        ctx,
                        {
                            "company_id": row.get("company_id"),
                            "first_name": first,
                            "last_name": row.get("last_name"),
                            "designation": row.get("designation"),
                            "email": row.get("email"),
                            "phone": row.get("phone"),
                            "mobile": row.get("mobile"),
                        },
                    )
                    imported += 1
                elif entity == "leads":
                    company = (row.get("company_name") or "").strip()
                    if not company:
                        raise ValueError("company_name is required")
                    known = {
                        "company_name", "industry", "website", "business_type", "email", "phone",
                        "primary_contact_name", "source", "priority", "status",
                        "estimated_deliveries_per_month", "estimated_revenue_cents",
                        "preferred_vehicle", "service_area", "current_logistics_provider",
                        "street", "city", "province", "postal_code", "country", "address",
                    }
                    address = {
                        k: row[k]
                        for k in ("street", "city", "province", "postal_code", "country")
                        if row.get(k)
                    }
                    # Any column we don't explicitly model is preserved on the lead.
                    extras = {k: v for k, v in row.items() if k not in known and str(v).strip()}
                    self.create_lead(
                        db,
                        ctx,
                        {
                            "company_name": company,
                            "industry": row.get("industry"),
                            "website": row.get("website"),
                            "business_type": row.get("business_type"),
                            "email": row.get("email"),
                            "phone": row.get("phone"),
                            "primary_contact_name": row.get("primary_contact_name"),
                            "source": row.get("source") or "csv_import",
                            "priority": row.get("priority") or "medium",
                            "estimated_deliveries_per_month": _to_int(row.get("estimated_deliveries_per_month")),
                            "estimated_revenue_cents": _to_int(row.get("estimated_revenue_cents")),
                            "preferred_vehicle": row.get("preferred_vehicle"),
                            "service_area": row.get("service_area") or address.get("city"),
                            "current_logistics_provider": row.get("current_logistics_provider"),
                            "address": address,
                            "custom_fields": extras,
                        },
                    )
                    imported += 1
                elif entity == "deals":
                    name = (row.get("name") or "").strip()
                    if not name:
                        raise ValueError("name is required")
                    self.create_deal(
                        db,
                        ctx,
                        {
                            "name": name,
                            "company_id": row.get("company_id"),
                            "stage": row.get("stage") or DealStage.PROSPECTING.value,
                            "expected_revenue_cents": _to_int(row.get("expected_revenue_cents")) or 0,
                        },
                    )
                    imported += 1
                else:
                    raise ValueError(f"unsupported entity '{entity}'")
            except Exception as exc:  # noqa: BLE001 — collect per-row errors
                db.rollback()
                errors.append({"row": index + 1, "error": str(exc)})

        return {
            "entity": entity,
            "total": len(rows),
            "imported": imported,
            "duplicates": duplicates,
            "errors": errors,
        }


