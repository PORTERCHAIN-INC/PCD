"""Merchant 360 — admin merchant command center aggregation.

Per masterrule.md: merchants, CRM, invoices, contracts, billing are Porterchain
business logic. This service reads only Porterchain-owned data (Merchant, Order,
CRM company/contacts/contracts/invoices/activities/tasks, merchant sub-models).
Operational order data is the Porterchain mirror — Fleetbase is never called here.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.crm_models import (
    CrmActivity,
    CrmCompany,
    CrmContact,
    CrmContract,
    CrmInvoice,
    CrmSalesTask,
)
from porterchain_api.merchant_models import (
    Merchant,
    MerchantApiKey,
    MerchantRecipient,
    MerchantUser,
    MerchantWebhook,
    SavedAddress,
)
from porterchain_api.models import Order


def _now() -> datetime:
    return datetime.now(UTC)


OUTSTANDING_STATUSES = ("sent", "overdue", "partial")
OPEN_ORDER_STATES = ("BOOKED", "DISPATCH_READY", "ASSIGNED", "IN_TRANSIT", "OUT_FOR_DELIVERY")


class Merchant360Service:
    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _linked_company(self, db: Session, merchant_id: str) -> CrmCompany | None:
        return db.query(CrmCompany).filter(CrmCompany.merchant_id == merchant_id).first()

    def _metrics(self, db: Session, merchant: Merchant, company: CrmCompany | None) -> dict[str, Any]:
        cutoff = _now() - timedelta(days=30)
        orders = db.query(Order).filter(Order.merchant_id == merchant.id)
        monthly = orders.filter(Order.created_at >= cutoff).all()
        lifetime_count = orders.count()
        lifetime_revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.merchant_id == merchant.id)
            .scalar()
            or 0
        )
        monthly_revenue = sum(o.amount_cents for o in monthly)
        open_orders = orders.filter(Order.state.in_(OPEN_ORDER_STATES)).count()

        outstanding = 0
        overdue = 0
        if company:
            invs = db.query(CrmInvoice).filter(CrmInvoice.company_id == company.id).all()
            today = _now().date()
            for inv in invs:
                if inv.status in OUTSTANDING_STATUSES:
                    outstanding += inv.total_cents
                    if inv.due_date and inv.due_date < today:
                        overdue += inv.total_cents

        api_connected = (
            db.query(MerchantApiKey)
            .filter(MerchantApiKey.merchant_id == merchant.id, MerchantApiKey.is_active == True)  # noqa: E712
            .count()
            > 0
        )
        active_contract = False
        if company:
            active_contract = (
                db.query(CrmContract)
                .filter(CrmContract.company_id == company.id, CrmContract.status == "active")
                .count()
                > 0
            )

        last_order = orders.order_by(Order.created_at.desc()).first()
        last_activity_at = last_order.created_at if last_order else merchant.updated_at

        return {
            "monthly_orders": len(monthly),
            "monthly_revenue_cents": monthly_revenue,
            "lifetime_orders": lifetime_count,
            "lifetime_revenue_cents": int(lifetime_revenue),
            "open_orders": open_orders,
            "outstanding_balance_cents": outstanding,
            "overdue_balance_cents": overdue,
            "api_connected": api_connected,
            "active_contract": active_contract,
            "last_activity_at": last_activity_at,
        }

    def _health(self, merchant: Merchant, metrics: dict) -> int:
        score = 50
        if merchant.status == "ACTIVE":
            score += 15
        elif merchant.status == "SUSPENDED":
            score -= 30
        if metrics["monthly_orders"] > 0:
            score += min(20, metrics["monthly_orders"])
        else:
            score -= 10
        if metrics["active_contract"]:
            score += 10
        if metrics["api_connected"]:
            score += 5
        if metrics["overdue_balance_cents"] > 0:
            score -= 20
        elif metrics["outstanding_balance_cents"] > 0:
            score -= 5
        return max(0, min(100, score))

    def _ai_insights(self, merchant: Merchant, company: CrmCompany | None, metrics: dict, health: int) -> dict:
        risk = "low"
        if health < 40 or metrics["overdue_balance_cents"] > 0:
            risk = "high"
        elif health < 65:
            risk = "medium"
        payment_risk = "high" if metrics["overdue_balance_cents"] > 0 else (
            "medium" if metrics["outstanding_balance_cents"] > 0 else "low"
        )
        # Revenue trend proxy: monthly vs lifetime average.
        avg = metrics["lifetime_revenue_cents"] / max(1, metrics["lifetime_orders"]) if metrics["lifetime_orders"] else 0
        trend = "up" if metrics["monthly_orders"] > 0 else "flat"
        predicted_monthly = metrics["monthly_revenue_cents"] or int(avg * metrics["monthly_orders"])
        suggestions: list[str] = []
        if metrics["overdue_balance_cents"] > 0:
            suggestions.append("Follow up on overdue invoices to reduce payment risk.")
        if metrics["monthly_orders"] == 0 and merchant.status == "ACTIVE":
            suggestions.append("No orders in 30 days — schedule a re-engagement call.")
        if not metrics["active_contract"]:
            suggestions.append("No active contract — propose a service agreement.")
        if not metrics["api_connected"]:
            suggestions.append("Offer API/Shopify integration to increase volume.")
        if not suggestions:
            suggestions.append("Account is healthy — explore upsell on additional service areas.")
        return {
            "risk_score": risk,
            "payment_risk": payment_risk,
            "revenue_trend": trend,
            "predicted_monthly_revenue_cents": predicted_monthly,
            "renewal_risk": "high" if not metrics["active_contract"] else "low",
            "suggested_actions": suggestions,
        }

    def _row(self, db: Session, merchant: Merchant, *, light: bool = False) -> dict[str, Any]:
        company = self._linked_company(db, merchant.id)
        metrics = self._metrics(db, merchant, company)
        health = self._health(merchant, metrics)
        primary = None
        if company:
            primary = (
                db.query(CrmContact)
                .filter(CrmContact.company_id == company.id, CrmContact.is_primary == True)  # noqa: E712
                .first()
            )
        address = (company.address if company else None) or merchant.billing_address or {}
        contract_status = "active" if metrics["active_contract"] else "none"
        row = {
            "id": merchant.id,
            "company_name": merchant.company_name,
            "legal_name": merchant.legal_name,
            "logo_url": company.logo_url if company else None,
            "status": merchant.status,
            "industry": (company.industry if company else None) or (merchant.profile or {}).get("industry"),
            "city": address.get("city"),
            "province": address.get("province"),
            "country": address.get("country"),
            "email": merchant.email,
            "phone": merchant.phone,
            "primary_contact": (
                f"{primary.first_name} {primary.last_name or ''}".strip() if primary else None
            ),
            "payment_terms": merchant.payment_terms,
            "contract_status": contract_status,
            "monthly_deliveries": metrics["monthly_orders"],
            "monthly_revenue_cents": metrics["monthly_revenue_cents"],
            "outstanding_balance_cents": metrics["outstanding_balance_cents"],
            "health_score": health,
            "api_connected": metrics["api_connected"],
            "service_area": company.service_area if company else None,
            "owner_id": company.owner_id if company else None,
            "tags": (company.tags if company else None) or [],
            "last_activity_at": metrics["last_activity_at"],
            "created_at": merchant.created_at,
            "company_id": company.id if company else None,
        }
        if not light:
            row["metrics"] = metrics
        return row

    # ------------------------------------------------------------------ #
    # List / facets / stats
    # ------------------------------------------------------------------ #
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
        return [self._row(db, m, light=True) for m in merchants]

    def facets(self, db: Session) -> dict:
        status_rows = db.query(Merchant.status, func.count(Merchant.id)).group_by(Merchant.status).all()
        terms_rows = (
            db.query(Merchant.payment_terms, func.count(Merchant.id)).group_by(Merchant.payment_terms).all()
        )
        return {
            "statuses": [{"value": s, "count": n} for s, n in status_rows if s],
            "payment_terms": [{"value": t, "count": n} for t, n in terms_rows if t],
        }

    def stats(self, db: Session) -> dict:
        total = db.query(func.count(Merchant.id)).scalar() or 0
        active = db.query(func.count(Merchant.id)).filter(Merchant.status == "ACTIVE").scalar() or 0
        pending = db.query(func.count(Merchant.id)).filter(Merchant.status == "PENDING").scalar() or 0
        suspended = db.query(func.count(Merchant.id)).filter(Merchant.status == "SUSPENDED").scalar() or 0
        cutoff = _now() - timedelta(days=30)
        monthly_revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.merchant_id.isnot(None), Order.created_at >= cutoff)
            .scalar()
            or 0
        )
        outstanding = (
            db.query(func.coalesce(func.sum(CrmInvoice.total_cents), 0))
            .filter(CrmInvoice.status.in_(OUTSTANDING_STATUSES))
            .scalar()
            or 0
        )
        return {
            "total": total,
            "active": active,
            "pending": pending,
            "suspended": suspended,
            "monthly_revenue_cents": int(monthly_revenue),
            "outstanding_balance_cents": int(outstanding),
        }

    # ------------------------------------------------------------------ #
    # Detail (360)
    # ------------------------------------------------------------------ #
    def detail(self, db: Session, merchant_id: str) -> dict | None:
        merchant = db.get(Merchant, merchant_id)
        if not merchant:
            return None
        company = self._linked_company(db, merchant_id)
        metrics = self._metrics(db, merchant, company)
        health = self._health(merchant, metrics)
        ai = self._ai_insights(merchant, company, metrics, health)
        row = self._row(db, merchant, light=False)
        row.update(
            {
                "hst_number": merchant.hst_number,
                "business_number": merchant.business_number,
                "credit_limit_cents": merchant.credit_limit_cents,
                "billing_address": merchant.billing_address or {},
                "preferred_vehicles": merchant.preferred_vehicles or [],
                "delivery_zones": merchant.delivery_zones or [],
                "pricing_config": merchant.pricing_config or {},
                "profile": merchant.profile or {},
                "activated_at": merchant.activated_at,
                "website": company.website if company else None,
                "health": health,
                "ai": ai,
                "counts": {
                    "contacts": db.query(CrmContact).filter(CrmContact.company_id == (company.id if company else "")).count() if company else 0,
                    "users": db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant_id).count(),
                    "locations": db.query(SavedAddress).filter(SavedAddress.merchant_id == merchant_id).count(),
                    "api_keys": db.query(MerchantApiKey).filter(MerchantApiKey.merchant_id == merchant_id).count(),
                    "open_tasks": db.query(CrmSalesTask).filter(
                        CrmSalesTask.company_id == (company.id if company else ""),
                        CrmSalesTask.status.in_(["open", "in_progress"]),
                    ).count() if company else 0,
                },
            }
        )
        return row

    # ------------------------------------------------------------------ #
    # Sub-resources
    # ------------------------------------------------------------------ #
    def orders(self, db: Session, merchant_id: str, *, state: str | None = None, limit: int = 200) -> list[dict]:
        q = db.query(Order).filter(Order.merchant_id == merchant_id)
        if state:
            q = q.filter(Order.state == state)
        rows = q.order_by(Order.created_at.desc()).limit(limit).all()
        return [
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
            }
            for o in rows
        ]

    def locations(self, db: Session, merchant_id: str) -> dict:
        addresses = db.query(SavedAddress).filter(SavedAddress.merchant_id == merchant_id).all()
        recipients = db.query(MerchantRecipient).filter(MerchantRecipient.merchant_id == merchant_id).all()
        return {
            "addresses": [
                {
                    "id": a.id,
                    "label": a.label,
                    "address_type": a.address_type,
                    "formatted": a.formatted,
                    "lat": a.lat,
                    "lng": a.lng,
                    "is_default": a.is_default,
                }
                for a in addresses
            ],
            "recipients": [
                {"id": r.id, "name": r.name, "email": r.email, "phone": r.phone, "company": r.company}
                for r in recipients
            ],
        }

    def team(self, db: Session, merchant_id: str) -> list[dict]:
        users = db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant_id).all()
        return [
            {"id": u.id, "email": u.email, "role": u.role, "is_active": u.is_active, "created_at": u.created_at.isoformat()}
            for u in users
        ]

    def api_keys(self, db: Session, merchant_id: str) -> dict:
        keys = db.query(MerchantApiKey).filter(MerchantApiKey.merchant_id == merchant_id).all()
        hooks = db.query(MerchantWebhook).filter(MerchantWebhook.merchant_id == merchant_id).all()
        return {
            "api_keys": [
                {
                    "id": k.id,
                    "name": k.name,
                    "key_prefix": k.key_prefix,
                    "environment": k.environment,
                    "scopes": k.scopes,
                    "rate_limit_per_minute": k.rate_limit_per_minute,
                    "is_active": k.is_active,
                    "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                    "created_at": k.created_at.isoformat(),
                }
                for k in keys
            ],
            "webhooks": [
                {"id": w.id, "url": w.url, "events": w.events, "is_active": w.is_active, "created_at": w.created_at.isoformat()}
                for w in hooks
            ],
        }

    def analytics(self, db: Session, merchant_id: str) -> dict:
        orders = db.query(Order).filter(Order.merchant_id == merchant_id).all()
        by_month: dict[str, dict[str, int]] = defaultdict(lambda: {"orders": 0, "revenue_cents": 0})
        destinations: dict[str, int] = defaultdict(int)
        for o in orders:
            key = o.created_at.strftime("%Y-%m") if o.created_at else "unknown"
            by_month[key]["orders"] += 1
            by_month[key]["revenue_cents"] += o.amount_cents
            city = (o.dropoff or {}).get("city") if isinstance(o.dropoff, dict) else None
            if city:
                destinations[city] += 1
        months = sorted(by_month.keys())[-12:]
        return {
            "revenue_by_month": [{"month": m, **by_month[m]} for m in months],
            "top_destinations": sorted(
                ({"city": c, "orders": n} for c, n in destinations.items()), key=lambda x: -x["orders"]
            )[:8],
            "lifetime_orders": len(orders),
            "lifetime_revenue_cents": sum(o.amount_cents for o in orders),
        }

    def timeline(self, db: Session, merchant_id: str, company_id: str | None) -> list[dict]:
        events: list[dict] = []
        ids = [merchant_id] + ([company_id] if company_id else [])
        acts = (
            db.query(CrmActivity)
            .filter(CrmActivity.entity_id.in_(ids))
            .order_by(CrmActivity.occurred_at.desc())
            .limit(50)
            .all()
        )
        for a in acts:
            events.append(
                {
                    "kind": "activity",
                    "type": a.activity_type,
                    "title": a.subject or a.body or a.activity_type,
                    "at": a.occurred_at.isoformat(),
                }
            )
        orders = (
            db.query(Order).filter(Order.merchant_id == merchant_id).order_by(Order.created_at.desc()).limit(25).all()
        )
        for o in orders:
            events.append(
                {
                    "kind": "order",
                    "type": o.state,
                    "title": f"Order {o.order_number} — {o.state}",
                    "at": o.created_at.isoformat() if o.created_at else None,
                }
            )
        if company_id:
            invs = (
                db.query(CrmInvoice)
                .filter(CrmInvoice.company_id == company_id)
                .order_by(CrmInvoice.created_at.desc())
                .limit(25)
                .all()
            )
            for inv in invs:
                events.append(
                    {
                        "kind": "invoice",
                        "type": inv.status,
                        "title": f"Invoice {inv.invoice_number} — {inv.status}",
                        "at": inv.created_at.isoformat() if inv.created_at else None,
                    }
                )
        events.sort(key=lambda e: e["at"] or "", reverse=True)
        return events[:80]
