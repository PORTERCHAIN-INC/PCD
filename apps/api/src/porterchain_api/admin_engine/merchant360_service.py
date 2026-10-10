"""Merchant 360 — admin merchant command center aggregation.

Per masterrule.md: merchants, CRM, invoices, contracts, billing are Porterchain
business logic. This service reads only Porterchain-owned data (Merchant, Order,
CRM company/contacts/contracts/invoices/activities/tasks, merchant sub-models).
Operational order data comes from PorterChain orders.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.merchant360_board import (
    ai_insights,
    analytics_payload,
    api_keys_payload,
    batch_onboarding_summaries,
    detail_payload,
    health_score,
    locations_payload,
    metrics_payload,
    onboarding_payload,
    row_payload,
    stats_payload,
    timeline_payload,
)
from porterchain_api.admin_engine.settings_service import (
    _clerk_linked,
    _invite_status,
    _latest_invitations,
)
from porterchain_api.config import Settings
from porterchain_api.crm_models import CrmCompany
from porterchain_api.domain.catalog_labels import invite_status_label, seat_status_label
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.booking_models import Order


class Merchant360Service:
    def _linked_company(self, db: Session, merchant_id: str) -> CrmCompany | None:
        return db.query(CrmCompany).filter(CrmCompany.merchant_id == merchant_id).first()

    def _ops_ar_balances(self, db: Session, merchant: Merchant) -> tuple[int, int]:
        """Outstanding / overdue delivery AR — same cents as merchant Billing (BD)."""
        from porterchain_api.billing_engine.ar import merchant_ar

        ar = merchant_ar(db, merchant)
        return ar.outstanding_cents, ar.overdue_cents

    def _metrics(self, db: Session, merchant: Merchant, company: CrmCompany | None) -> dict[str, Any]:
        outstanding, overdue = self._ops_ar_balances(db, merchant)
        return metrics_payload(db, merchant, company, outstanding=outstanding, overdue=overdue)

    def _health(self, merchant: Merchant, metrics: dict) -> int:
        return health_score(merchant, metrics)

    def _ai_insights(
        self,
        merchant: Merchant,
        company: CrmCompany | None,
        metrics: dict,
        health: int,
        *,
        db: Session | None = None,
        flags: dict[str, bool] | None = None,
    ) -> dict:
        return ai_insights(merchant, company, metrics, health, db=db, flags=flags)

    def _row(
        self,
        db: Session,
        merchant: Merchant,
        *,
        light: bool = False,
        onboarding: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.merchant_engine.coverage import profile_service_area
        from porterchain_api.merchant_engine.organization_sync import branding_logo_url, industry_of

        return row_payload(
            self,
            db,
            merchant,
            light=light,
            onboarding=onboarding,
            logo_url=branding_logo_url(merchant),
            industry=industry_of(merchant),
            service_area=profile_service_area(merchant),
        )

    def _batch_onboarding_summaries(self, db: Session, merchants: list[Merchant]) -> dict[str, dict[str, Any]]:
        return batch_onboarding_summaries(db, merchants)

    def list_merchants(
        self,
        db: Session,
        *,
        status: str | None = None,
        payment_terms: str | None = None,
        search: str | None = None,
        limit: int = 500,
    ) -> list[dict]:
        q = db.query(Merchant)
        if status:
            q = q.filter(Merchant.status == status)
        if payment_terms:
            q = q.filter(Merchant.payment_terms == payment_terms)
        if search:
            like = f"%{search}%"
            q = q.filter(or_(Merchant.company_name.ilike(like), Merchant.email.ilike(like)))
        merchants = q.order_by(Merchant.created_at.desc()).limit(limit).all()
        summaries = self._batch_onboarding_summaries(db, merchants)
        return [self._row(db, m, light=True, onboarding=summaries.get(m.id)) for m in merchants]

    def facets(self, db: Session) -> dict:
        from sqlalchemy import func

        status_rows = db.query(Merchant.status, func.count(Merchant.id)).group_by(Merchant.status).all()
        terms_rows = (
            db.query(Merchant.payment_terms, func.count(Merchant.id)).group_by(Merchant.payment_terms).all()
        )
        return {
            "statuses": [{"value": s, "count": n} for s, n in status_rows if s],
            "payment_terms": [{"value": t, "count": n} for t, n in terms_rows if t],
        }

    def stats(self, db: Session) -> dict:
        from porterchain_api.billing_engine.ar import delivery_ar_total_cents

        return stats_payload(db, outstanding=delivery_ar_total_cents(db))

    def unprovisioned_signups(self, db: Session, settings: Settings) -> list[dict[str, Any]]:
        """Clerk merchant-app users with no Porterchain merchant_users row.

        Raises on Clerk directory failure so Admin can surface the error (M-4).
        """
        from porterchain_api.admin_engine.clerk_directory_service import fetch_clerk_snapshots

        try:
            snaps = fetch_clerk_snapshots(settings, "merchant", limit=500)
        except Exception as exc:
            raise RuntimeError(f"clerk_directory_unavailable: {exc}") from exc

        linked_clerk_ids = {
            u.clerk_user_id
            for u in db.query(MerchantUser).all()
            if u.clerk_user_id and not u.clerk_user_id.startswith("pending:")
        }
        linked_emails = {u.email.lower() for u in db.query(MerchantUser).all()}

        out: list[dict[str, Any]] = []
        for email, snap in snaps.items():
            if email in linked_emails or snap.clerk_user_id in linked_clerk_ids:
                continue
            name = " ".join(p for p in (snap.first_name, snap.last_name) if p) or email.split("@")[0]
            out.append(
                {
                    "email": email,
                    "name": name,
                    "clerk_user_id": snap.clerk_user_id,
                    "clerk_status": snap.clerk_status,
                    "last_sign_in_at": snap.last_sign_in_at.isoformat() if snap.last_sign_in_at else None,
                    "suggested_company_name": name.title(),
                }
            )
        out.sort(key=lambda r: r.get("last_sign_in_at") or "", reverse=True)
        return out

    def detail(self, db: Session, merchant_id: str) -> dict | None:
        merchant = db.get(Merchant, merchant_id)
        if not merchant:
            return None
        from porterchain_api.config import get_settings
        from porterchain_api.merchant_engine.coverage import coverage_snapshot
        from porterchain_api.merchant_engine.organization_sync import tax_legal_snapshot, website_of
        from porterchain_api.merchant_engine.profile_service import profile_public_fields

        return detail_payload(
            self,
            db,
            merchant,
            tax_legal=tax_legal_snapshot(merchant),
            extra=profile_public_fields(merchant),
            coverage=coverage_snapshot(merchant, db),
            website=website_of(merchant),
            flags=get_settings().phase2_flags,
        )

    def orders(
        self,
        db: Session,
        merchant_id: str,
        *,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        from porterchain_api.platform.pagination import MAX_EMBEDDED_LIST_LIMIT, as_page, clamp_page

        limit, offset = clamp_page(limit, offset, max_limit=MAX_EMBEDDED_LIST_LIMIT)
        q = db.query(Order).filter(Order.merchant_id == merchant_id)
        if state:
            q = q.filter(Order.state == state)
        q = q.order_by(Order.created_at.desc(), Order.id.desc())
        total = q.count()
        rows = q.offset(offset).limit(limit).all()
        items = [
            {
                "id": o.id,
                "order_number": o.order_number,
                "tracking_number": o.tracking_number,
                "state": o.state,
                "amount_cents": o.amount_cents,
                "scheduled_at": o.scheduled_at.isoformat() if o.scheduled_at else None,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "pickup": o.pickup,
                "dropoff": o.dropoff,
                "assigned_driver_id": o.assigned_driver_id,
                "order_source": o.order_source,
                "route_import_job_id": (
                    (o.compliance_metadata or {}).get("route_import_job_id")
                    if isinstance(o.compliance_metadata, dict)
                    else None
                ),
            }
            for o in rows
        ]
        return as_page(items, total, limit, offset)

    def locations(self, db: Session, merchant_id: str) -> dict:
        return locations_payload(db, merchant_id)

    def team(self, db: Session, merchant_id: str) -> list[dict]:
        from porterchain_api.merchant_engine.rbac import english_role
        from porterchain_api.merchant_engine.team_service import seat_status

        invitations = _latest_invitations(db, "merchant")
        users = db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant_id).all()
        rows: list[dict] = []
        for u in users:
            invite = _invite_status(invitations.get(u.email.lower()), u.clerk_user_id)
            seat = seat_status(u)
            rows.append(
                {
                    "id": u.id,
                    "email": u.email,
                    "role": u.role,
                    "role_label": english_role(u.role),
                    "is_active": u.is_active,
                    "seat_status": seat,
                    "seat_status_label": seat_status_label(seat),
                    "created_at": u.created_at.isoformat(),
                    "clerk_linked": _clerk_linked(u.clerk_user_id),
                    "invite_status": invite,
                    "invite_status_label": invite_status_label(invite),
                }
            )
        return rows

    def onboarding(self, db: Session, merchant_id: str) -> dict[str, Any]:
        merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
        if not merchant:
            raise LookupError("merchant_not_found")
        return onboarding_payload(db, merchant)

    def api_keys(self, db: Session, merchant_id: str) -> dict:
        return api_keys_payload(db, merchant_id)

    def analytics(self, db: Session, merchant_id: str) -> dict:
        return analytics_payload(db, merchant_id)

    def timeline(self, db: Session, merchant_id: str, company_id: str | None) -> list[dict]:
        return timeline_payload(db, merchant_id, company_id)
