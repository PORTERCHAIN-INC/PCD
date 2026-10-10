"""Merchant 360 board — metrics, row, onboarding, analytics, timeline."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.settings_service import (
    _clerk_linked,
    _invite_status,
    _latest_invitations,
)
from porterchain_api.booking_models import Invoice, Order
from porterchain_api.crm_models import (
    CrmActivity,
    CrmCompany,
    CrmContact,
    CrmContract,
    CrmInvoice,
    CrmSalesTask,
)
from porterchain_api.domain.catalog_labels import (
    invite_status_label,
    merchant_status_label,
    onboarding_phase_label,
)
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_models import (
    Merchant,
    MerchantApiKey,
    MerchantRecipient,
    MerchantUser,
    MerchantWebhook,
    SavedAddress,
    ShopifyShop,
)

OUTSTANDING_STATUSES = ("sent", "overdue", "partial")
OPEN_ORDER_STATES = ("BOOKED", "DISPATCH_READY", "ASSIGNED", "IN_TRANSIT", "OUT_FOR_DELIVERY")


def _now() -> datetime:
    return datetime.now(UTC)


def metrics_payload(
    db: Session,
    merchant: Merchant,
    company: CrmCompany | None,
    *,
    outstanding: int,
    overdue: int,
) -> dict[str, Any]:
    cutoff = _now() - timedelta(days=30)
    orders = db.query(Order).filter(Order.merchant_id == merchant.id, Order.is_sandbox.is_(False))
    monthly = orders.filter(Order.created_at >= cutoff).all()
    lifetime_count = orders.count()
    lifetime_revenue = (
        db.query(func.coalesce(func.sum(Order.amount_cents), 0))
        .filter(Order.merchant_id == merchant.id, Order.is_sandbox.is_(False))
        .scalar()
        or 0
    )
    monthly_revenue = sum(o.amount_cents for o in monthly)
    open_orders = orders.filter(Order.state.in_(OPEN_ORDER_STATES)).count()

    crm_outstanding = 0
    if company:
        invs = db.query(CrmInvoice).filter(CrmInvoice.company_id == company.id).all()
        for inv in invs:
            if inv.status in OUTSTANDING_STATUSES:
                crm_outstanding += inv.total_cents

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
        "crm_outstanding_balance_cents": crm_outstanding,
        "api_connected": api_connected,
        "active_contract": active_contract,
        "last_activity_at": last_activity_at,
    }


def health_score(merchant: Merchant, metrics: dict) -> int:
    score = 50
    if merchant.status == "ACTIVE":
        score += 15
    elif merchant.status == "SUSPENDED":
        score -= 30
    elif merchant.status == "CLOSED":
        score -= 40
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


def ai_insights(
    merchant: Merchant,
    company: CrmCompany | None,
    metrics: dict,
    health: int,
    *,
    db: Session | None = None,
    flags: dict[str, bool] | None = None,
) -> dict:
    risk = "low"
    if health < 40 or metrics["overdue_balance_cents"] > 0:
        risk = "high"
    elif health < 65:
        risk = "medium"
    payment_risk = "high" if metrics["overdue_balance_cents"] > 0 else (
        "medium" if metrics["outstanding_balance_cents"] > 0 else "low"
    )
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
    insights = {
        "risk_score": risk,
        "payment_risk": payment_risk,
        "revenue_trend": trend,
        "predicted_monthly_revenue_cents": predicted_monthly,
        "renewal_risk": "high" if not metrics["active_contract"] else "low",
        "suggested_actions": suggestions,
        "actions_source": "heuristic",
    }
    if db is None:
        return insights
    from porterchain_api.intelligence_engine.enrichers import paraphrase_merchant_actions

    return paraphrase_merchant_actions(insights, flags=flags, db=db)


def row_payload(
    svc: Any,
    db: Session,
    merchant: Merchant,
    *,
    light: bool = False,
    onboarding: dict[str, Any] | None = None,
    logo_url: str | None,
    industry: str | None,
    service_area: str | None,
) -> dict[str, Any]:
    company = svc._linked_company(db, merchant.id)
    metrics = svc._metrics(db, merchant, company)
    health = svc._health(merchant, metrics)
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
        "logo_url": logo_url or (company.logo_url if company else None),
        "status": merchant.status,
        "status_label": merchant_status_label(merchant.status),
        "industry": industry or (company.industry if company else None),
        "city": address.get("city"),
        "province": address.get("province"),
        "country": address.get("country"),
        "email": merchant.email,
        "phone": merchant.phone,
        "primary_contact": (
            f"{primary.first_name} {primary.last_name or ''}".strip() if primary else None
        ),
        "payment_terms": merchant.payment_terms,
        "parent_merchant_id": merchant.parent_merchant_id,
        "support_tier": (
            (merchant.profile or {}).get("enterprise", {}).get("support_tier")
            if isinstance(merchant.profile, dict)
            else None
        )
        or "standard",
        "contract_status": contract_status,
        "monthly_deliveries": metrics["monthly_orders"],
        "monthly_revenue_cents": metrics["monthly_revenue_cents"],
        "outstanding_balance_cents": metrics["outstanding_balance_cents"],
        "health_score": health,
        "api_connected": metrics["api_connected"],
        "service_area": service_area or (company.service_area if company else None),
        "owner_id": company.owner_id if company else None,
        "tags": (company.tags if company else None) or [],
        "last_activity_at": metrics["last_activity_at"],
        "created_at": merchant.created_at,
        "company_id": company.id if company else None,
    }
    if onboarding is not None:
        row.update(onboarding)
    if not light:
        row["metrics"] = metrics
    return row


def batch_onboarding_summaries(db: Session, merchants: list[Merchant]) -> dict[str, dict[str, Any]]:
    if not merchants:
        return {}
    ids = [m.id for m in merchants]
    users_by_mid: dict[str, list[MerchantUser]] = defaultdict(list)
    for mu in db.query(MerchantUser).filter(MerchantUser.merchant_id.in_(ids)).all():
        users_by_mid[mu.merchant_id].append(mu)
    invitations = _latest_invitations(db, "merchant")

    result: dict[str, dict[str, Any]] = {}
    for merchant in merchants:
        users = users_by_mid.get(merchant.id, [])
        owner = next((u for u in users if u.role == MerchantRole.OWNER.value), None)
        if not owner and users:
            owner = users[0]

        owner_invite = (
            _invite_status(invitations.get(owner.email.lower()), owner.clerk_user_id)
            if owner
            else "not_invited"
        )
        owner_linked = _clerk_linked(owner.clerk_user_id) if owner else False
        merchant_active = merchant.status == MerchantStatus.ACTIVE.value
        user_active = bool(owner and owner.is_active)
        company_ready = bool(merchant.company_name and merchant.email)

        steps = [
            owner is not None,
            owner is not None and owner_invite != "not_invited",
            owner_linked,
            merchant_active,
            user_active,
            company_ready,
        ]
        steps_complete = sum(1 for s in steps if s)
        ready = all(steps) and merchant.status != MerchantStatus.SUSPENDED.value

        if ready:
            phase = "ready"
        elif not owner or owner_invite in ("not_invited", "invite_failed", "revoked"):
            phase = "needs_invite"
        elif not owner_linked:
            phase = "awaiting_clerk"
        elif not user_active:
            phase = "needs_activation"
        elif not merchant_active:
            phase = "needs_approval"
        else:
            phase = "onboarding"

        result[merchant.id] = {
            "portal_ready": ready,
            "onboarding_phase": phase,
            "onboarding_phase_label": onboarding_phase_label(phase),
            "onboarding_progress": int(steps_complete / len(steps) * 100),
            "owner_email": owner.email if owner else merchant.email,
            "owner_invite_status": owner_invite,
            "owner_clerk_linked": owner_linked,
            "owner_active": user_active,
            "team_count": len(users),
            "blockers_count": 0 if ready else len(steps) - steps_complete,
            "can_approve": merchant.status
            not in (MerchantStatus.ACTIVE.value, MerchantStatus.SUSPENDED.value),
            "can_invite_owner": not owner
            or owner_invite in ("not_invited", "invite_failed", "revoked")
            or not owner_linked,
            "can_activate_user": bool(owner and not owner.is_active),
        }
    return result


def stats_payload(db: Session, *, outstanding: int) -> dict:
    total = db.query(func.count(Merchant.id)).scalar() or 0
    active = db.query(func.count(Merchant.id)).filter(Merchant.status == "ACTIVE").scalar() or 0
    pending = db.query(func.count(Merchant.id)).filter(Merchant.status == "PENDING").scalar() or 0
    suspended = db.query(func.count(Merchant.id)).filter(Merchant.status == "SUSPENDED").scalar() or 0
    cutoff = _now() - timedelta(days=30)
    monthly_revenue = (
        db.query(func.coalesce(func.sum(Order.amount_cents), 0))
        .filter(
            Order.is_sandbox.is_(False),
            Order.merchant_id.isnot(None),
            Order.created_at >= cutoff,
        )
        .scalar()
        or 0
    )
    onboarding_pending = (
        db.query(func.count(Merchant.id))
        .filter(Merchant.status.in_([MerchantStatus.PENDING.value, MerchantStatus.ONBOARDING.value]))
        .scalar()
        or 0
    )
    return {
        "total": total,
        "active": active,
        "pending": pending,
        "suspended": suspended,
        "onboarding_pending": int(onboarding_pending),
        "monthly_revenue_cents": int(monthly_revenue),
        "outstanding_balance_cents": int(outstanding),
    }


def detail_payload(
    svc: Any,
    db: Session,
    merchant: Merchant,
    *,
    tax_legal: dict[str, Any],
    extra: dict[str, Any],
    coverage: dict[str, Any],
    website: str | None,
    flags: dict[str, bool] | None = None,
) -> dict[str, Any]:
    merchant_id = merchant.id
    company = svc._linked_company(db, merchant_id)
    metrics = svc._metrics(db, merchant, company)
    health = svc._health(merchant, metrics)
    # Heuristic only on this GET — NIM paraphrase is 12s×retries and trips the
    # admin 15s fetch abort (`porterchain_api_timeout` / endless Loading merchant).
    ai = svc._ai_insights(merchant, company, metrics, health, db=None, flags=flags)
    row = svc._row(db, merchant, light=False)
    row.update(
        {
            "hst_number": tax_legal["hst_number"],
            "business_number": tax_legal["business_number"],
            "tax_exempt": tax_legal["tax_exempt"],
            "tax_region": tax_legal["tax_region"],
            "tax_legal_meta": tax_legal["tax_legal_meta"],
            "identity_meta": extra.get("identity_meta"),
            "credit_limit_cents": merchant.credit_limit_cents,
            "available_credit_cents": (
                max(0, int(merchant.credit_limit_cents) - int(metrics["outstanding_balance_cents"]))
                if merchant.credit_limit_cents and merchant.credit_limit_cents > 0
                else None
            ),
            "billing_cycle": merchant.billing_cycle or "MONTHLY",
            "billing_address": merchant.billing_address or {},
            "preferred_vehicles": merchant.preferred_vehicles or [],
            "delivery_zones": merchant.delivery_zones or [],
            "coverage": coverage,
            "pricing_config": merchant.pricing_config or {},
            "profile": merchant.profile or {},
            "stripe_enabled": bool(getattr(merchant, "stripe_enabled", False))
            or (
                isinstance(merchant.profile, dict)
                and bool((merchant.profile or {}).get("stripe_enabled"))
            ),
            "cod_enabled": bool(getattr(merchant, "cod_enabled", False)),
            "stripe_connect_account_id": getattr(merchant, "stripe_connect_account_id", None),
            "documents": list(
                ((merchant.profile or {}).get("settings") or {}).get("documents") or []
            )
            if isinstance(merchant.profile, dict)
            and isinstance((merchant.profile or {}).get("settings") or {}, dict)
            else [],
            "activated_at": merchant.activated_at,
            "website": website or (company.website if company else None),
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


def locations_payload(db: Session, merchant_id: str) -> dict:
    addresses = db.query(SavedAddress).filter(SavedAddress.merchant_id == merchant_id).all()
    recipients = db.query(MerchantRecipient).filter(MerchantRecipient.merchant_id == merchant_id).all()
    return {
        "addresses": [
            {
                "id": a.id,
                "label": a.label,
                "address_type": a.address_type,
                "formatted": a.formatted,
                "postal": a.postal,
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


def onboarding_payload(db: Session, merchant: Merchant) -> dict[str, Any]:
    users = db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant.id).all()
    invitations = _latest_invitations(db, "merchant")
    owner = next((u for u in users if u.role == MerchantRole.OWNER.value), None)
    if not owner and users:
        owner = users[0]

    owner_invite = (
        _invite_status(invitations.get(owner.email.lower()), owner.clerk_user_id) if owner else "not_invited"
    )
    owner_linked = _clerk_linked(owner.clerk_user_id) if owner else False
    merchant_active = merchant.status == MerchantStatus.ACTIVE.value
    company_ready = bool(merchant.company_name and merchant.email)
    owner_provisioned = owner is not None

    steps = [
        {
            "id": "owner_provisioned",
            "label": "Owner user provisioned",
            "complete": owner_provisioned,
        },
        {
            "id": "owner_seat",
            "label": "Owner seat reserved",
            "complete": owner_provisioned and owner_invite != "not_invited",
        },
        {
            "id": "clerk_activated",
            "label": "Owner signed in (Clerk linked)",
            "complete": owner_linked,
        },
        {
            "id": "admin_approved",
            "label": "Merchant approved (portal access)",
            "complete": merchant_active,
        },
        {
            "id": "company_profile",
            "label": "Company profile on file",
            "complete": company_ready,
        },
    ]
    blockers = [s["id"] for s in steps if not s["complete"]]
    if merchant.status == MerchantStatus.SUSPENDED.value:
        blockers = ["account_suspended"]
    elif merchant.status == MerchantStatus.CLOSED.value:
        blockers = ["account_closed"]

    return {
        "merchant_id": merchant.id,
        "merchant_status": merchant.status,
        "merchant_status_label": merchant_status_label(merchant.status),
        "company_name": merchant.company_name,
        "company_email": merchant.email,
        "owner_email": owner.email if owner else merchant.email,
        "owner_invite_status": owner_invite,
        "owner_invite_status_label": invite_status_label(owner_invite),
        "owner_clerk_linked": owner_linked,
        "team_count": len(users),
        "steps": steps,
        "blockers": blockers,
        "ready": len(blockers) == 0,
        "can_approve": merchant.status
        not in (
            MerchantStatus.ACTIVE.value,
            MerchantStatus.SUSPENDED.value,
            MerchantStatus.CLOSED.value,
        ),
        "can_invite_owner": not owner_linked or owner_invite in ("not_invited", "invite_failed", "revoked"),
    }


def _key_expired(key: MerchantApiKey) -> bool:
    from datetime import UTC, datetime

    exp = getattr(key, "expires_at", None)
    if exp is None:
        return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    return exp <= datetime.now(UTC)


def api_keys_payload(db: Session, merchant_id: str) -> dict:
    """Integrations health for admin merchant 360 — mirrors merchant portal overview.

    Mint/connect stay merchant-owned; this payload is read + ops (revoke/RPM/disable).
    """
    from datetime import UTC, datetime, timedelta

    from porterchain_api.booking_models import Order
    from porterchain_api.config import get_settings
    from porterchain_api.domain.states import OrderSource
    from porterchain_api.gateway_engine import merchant_api as gateway
    from porterchain_api.merchant_engine.shopify_health import DLQ_WAITING, shop_health
    from porterchain_api.merchant_engine.shopify_service import default_pickup_address
    from porterchain_api.merchant_engine.shopify_urls import (
        carrier_rates_url,
        fulfillment_callback_prefix,
        fulfillment_service_url,
        webhook_url,
    )
    from porterchain_api.merchant_models import (
        MerchantAuditLog,
        MerchantWebhookDelivery,
        ShopifyRateQuote,
    )

    settings = get_settings()
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    keys = db.query(MerchantApiKey).filter(MerchantApiKey.merchant_id == merchant_id).all()
    hooks = db.query(MerchantWebhook).filter(MerchantWebhook.merchant_id == merchant_id).all()
    shops = (
        db.query(ShopifyShop)
        .filter(ShopifyShop.merchant_id == merchant_id)
        .order_by(ShopifyShop.created_at.desc())
        .all()
    )
    usage = gateway.usage_summary(db, merchant_id)
    limits = gateway.rate_limits_for_merchant(db, merchant_id)
    delivery_rows = (
        db.query(MerchantWebhookDelivery)
        .filter(MerchantWebhookDelivery.merchant_id == merchant_id)
        .order_by(MerchantWebhookDelivery.created_at.desc())
        .limit(10)
        .all()
    )

    def _delivery(row: MerchantWebhookDelivery) -> dict[str, Any]:
        return {
            "id": row.id,
            "webhook_id": row.webhook_id,
            "event_type": row.event_type,
            "response_status": row.response_status,
            "success": row.success,
            "attempt": row.attempt,
            "error_message": row.error_message,
            "duration_ms": row.duration_ms,
            "next_retry_at": row.next_retry_at.isoformat() if row.next_retry_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    shopify_shops: list[dict[str, Any]] = []
    for shop in shops:
        pickup = default_pickup_address(db, merchant_id, shop=shop)
        health = shop_health(db, shop, settings, pickup_set=pickup is not None)
        installed = health["connected"]  # was uninstalled_at only; merchant view also needs a token
        shopify_shops.append(
            {
                "id": shop.id,
                "shop_domain": shop.shop_domain,
                "installed": installed,
                "installed_at": shop.installed_at.isoformat() if shop.installed_at else None,
                "last_webhook_at": shop.last_webhook_at.isoformat() if shop.last_webhook_at else None,
                "default_pickup": pickup.formatted if pickup else None,
                "default_pickup_address_id": shop.default_pickup_address_id,
                "missing_pickup": installed and pickup is None,
                "carrier_registered": bool(shop.carrier_service_gid),
                "fulfillment_service_registered": bool(shop.fulfillment_service_gid),
                "ingress_paused": bool(getattr(shop, "ingress_paused", False)),
                "auto_dispatch": bool(getattr(shop, "auto_dispatch", False)),
                "default_vehicle_class": getattr(shop, "default_vehicle_class", None),
                "default_package_type": getattr(shop, "default_package_type", None),
                "health": health,
            }
        )

    audit_actions = (
        "api_key.",
        "webhook.",
        "shopify.",
        "partner_api.",
    )
    # Filter in SQL: a busy account (pricing/credit edits) used to push every
    # integration event out of a 40-row window, so the log looked empty.
    from sqlalchemy import or_

    audit_rows = (
        db.query(MerchantAuditLog)
        .filter(
            MerchantAuditLog.merchant_id == merchant_id,
            or_(*[MerchantAuditLog.action.like(f"{p}%") for p in audit_actions]),
        )
        .order_by(MerchantAuditLog.created_at.desc())
        .limit(20)
        .all()
    )
    audit_events = [
        {
            "id": row.id,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "actor_user_id": row.actor_user_id,
            "payload": row.payload or {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in audit_rows
        if any(row.action.startswith(prefix) for prefix in audit_actions)
    ][:20]

    last_quote = (
        db.query(ShopifyRateQuote)
        .filter(ShopifyRateQuote.merchant_id == merchant_id)
        .order_by(ShopifyRateQuote.created_at.desc())
        .first()
    )
    since_24h = datetime.now(UTC) - timedelta(hours=24)
    quotes_24h = (
        db.query(ShopifyRateQuote)
        .filter(
            ShopifyRateQuote.merchant_id == merchant_id,
            ShopifyRateQuote.created_at >= since_24h,
        )
        .count()
    )
    last_book = (
        db.query(Order)
        .filter(
            Order.merchant_id == merchant_id,
            Order.order_source == OrderSource.SHOPIFY.value,
        )
        .order_by(Order.created_at.desc())
        .first()
    )
    last_fulfill_meta: dict[str, Any] | None = None
    last_fulfill_at: str | None = None
    if last_book:
        shopify_meta = ((last_book.compliance_metadata or {}).get("shopify") or {})
        if shopify_meta.get("fulfillment_id"):
            last_fulfill_meta = {
                "order_id": last_book.id,
                "fulfillment_id": str(shopify_meta.get("fulfillment_id")),
                "rate_quote_id": shopify_meta.get("rate_quote_id"),
                "rate_quote_cents": shopify_meta.get("rate_quote_cents"),
                "last_tracking_push_at": shopify_meta.get("last_tracking_push_at"),
                "last_tracking_state": shopify_meta.get("last_tracking_state"),
                "last_event_status": shopify_meta.get("last_event_status"),
                "last_event_at": shopify_meta.get("last_event_at"),
            }
            last_fulfill_at = last_book.updated_at.isoformat() if getattr(last_book, "updated_at", None) else None
    if not last_fulfill_meta:
        fulfill_orders = (
            db.query(Order)
            .filter(
                Order.merchant_id == merchant_id,
                Order.order_source == OrderSource.SHOPIFY.value,
            )
            .order_by(Order.created_at.desc())
            .limit(25)
            .all()
        )
        for order in fulfill_orders:
            meta = ((order.compliance_metadata or {}).get("shopify") or {})
            if meta.get("fulfillment_id"):
                last_fulfill_meta = {
                    "order_id": order.id,
                    "fulfillment_id": str(meta.get("fulfillment_id")),
                    "rate_quote_id": meta.get("rate_quote_id"),
                    "rate_quote_cents": meta.get("rate_quote_cents"),
                    "last_tracking_push_at": meta.get("last_tracking_push_at"),
                    "last_tracking_state": meta.get("last_tracking_state"),
                    "last_event_status": meta.get("last_event_status"),
                    "last_event_at": meta.get("last_event_at"),
                }
                last_fulfill_at = order.updated_at.isoformat() if getattr(order, "updated_at", None) else (
                    order.created_at.isoformat() if order.created_at else None
                )
                break

    quote_book_locked = False
    if last_book:
        book_meta = ((last_book.compliance_metadata or {}).get("shopify") or {})
        quote_book_locked = bool(book_meta.get("rate_quote_id"))

    from porterchain_api.merchant_models import ShopifyIngressDlq

    dlq_open = (
        db.query(ShopifyIngressDlq)
        .filter(
            ShopifyIngressDlq.merchant_id == merchant_id,
            ShopifyIngressDlq.status.in_(DLQ_WAITING),
        )
        .count()
    )

    shopify_partner = {
        "carrier_rates_url": carrier_rates_url(settings),
        "last_rate_quote_at": last_quote.created_at.isoformat() if last_quote and last_quote.created_at else None,
        "last_rate_quote_cents": last_quote.total_cents if last_quote else None,
        "rate_quotes_24h": quotes_24h,
        "last_book_at": last_book.created_at.isoformat() if last_book and last_book.created_at else None,
        "last_book_order_id": last_book.id if last_book else None,
        "last_fulfillment_at": last_fulfill_at,
        "last_fulfillment": last_fulfill_meta,
        "quote_book_locked": quote_book_locked,
        "oauth_configured": bool(settings.shopify_api_key and settings.shopify_api_secret),
        # Real signal, not a constant: did we push tracking to Shopify for the latest fulfilled order?
        "mid_flight_tracking": bool(last_fulfill_meta and last_fulfill_meta.get("last_tracking_push_at")),
        "fo_partner_path": (
            "flag_on" if settings.shopify_fulfillment_service_enabled else "flag_off"
        ),
        "fulfillment_service_url": fulfillment_service_url(settings),
        "fulfillment_callback_url": fulfillment_callback_prefix(settings),
        "fulfillment_service_enabled": bool(settings.shopify_fulfillment_service_enabled),
        "ingress_dlq_open": dlq_open,
    }

    return {
        "api_keys": [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "environment": k.environment,
                "scopes": k.scopes or [],
                "rate_limit_per_minute": k.rate_limit_per_minute,
                # A rotated key past its grace window is dead even before its next auth attempt flips the flag.
                "is_active": bool(k.is_active) and not _key_expired(k),
                "expires_at": k.expires_at.isoformat() if getattr(k, "expires_at", None) else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ],
        "webhooks": [
            {
                "id": w.id,
                "url": w.url,
                "events": w.events or [],
                "environment": w.environment or "production",
                "is_active": w.is_active,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in hooks
        ],
        "shopify_shops": shopify_shops,
        "shopify_connected": any(s["installed"] for s in shopify_shops),
        "shopify_webhook_url": webhook_url(settings),
        "sandbox_mode": gateway.sandbox_mode_enabled(merchant) if merchant else False,
        "booking_env_preference": gateway.booking_env_preference(merchant) if merchant else "live",
        "api_keys_count": len(keys),
        "active_keys": sum(1 for k in keys if k.is_active and not _key_expired(k)),
        "sandbox_keys": sum(1 for k in keys if k.environment == "sandbox"),
        "production_keys": sum(1 for k in keys if k.environment == "production"),
        "webhooks_count": len(hooks),
        "active_webhooks": sum(1 for h in hooks if h.is_active),
        "usage": usage,
        "rate_limits": limits,
        "recent_webhook_deliveries": [_delivery(r) for r in delivery_rows],
        "health": {
            "failed_deliveries_recent": sum(1 for r in delivery_rows if not r.success),
            "throttled_keys": sum(1 for row in limits if row.get("throttled")),
        },
        "audit_events": audit_events,
        "shopify_partner": shopify_partner,
        "available_integrations": ["shopify", "merchant-api"],
    }


def analytics_payload(db: Session, merchant_id: str) -> dict:
    orders = (
        db.query(Order)
        .filter(Order.merchant_id == merchant_id, Order.is_sandbox.is_(False))
        .all()
    )
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


def timeline_payload(db: Session, merchant_id: str, company_id: str | None) -> list[dict]:
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
        db.query(Order)
        .filter(Order.merchant_id == merchant_id, Order.is_sandbox.is_(False))
        .order_by(Order.created_at.desc())
        .limit(25)
        .all()
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
    invs = (
        db.query(Invoice, Order)
        .join(Order, Invoice.order_id == Order.id)
        .filter(Order.merchant_id == merchant_id, Order.is_sandbox.is_(False))
        .order_by(Invoice.created_at.desc())
        .limit(25)
        .all()
    )
    for inv, order in invs:
        amount = f"${(inv.amount_cents or 0) / 100:.2f}"
        events.append(
            {
                "kind": "invoice",
                "type": "ops",
                "title": f"Invoice {inv.invoice_number} · {amount} · {order.order_number}",
                "at": inv.created_at.isoformat() if inv.created_at else None,
            }
        )
    events.sort(key=lambda e: e["at"] or "", reverse=True)
    return events[:80]
