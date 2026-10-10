"""Connections watchdog: one status light per connection and the one-click fixes.

* Shopify: install, token, granted scopes vs required, CarrierService,
  fulfillment service, last webhook, open DLQ rows. Fixes: re-register
  (existing), backfill pending fulfillment requests, replay DLQ (existing).
* API keys: active / expiring / unused. Fix: rotate with a grace window.
* Webhooks: failures in 24 h. Fix: replay every failed delivery in a window.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_models import (
    MerchantApiKey,
    MerchantWebhook,
    MerchantWebhookDelivery,
    ShopifyShop,
)

MAX_ROTATE_GRACE_DAYS = 30
MAX_REPLAY = 200


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _scope_set(raw: str | None) -> set[str]:
    return {p.strip() for p in str(raw or "").split(",") if p.strip()}


def missing_scopes(granted: str | None, required: str) -> list[str]:
    """Required scopes not granted. A write_X grant implies read_X (Shopify rule)."""
    from porterchain_api.merchant_engine.shopify_health import (
        missing_scopes as _missing,
    )

    return _missing(granted, required)


def _light(problems: list[str], warnings: list[str]) -> str:
    return "red" if problems else ("amber" if warnings else "green")


def shopify_status(db: Session, shop: ShopifyShop, settings: Any, *, now: datetime) -> dict[str, Any]:
    """Watchdog row built from the shared shop health, so admin and merchant agree."""
    from porterchain_api.merchant_engine.shopify_health import shop_health

    health = shop_health(db, shop, settings, now=now)
    problems = [p["text"] for p in health["problems"]]
    warnings: list[str] = []
    refresh_exp = _aware(shop.refresh_token_expires_at)
    if health["connected"] and refresh_exp and refresh_exp - now < timedelta(days=14):
        warnings.append("Shopify access needs renewing within 14 days")
    if not problems and health["light"] == "amber":
        warnings.append(health["reason"])
    fixes = ["backfill", "reregister"] if health["connected"] else []
    if health["orders_waiting"]:
        fixes.append("replay_dlq")
    return {
        "kind": "shopify",
        "id": shop.id,
        "name": shop.shop_domain,
        "light": _light(problems, warnings),
        "problems": problems,
        "warnings": warnings,
        "missing_scopes": health["missing_scopes"],
        "granted_scopes": sorted(_scope_set(shop.scopes)),
        "last_webhook_at": health["last_order_at"],
        "dlq_open": health["orders_waiting"],
        "health": health,
        "fixes": fixes,
    }


def watchdog(db: Session, merchant_id: str, settings: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    items: list[dict[str, Any]] = []
    for shop in db.query(ShopifyShop).filter(ShopifyShop.merchant_id == merchant_id).all():
        items.append(shopify_status(db, shop, settings, now=now))

    keys = db.query(MerchantApiKey).filter(MerchantApiKey.merchant_id == merchant_id).all()
    for key in keys:
        if not key.is_active:
            continue
        problems: list[str] = []
        warnings: list[str] = []
        exp = _aware(key.expires_at)
        if exp and exp <= now:
            problems.append("Expired")
        elif exp:
            warnings.append(f"Retires {exp.date().isoformat()} (rotated)")
        last_used = _aware(key.last_used_at)
        created = _aware(key.created_at)
        if key.environment == "production" and created and now - created > timedelta(days=365):
            warnings.append("Older than 12 months: rotate")
        if last_used is None and created and now - created > timedelta(days=30):
            warnings.append("Never used")
        items.append(
            {
                "kind": "api_key",
                "id": key.id,
                "name": f"{key.name} ({key.key_prefix}…)",
                "environment": key.environment,
                "light": _light(problems, warnings),
                "problems": problems,
                "warnings": warnings,
                "last_used_at": last_used.isoformat() if last_used else None,
                "fixes": ["rotate"],
            }
        )

    since = now - timedelta(hours=24)
    for hook in db.query(MerchantWebhook).filter(MerchantWebhook.merchant_id == merchant_id).all():
        q = db.query(MerchantWebhookDelivery).filter(
            MerchantWebhookDelivery.webhook_id == hook.id, MerchantWebhookDelivery.created_at >= since
        )
        total = q.count()
        failed = q.filter(MerchantWebhookDelivery.success.is_(False)).count()
        problems, warnings = [], []
        if not hook.is_active:
            warnings.append("Disabled")
        if total and failed * 2 >= total and failed >= 3:
            problems.append(f"{failed} of {total} deliveries failed (24h)")
        elif failed:
            warnings.append(f"{failed} failed deliveries (24h)")
        items.append(
            {
                "kind": "webhook",
                "id": hook.id,
                "name": hook.url,
                "environment": hook.environment,
                "light": _light(problems, warnings),
                "problems": problems,
                "warnings": warnings,
                "deliveries_24h": total,
                "failed_24h": failed,
                "fixes": ["replay_failed"] if failed else [],
            }
        )

    order = {"red": 0, "amber": 1, "green": 2}
    items.sort(key=lambda i: order.get(i["light"], 3))
    overall = items[0]["light"] if items else "none"
    return {"light": overall, "items": items, "checked_at": now.isoformat()}


def rotate_api_key(
    db: Session, ctx: Any, merchant_id: str, key_id: str, *, grace_days: int, reason: str | None
) -> dict[str, Any]:
    """Mint a successor key; the old one keeps working for ``grace_days`` then retires.

    Elevated (super admin / compliance): the new secret is shown once to the
    operator, who hands it to the merchant over a secure channel. The secret is
    never stored or logged; only its hash and prefix are kept.
    """
    from porterchain_api.merchant_engine.account_ops import staff_audit

    # Elevated gate (super admin / compliance) is enforced by the admin router.
    note = (reason or "").strip()
    if not note:
        raise ValueError("reason_required")
    if grace_days < 0 or grace_days > MAX_ROTATE_GRACE_DAYS:
        raise ValueError("grace_days_invalid")
    old = (
        db.query(MerchantApiKey)
        .filter(MerchantApiKey.id == key_id, MerchantApiKey.merchant_id == merchant_id)
        .first()
    )
    if not old:
        raise LookupError("api_key_not_found")
    if not old.is_active:
        raise ValueError("api_key_inactive")
    now = datetime.now(UTC)
    raw = f"pk_{old.environment}_{secrets.token_urlsafe(32)}"
    new = MerchantApiKey(
        merchant_id=merchant_id,
        name=old.name,
        key_prefix=raw[:12],
        key_hash=hashlib.sha256(raw.encode()).hexdigest(),
        scopes=list(old.scopes or []),
        environment=old.environment,
        rate_limit_per_minute=old.rate_limit_per_minute,
        rotated_from_id=old.id,
    )
    db.add(new)
    if grace_days == 0:
        old.is_active = False
        old.expires_at = now
    else:
        old.expires_at = now + timedelta(days=grace_days)
    db.flush()
    staff_audit(
        db,
        ctx,
        merchant_id,
        action="api_key.rotated",
        resource_type="api_key",
        resource_id=new.id,
        payload={
            "reason": note,
            "changes": {
                "old_key": {"old": old.key_prefix, "new": f"retires {old.expires_at.isoformat()}"},
                "new_key": {"old": None, "new": new.key_prefix},
            },
        },
    )
    return {
        "key_id": new.id,
        "key_prefix": new.key_prefix,
        "secret": raw,
        "old_key_id": old.id,
        "old_key_retires_at": old.expires_at.isoformat() if old.expires_at else None,
    }


def replay_failed_webhooks(
    db: Session,
    ctx: Any,
    mctx: Any,
    settings: Any,
    *,
    hours: int = 24,
    webhook_id: str | None = None,
) -> dict[str, Any]:
    """Re-send the latest failed attempt of each event in the window (oldest first).

    ``mctx`` is the merchant seat; the admin router builds it (admin_merchant_context).
    """
    from porterchain_api.merchant_engine.account_ops import staff_audit

    merchant_id = mctx.merchant.id
    from porterchain_api.merchant_engine.integrations_service import (
        MerchantIntegrationsService,
    )

    hours = max(1, min(int(hours), 24 * 7))
    since = datetime.now(UTC) - timedelta(hours=hours)
    q = db.query(MerchantWebhookDelivery).filter(
        MerchantWebhookDelivery.merchant_id == merchant_id,
        MerchantWebhookDelivery.created_at >= since,
    )
    if webhook_id:
        q = q.filter(MerchantWebhookDelivery.webhook_id == webhook_id)
    rows = q.order_by(MerchantWebhookDelivery.created_at.asc()).all()
    # Latest attempt per (webhook, event body): a later success means nothing to replay.
    latest: dict[tuple[str, str], MerchantWebhookDelivery] = {}
    for row in rows:
        body_key = hashlib.sha256(repr(sorted((row.request_body or {}).items())).encode()).hexdigest()
        latest[(row.webhook_id, body_key)] = row
    failed = [r for r in latest.values() if not r.success][:MAX_REPLAY]
    if not failed:
        return {"replayed": 0, "succeeded": 0, "failed": 0}
    svc = MerchantIntegrationsService()
    ok = bad = 0
    for row in failed:
        try:
            res = svc.retry_delivery(db, mctx, row.id, encryption_key=settings.jwt_secret)
            if isinstance(res, dict) and res.get("success"):
                ok += 1
            else:
                bad += 1
        except (LookupError, ValueError, RuntimeError):
            bad += 1
    staff_audit(
        db,
        ctx,
        merchant_id,
        action="webhook.bulk_replay",
        resource_type="api_key",
        resource_id=webhook_id,
        payload={"hours": hours, "replayed": len(failed), "succeeded": ok, "failed": bad},
    )
    return {"replayed": len(failed), "succeeded": ok, "failed": bad}


def backfill_shopify(db: Session, ctx: Any, merchant_id: str, shop_id: str, settings: Any) -> dict[str, Any]:
    """Re-poll fulfillment requests Shopify assigned to us and book any we missed.

    Booking is idempotent per Shopify order, so already-booked orders are skipped.
    """
    from porterchain_api.merchant_engine.account_ops import get_merchant, staff_audit
    from porterchain_api.merchant_engine.shopify_fulfillment_ops import (
        _act_on_fulfillment_requests,
    )
    from porterchain_api.merchant_engine.shopify_tokens import access_token_for

    get_merchant(db, merchant_id)
    shop = (
        db.query(ShopifyShop).filter(ShopifyShop.id == shop_id, ShopifyShop.merchant_id == merchant_id).first()
    )
    if not shop:
        raise LookupError("shop_not_found")
    if shop.uninstalled_at is not None:
        raise ValueError("shop_not_connected")
    if shop.ingress_paused:
        raise ValueError("ingress_paused")
    token = access_token_for(shop, settings)
    if not token:
        raise ValueError("missing_access_token")
    result = _act_on_fulfillment_requests(db, settings, shop, token)
    staff_audit(
        db,
        ctx,
        merchant_id,
        action="shopify.backfill",
        resource_type="shopify_shop",
        resource_id=shop_id,
        payload={"result": result},
    )
    return result
