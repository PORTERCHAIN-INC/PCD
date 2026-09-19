"""merchant routes — integrations."""

from collections.abc import Callable
from typing import TypeVar

from porterchain_api.merchant_engine.integration_copy import integration_error_message
from porterchain_api.routers.merchant._deps import (
    Annotated,
    ApiKeyCreateRequest,
    ApiKeyResponse,
    Depends,
    HTTPException,
    MerchantApiKeyRateLimitRequest,
    MerchantConsoleRequest,
    MerchantContext,
    MerchantSandboxRequest,
    Query,
    Response,
    Session,
    Settings,
    WebhookCreateRequest,
    WebhookResponse,
    WebhookUpdateRequest,
    _api_key_out,
    _api_keys,
    _integrations,
    _webhook_out,
    get_db,
    get_merchant_context,
    get_settings,
    require_module,
    router,
)
from porterchain_api.schemas_merchant import (
    MerchantSandboxPurgeRequest,
    MerchantSandboxSimulateRequest,
    NetSuiteConnectRequest,
    NetSuiteSyncRequest,
)
from porterchain_api.schemas_oauth import OAuthClientCreateRequest

T = TypeVar("T")
Ctx = Annotated[MerchantContext, Depends(get_merchant_context)]


def _integration_http(status: int, exc: BaseException) -> HTTPException:
    return HTTPException(status_code=status, detail=integration_error_message(str(exc)))


def _invoke(fn: Callable[..., T], ctx: MerchantContext, *args: object, **kwargs: object) -> T:
    try:
        require_module(ctx, "api_keys")
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise _integration_http(403, exc) from exc
    except LookupError as exc:
        raise _integration_http(404, exc) from None
    except ValueError as exc:
        raise _integration_http(400, exc) from exc


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(ctx: Ctx, db: Session = Depends(get_db)) -> list[ApiKeyResponse]:
    return _invoke(lambda: [_api_key_out(k) for k in _api_keys.list_keys(db, ctx)], ctx)


