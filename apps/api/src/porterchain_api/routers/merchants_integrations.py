"""Admin merchant Integrations ops — thin routes (M1–M7 + Kaylulu pricing + Shopify control)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.merchant_org import (
    activate_webhook,
    apply_kaylulu_pricing_template,
    clone_pricing_from,
    deactivate_webhook,
    force_disconnect_shopify,
    freeze_partner_api,
    org_error_message,
    revoke_api_key,
    shopify_install_url_for,
    test_webhook,
)
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.admin_engine.shopify_control_service import (
    list_merchant_ingress_dlq,
    replay_ingress_dlq,
    reregister_shop_hooks,
    set_auto_dispatch,
    set_booking_policy,
    set_ingress_paused,
)
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas_admin import MerchantPricingResponse

router = APIRouter(prefix="/v1/admin/merchants", tags=["merchants"])
Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _invoke(ctx: AdminContext, module: str, fn, *args, org=False, copy=None, **kwargs):
    from fastapi import HTTPException

    from porterchain_api.admin_engine.merchant_org import raise_org_http

    try:
        require_module(ctx, module)
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        if org:
            raise_org_http(exc)
            raise
        detail = str(exc) or "merchant_not_found"
        raise HTTPException(status_code=404, detail=copy(detail) if copy else detail) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        if str(exc) == "clerk_not_configured":
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if org:
            raise_org_http(exc)
            raise
        detail = str(exc)
        raise HTTPException(status_code=400, detail=copy(detail) if copy else detail) from exc


@router.post("/{merchant_id}/pricing/apply-kaylulu", response_model=MerchantPricingResponse)
def apply_merchant_kaylulu_pricing(
    merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> MerchantPricingResponse:
    view = _invoke(
        ctx, "merchants", apply_kaylulu_pricing_template, db, ctx, merchant_id, org=True, copy=org_error_message
    )
    return MerchantPricingResponse(**{k: v for k, v in view.items() if k != "clone"})


@router.post("/{merchant_id}/pricing/clone-from/{source_merchant_id}", response_model=MerchantPricingResponse)
def clone_merchant_pricing(
    merchant_id: str,
    source_merchant_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    include_fsa: bool = Query(False),
) -> MerchantPricingResponse:
    view = _invoke(
        ctx,
        "merchants",
        clone_pricing_from,
        db,
        ctx,
        merchant_id,
        source_merchant_id,
        include_fsa=include_fsa,
        org=True,
        copy=org_error_message,
    )
    return MerchantPricingResponse(**{k: v for k, v in view.items() if k != "clone"})


@router.delete("/{merchant_id}/api-keys/{key_id}", status_code=204)
def revoke_merchant_api_key(
    merchant_id: str, key_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> None:
    _invoke(ctx, "merchants", revoke_api_key, db, ctx, merchant_id, key_id, org=True)


@router.delete("/{merchant_id}/webhooks/{webhook_id}", status_code=204)
def deactivate_merchant_webhook(
    merchant_id: str, webhook_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> None:
    _invoke(ctx, "merchants", deactivate_webhook, db, ctx, merchant_id, webhook_id, org=True)


@router.post("/{merchant_id}/webhooks/{webhook_id}/enable", status_code=204)
def enable_merchant_webhook(
    merchant_id: str, webhook_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> None:
    _invoke(ctx, "merchants", activate_webhook, db, ctx, merchant_id, webhook_id, org=True)


@router.post("/{merchant_id}/webhooks/{webhook_id}/test")
def test_merchant_webhook(
    merchant_id: str,
    webhook_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _invoke(
        ctx,
        "merchants",
        test_webhook,
        db,
        ctx,
        merchant_id,
        webhook_id,
        encryption_key=settings.jwt_secret,
        org=True,
    )


@router.post("/{merchant_id}/integrations/freeze")
def freeze_merchant_partner_api(
    merchant_id: str,
    body: dict,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    return _invoke(
        ctx,
        "merchants",
        freeze_partner_api,
        db,
        ctx,
        merchant_id,
        reason=body.get("reason"),
        org=True,
        copy=org_error_message,
    )


@router.post("/{merchant_id}/shopify/{shop_id}/force-disconnect", status_code=204)
def force_disconnect_merchant_shopify(
    merchant_id: str,
    shop_id: str,
    body: dict,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> None:
    _invoke(
        ctx,
        "merchants",
        force_disconnect_shopify,
        db,
        ctx,
        merchant_id,
        shop_id,
        reason=body.get("reason"),
        org=True,
        copy=org_error_message,
    )


@router.get("/{merchant_id}/shopify/install-url")
def merchant_shopify_install_url(
    merchant_id: str,
    ctx: Ctx,
    shop: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _invoke(
        ctx,
        "merchants",
        shopify_install_url_for,
        db,
        ctx,
        merchant_id,
        settings,
        shop=shop,
        org=True,
        copy=org_error_message,
    )


@router.post("/{merchant_id}/shopify/{shop_id}/ingress-pause")
def merchant_shopify_ingress_pause(
    merchant_id: str,
    shop_id: str,
    body: dict,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    return _invoke(
        ctx,
        "merchants",
        set_ingress_paused,
        db,
        ctx,
        merchant_id,
        shop_id,
        paused=bool(body.get("paused")),
        reason=body.get("reason"),
        org=True,
        copy=org_error_message,
    )


@router.post("/{merchant_id}/shopify/{shop_id}/auto-dispatch")
def merchant_shopify_auto_dispatch(
    merchant_id: str,
    shop_id: str,
    body: dict,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    return _invoke(
        ctx,
        "merchants",
        set_auto_dispatch,
        db,
        ctx,
        merchant_id,
        shop_id,
        enabled=bool(body.get("enabled")),
        reason=body.get("reason"),
        org=True,
        copy=org_error_message,
    )


@router.get("/{merchant_id}/shopify/ingress-dlq")
def merchant_shopify_ingress_dlq(
    merchant_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    return _invoke(
        ctx,
        "merchants",
        list_merchant_ingress_dlq,
        db,
        ctx,
        merchant_id,
        status=status,
        limit=limit,
        org=True,
        copy=org_error_message,
    )


@router.post("/{merchant_id}/shopify/ingress-dlq/{dlq_id}/replay")
def merchant_shopify_ingress_dlq_replay(
    merchant_id: str,
    dlq_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _invoke(
        ctx,
        "merchants",
        replay_ingress_dlq,
        db,
        ctx,
        merchant_id,
        dlq_id,
        settings,
        org=True,
        copy=org_error_message,
    )


@router.post("/{merchant_id}/shopify/{shop_id}/reregister-hooks")
def merchant_shopify_reregister_hooks(
    merchant_id: str,
    shop_id: str,
    body: dict,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _invoke(
        ctx,
        "merchants",
        reregister_shop_hooks,
        db,
        ctx,
        merchant_id,
        shop_id,
        settings,
        reason=body.get("reason"),
        org=True,
        copy=org_error_message,
    )


@router.post("/{merchant_id}/shopify/{shop_id}/booking-policy")
def merchant_shopify_booking_policy(
    merchant_id: str,
    shop_id: str,
    body: dict,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    return _invoke(
        ctx,
        "merchants",
        set_booking_policy,
        db,
        ctx,
        merchant_id,
        shop_id,
        default_vehicle_class=body.get("default_vehicle_class"),
        default_package_type=body.get("default_package_type"),
        reason=body.get("reason"),
        org=True,
        copy=org_error_message,
    )


