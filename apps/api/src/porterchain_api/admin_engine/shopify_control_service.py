"""Admin Shopify control-plane ops — pause, policy, DLQ replay, release, re-push."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine.order_transitions import transition_to_dispatch_ready
from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_models import ShopifyIngressDlq, ShopifyShop

logger = logging.getLogger(__name__)


def _require_shop(db: Session, merchant_id: str, shop_id: str) -> ShopifyShop:
    shop = (
        db.query(ShopifyShop)
        .filter(ShopifyShop.id == shop_id, ShopifyShop.merchant_id == merchant_id)
        .first()
    )
    if not shop:
        raise LookupError("shop_not_found")
    return shop


def set_ingress_paused(
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    shop_id: str,
    *,
    paused: bool,
    reason: str | None = None,
) -> dict[str, Any]:
    from porterchain_api.admin_engine.merchant_org import (
        require_integrations_elevated,
        require_merchant,
        write_staff_audit,
    )

    require_integrations_elevated(ctx)
    require_merchant(db, merchant_id)
    note = (reason or "").strip()
    if not note:
        raise ValueError("reason_required")
    shop = _require_shop(db, merchant_id, shop_id)
    shop.ingress_paused = bool(paused)
    db.commit()
    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="shopify.ingress_paused" if paused else "shopify.ingress_resumed",
        resource_type="shopify_shop",
        resource_id=shop_id,
        payload={"reason": note, "ingress_paused": bool(paused), "shop_domain": shop.shop_domain},
    )
    return {
        "shop_id": shop.id,
        "shop_domain": shop.shop_domain,
        "ingress_paused": shop.ingress_paused,
    }


def set_auto_dispatch(
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    shop_id: str,
    *,
    enabled: bool,
    reason: str | None = None,
) -> dict[str, Any]:
    from porterchain_api.admin_engine.merchant_org import (
        require_integrations_elevated,
        require_merchant,
        write_staff_audit,
    )

    require_integrations_elevated(ctx)
    require_merchant(db, merchant_id)
    note = (reason or "").strip()
    if not note:
        raise ValueError("reason_required")
    shop = _require_shop(db, merchant_id, shop_id)
    shop.auto_dispatch = bool(enabled)
    db.commit()
    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="shopify.auto_dispatch_set",
        resource_type="shopify_shop",
        resource_id=shop_id,
        payload={"reason": note, "auto_dispatch": bool(enabled), "shop_domain": shop.shop_domain},
    )
    return {
        "shop_id": shop.id,
        "shop_domain": shop.shop_domain,
        "auto_dispatch": shop.auto_dispatch,
    }


def set_booking_policy(
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    shop_id: str,
    *,
    default_vehicle_class: str | None = None,
    default_package_type: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    from porterchain_api.admin_engine.merchant_org import (
        require_integrations_elevated,
        require_merchant,
        write_staff_audit,
    )
    from porterchain_api.domain.catalog_labels import PACKAGE_LABELS, VEHICLE_LABELS

    require_integrations_elevated(ctx)
    require_merchant(db, merchant_id)
    note = (reason or "").strip()
    if not note:
        raise ValueError("reason_required")
    shop = _require_shop(db, merchant_id, shop_id)
    if default_vehicle_class is not None:
        from porterchain_api.domain.customer_goods import CATALOG_VEHICLE_IDS, persist_vehicle_class

        if not (default_vehicle_class or "").strip():
            shop.default_vehicle_class = None
        else:
            vc = persist_vehicle_class(default_vehicle_class)
            if vc not in CATALOG_VEHICLE_IDS:
                raise ValueError("vehicle_class_invalid")
            shop.default_vehicle_class = vc
    if default_package_type is not None:
        pt = (default_package_type or "").strip()
        if pt and pt not in PACKAGE_LABELS:
            raise ValueError("package_type_invalid")
        shop.default_package_type = pt or None
    db.commit()
    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="shopify.booking_policy_set",
        resource_type="shopify_shop",
        resource_id=shop_id,
        payload={
            "reason": note,
            "default_vehicle_class": shop.default_vehicle_class,
            "default_package_type": shop.default_package_type,
            "shop_domain": shop.shop_domain,
        },
    )
    return {
        "shop_id": shop.id,
        "shop_domain": shop.shop_domain,
        "default_vehicle_class": shop.default_vehicle_class,
        "default_package_type": shop.default_package_type,
    }


def reregister_shop_hooks(
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    shop_id: str,
    settings: Settings,
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    from porterchain_api.admin_engine.merchant_org import (
        require_integrations_elevated,
        require_merchant,
        write_staff_audit,
    )
    from porterchain_api.merchant_engine.shopify_fulfillment_service import re_register_shop_hooks

    require_integrations_elevated(ctx)
    require_merchant(db, merchant_id)
    note = (reason or "").strip()
    if not note:
        raise ValueError("reason_required")
    shop = _require_shop(db, merchant_id, shop_id)
    if shop.uninstalled_at is not None:
        raise ValueError("shop_not_connected")
    result = re_register_shop_hooks(shop, settings)
    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="shopify.hooks_reregistered",
        resource_type="shopify_shop",
        resource_id=shop_id,
        payload={"reason": note, "result": result},
    )
    if not result.get("ok"):
        raise RuntimeError("shopify_reregister_failed:" + ",".join(result.get("errors") or []))
    return result


def list_merchant_ingress_dlq(
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    *,
    status: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    from porterchain_api.admin_engine.merchant_org import require_merchant
    from porterchain_api.merchant_engine.shopify_ingress_dlq import dlq_row_payload, list_ingress_dlq

    require_merchant(db, merchant_id)
    rows = list_ingress_dlq(db, merchant_id, status=status, limit=limit)
    return {"items": [dlq_row_payload(r) for r in rows], "count": len(rows)}


def replay_ingress_dlq(
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    dlq_id: str,
    settings: Settings,
) -> dict[str, Any]:
    from porterchain_api.admin_engine.merchant_org import require_merchant, write_staff_audit
    from porterchain_api.merchant_engine.shopify_ingress_dlq import mark_dlq_resolved
    from porterchain_api.merchant_engine.shopify_service import process_queued_webhook

    require_merchant(db, merchant_id)
    row = (
        db.query(ShopifyIngressDlq)
        .filter(ShopifyIngressDlq.id == dlq_id, ShopifyIngressDlq.merchant_id == merchant_id)
        .first()
    )
    if not row:
        raise LookupError("dlq_not_found")
    if row.status == "resolved":
        return {
            "ok": True,
            "replayed": False,
            "already_resolved": True,
            "dlq_id": row.id,
            "porterchain_order_id": row.porterchain_order_id,
        }

    shop = (
        db.query(ShopifyShop).filter(ShopifyShop.id == row.shop_id).first() if row.shop_id else None
    )
    if shop and shop.ingress_paused and row.action == "shopify_orders_create":
        raise RuntimeError("ingress_still_paused")

    row.attempts = int(row.attempts or 0) + 1
    db.commit()

    result = process_queued_webhook(
        db,
        settings,
        {
            "action": row.action,
            "shop_domain": row.shop_domain,
            "topic": row.topic or "",
            "raw_body": row.raw_body,
            "_from_dlq_replay": True,
        },
    )
    order_id = None
    if isinstance(result, dict):
        order_id = result.get("order_id")
        if result.get("skipped") == "ingress_paused":
            raise RuntimeError("ingress_still_paused")

    admin_id = getattr(getattr(ctx, "user", None), "id", None) or getattr(ctx, "admin_user_id", None)
    mark_dlq_resolved(
        db,
        row,
        admin_id=str(admin_id) if admin_id else None,
        porterchain_order_id=str(order_id) if order_id else None,
    )
    write_staff_audit(
        db,
        ctx,
        merchant_id,
        action="shopify.webhook_replayed",
        resource_type="shopify_ingress_dlq",
        resource_id=dlq_id,
        payload={
            "shop_domain": row.shop_domain,
            "shopify_order_id": row.shopify_order_id,
            "order_id": order_id,
            "result": {
                k: result.get(k)
                for k in ("ok", "order_id", "replayed", "skipped", "held_for_ops")
                if isinstance(result, dict)
            },
        },
    )
    return {"ok": True, "replayed": True, "dlq_id": row.id, "result": result}


def release_shopify_order_to_fleetbase(
    db: Session,
    ctx: AdminContext,
    order_id: str,
) -> dict[str, Any]:
    """BOOKED Shopify hold → DISPATCH_READY (Fleetbase sync follows)."""
    from porterchain_api.admin_engine.merchant_org import write_staff_audit

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise LookupError("order_not_found")
    if order.order_source != OrderSource.SHOPIFY.value:
        raise ValueError("not_shopify_order")
    if bool(getattr(order, "is_sandbox", False)):
        raise ValueError("sandbox_order_no_fleetbase")
    if order.state != OrderState.BOOKED.value:
        raise ValueError(f"order_not_held:{order.state}")

    admin_id = getattr(getattr(ctx, "user", None), "id", None) or getattr(ctx, "admin_user_id", None)
    transition_to_dispatch_ready(
        db,
        order,
        event_type="order.dispatch_ready",
        actor_type="admin",
        actor_id=str(admin_id) if admin_id else "admin",
    )
    extra = dict(order.compliance_metadata or {})
    shopify_meta = dict(extra.get("shopify") or {})
    shopify_meta["held_for_ops"] = False
    shopify_meta["released_at"] = datetime.now(UTC).isoformat()
    extra["shopify"] = shopify_meta
    order.compliance_metadata = extra
    db.commit()
    db.refresh(order)

    if order.merchant_id:
        write_staff_audit(
            db,
            ctx,
            order.merchant_id,
            action="shopify.order_released",
            resource_type="order",
            resource_id=order.id,
            payload={"state": order.state},
        )
    return {"ok": True, "order_id": order.id, "state": order.state}


def repush_shopify_fulfillment(
    db: Session,
    ctx: AdminContext,
    order_id: str,
    settings: Settings,
) -> dict[str, Any]:
    from porterchain_api.admin_engine.merchant_org import write_staff_audit
    from porterchain_api.merchant_engine.shopify_fulfillment_service import push_fulfillment

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise LookupError("order_not_found")
    if order.order_source != OrderSource.SHOPIFY.value:
        raise ValueError("not_shopify_order")

    try:
        push_fulfillment(db, settings, order)
        db.refresh(order)
        extra = dict(order.compliance_metadata or {})
        shopify_meta = dict(extra.get("shopify") or {})
        shopify_meta.pop("last_fulfillment_error", None)
        shopify_meta["last_repush_at"] = datetime.now(UTC).isoformat()
        extra["shopify"] = shopify_meta
        order.compliance_metadata = extra
        db.commit()
        db.refresh(order)
    except Exception as exc:  # noqa: BLE001
        extra = dict(order.compliance_metadata or {})
        shopify_meta = dict(extra.get("shopify") or {})
        shopify_meta["last_fulfillment_error"] = str(exc)[:2000]
        extra["shopify"] = shopify_meta
        order.compliance_metadata = extra
        db.commit()
        raise RuntimeError(f"fulfillment_repush_failed:{exc}") from exc

    meta = ((order.compliance_metadata or {}).get("shopify") or {})
    if order.merchant_id:
        write_staff_audit(
            db,
            ctx,
            order.merchant_id,
            action="shopify.fulfillment_repushed",
            resource_type="order",
            resource_id=order.id,
            payload={
                "fulfillment_id": meta.get("fulfillment_id"),
                "last_tracking_state": meta.get("last_tracking_state"),
            },
        )
    return {
        "ok": True,
        "order_id": order.id,
        "fulfillment_id": meta.get("fulfillment_id"),
        "last_tracking_push_at": meta.get("last_tracking_push_at"),
        "last_tracking_state": meta.get("last_tracking_state"),
    }