@router.post("/api-keys", response_model=ApiKeyResponse)
def create_api_key(body: ApiKeyCreateRequest, ctx: Ctx, db: Session = Depends(get_db)) -> ApiKeyResponse:
    record, secret = _invoke(
        _api_keys.create_key, ctx, db, ctx, name=body.name, scopes=body.scopes, environment=body.environment
    )
    return _api_key_out(record, secret=secret)


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(key_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> None:
    return _invoke(_api_keys.revoke_key, ctx, db, ctx, key_id)


@router.get("/webhooks", response_model=list[WebhookResponse])
def list_webhooks(ctx: Ctx, db: Session = Depends(get_db)) -> list[WebhookResponse]:
    return _invoke(lambda: [_webhook_out(h) for h in _api_keys.list_webhooks(db, ctx)], ctx)


@router.post("/webhooks", response_model=WebhookResponse)
def create_webhook(
    body: WebhookCreateRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WebhookResponse:
    record, secret = _invoke(
        _api_keys.create_webhook,
        ctx,
        db,
        ctx,
        url=body.url,
        events=body.events,
        encryption_key=settings.jwt_secret,
        environment=body.environment,
    )
    return _webhook_out(record, signing_secret=secret)


@router.get("/integrations/overview")
def integrations_overview(ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    return _invoke(_integrations.overview, ctx, db, ctx, api_base_url=settings.porterchain_api_url)


@router.get("/integrations/documentation")
def integrations_documentation(ctx: Ctx, settings: Settings = Depends(get_settings)):
    return _invoke(_integrations.documentation, ctx, api_base_url=settings.porterchain_api_url)


@router.get("/integrations/events")
def integrations_events(ctx: Ctx):
    return _invoke(_integrations.event_catalog, ctx)


@router.get("/integrations/usage")
def integrations_usage(ctx: Ctx, db: Session = Depends(get_db), days: int = Query(7, ge=1, le=90)):
    return _invoke(_integrations.usage, ctx, db, ctx, days=days)


@router.get("/integrations/rate-limits")
def integrations_rate_limits(ctx: Ctx, db: Session = Depends(get_db)):
    return _invoke(_integrations.rate_limits, ctx, db, ctx)


@router.get("/integrations/sandbox")
def integrations_sandbox_get(ctx: Ctx):
    return _invoke(_integrations.sandbox_status, ctx, ctx)


@router.patch("/integrations/sandbox")
def integrations_sandbox_patch(body: MerchantSandboxRequest, ctx: Ctx, db: Session = Depends(get_db)):
    return _invoke(_integrations.set_sandbox_mode, ctx, db, ctx, body.sandbox_mode)


@router.post("/integrations/sandbox/purge")
def integrations_sandbox_purge(
    body: MerchantSandboxPurgeRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
):
    return _invoke(_integrations.purge_sandbox_orders, ctx, db, ctx, confirm=body.confirm)


@router.post("/integrations/sandbox/simulate")
def integrations_sandbox_simulate(
    body: MerchantSandboxSimulateRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _invoke(
        _integrations.simulate_lifecycle,
        ctx,
        db,
        settings,
        ctx,
        order_id=body.order_id,
        deliver_webhooks=body.deliver_webhooks,
        until_state=body.until_state,
    )


@router.get("/integrations/webhooks/logs")
def integrations_webhook_logs(
    ctx: Ctx,
    db: Session = Depends(get_db),
    webhook_id: str | None = None,
    limit: int = Query(50, le=200),
):
    return _invoke(_integrations.webhook_logs, ctx, db, ctx, webhook_id=webhook_id, limit=limit)


@router.get("/integrations/webhooks/{webhook_id}/history")
def integrations_webhook_history(webhook_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    return _invoke(_integrations.webhook_history, ctx, db, ctx, webhook_id)


@router.post("/integrations/webhooks/{webhook_id}/test")
def integrations_webhook_test(
    webhook_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    return _invoke(_integrations.test_webhook, ctx, db, ctx, webhook_id, encryption_key=settings.jwt_secret)


@router.post("/integrations/webhooks/deliveries/{delivery_id}/retry")
def integrations_webhook_retry(
    delivery_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    return _invoke(_integrations.retry_delivery, ctx, db, ctx, delivery_id, encryption_key=settings.jwt_secret)


@router.patch("/integrations/webhooks/{webhook_id}", response_model=WebhookResponse)
def integrations_webhook_update(
    webhook_id: str, body: WebhookUpdateRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> WebhookResponse:
    hook = _invoke(
        _integrations.update_webhook,
        ctx,
        db,
        ctx,
        webhook_id,
        url=body.url,
        events=body.events,
        is_active=body.is_active,
        environment=body.environment,
    )
    return _webhook_out(hook)


@router.delete("/integrations/webhooks/{webhook_id}", status_code=204)
def integrations_webhook_delete(webhook_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> None:
    return _invoke(_integrations.delete_webhook, ctx, db, ctx, webhook_id)


@router.post("/integrations/webhooks/{webhook_id}/rotate-secret", response_model=WebhookResponse)
def integrations_webhook_rotate(
    webhook_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> WebhookResponse:
    hook, secret = _invoke(
        _integrations.rotate_webhook_secret, ctx, db, ctx, webhook_id, encryption_key=settings.jwt_secret
    )
    return _webhook_out(hook, signing_secret=secret)


@router.patch("/integrations/api-keys/{key_id}/rate-limit")
def integrations_api_key_rate_limit(
    key_id: str, body: MerchantApiKeyRateLimitRequest, ctx: Ctx, db: Session = Depends(get_db)
):
    raise _integration_http(403, ValueError("rate_limits_admin_owned"))


@router.get("/integrations/erp")
def integrations_erp(ctx: Ctx):
    return _invoke(_integrations.erp_readiness, ctx)


@router.get("/integrations/netsuite/setup")
def netsuite_setup(ctx: Ctx, settings: Settings = Depends(get_settings)):
    """§7.2.3 — NetSuite MVP setup bundle."""
    return _invoke(_integrations.netsuite_setup, ctx, api_base_url=settings.porterchain_api_url)


@router.post("/integrations/netsuite/connect")
def netsuite_connect(body: NetSuiteConnectRequest, ctx: Ctx, db: Session = Depends(get_db)):
    return _invoke(_integrations.connect_netsuite, ctx, db, ctx, account_id=body.account_id)


@router.post("/integrations/netsuite/sync")
def netsuite_sync(
    body: NetSuiteSyncRequest, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    """§7.2.3 — map NetSuite fulfillment → Porterchain shipment."""
    return _invoke(_integrations.sync_netsuite, ctx, db, settings, ctx, body.model_dump())


@router.get("/integrations/zapier/templates")
def zapier_templates(ctx: Ctx):
    """§7.2.4 — Zapier template catalog."""
    return _invoke(_integrations.zapier_templates, ctx)


@router.get("/integrations/depth")
def integrations_depth(ctx: Ctx, db: Session = Depends(get_db)):
    """§8.3.1 — active integration channel count per merchant."""
    return _invoke(_integrations.integration_depth, ctx, db, ctx)


@router.get("/integrations/oauth")
def integrations_oauth(ctx: Ctx, settings: Settings = Depends(get_settings)):
    return _invoke(_integrations.oauth_readiness, ctx, enabled=settings.oauth_third_party_enabled)


@router.get("/integrations/oauth/clients")
def list_oauth_clients(ctx: Ctx):
    return _invoke(_integrations.list_oauth_clients, ctx, ctx)


@router.post("/integrations/oauth/clients")
def create_oauth_client(body: OAuthClientCreateRequest, ctx: Ctx, db: Session = Depends(get_db)):
    return _invoke(
        _integrations.create_oauth_client,
        ctx,
        db,
        ctx,
        name=body.name,
        scopes=body.scopes,
        environment=body.environment,
        redirect_uris=body.redirect_uris,
    )


@router.get("/integrations/csv-templates")
def integrations_csv_templates(ctx: Ctx):
    return _invoke(_integrations.csv_templates, ctx)


@router.get("/integrations/csv-templates/{template_id}.csv")
def integrations_csv_template_download(template_id: str, ctx: Ctx):
    content = _invoke(_integrations.csv_template_download, ctx, template_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={template_id}-template.csv"},
    )


@router.post("/integrations/console")
def integrations_console(
    body: MerchantConsoleRequest, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    return _invoke(
        _integrations.console_execute, ctx, db, settings, ctx, action=body.action, payload=body.payload
    )
