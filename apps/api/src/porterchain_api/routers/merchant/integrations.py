"""merchant routes — integrations."""

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
from porterchain_api.schemas_oauth import OAuthClientCreateRequest


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[ApiKeyResponse]:
    require_module(ctx, "api_keys")
    return [_api_key_out(k) for k in _api_keys.list_keys(db, ctx)]


@router.post("/api-keys", response_model=ApiKeyResponse)
def create_api_key(
    body: ApiKeyCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> ApiKeyResponse:
    require_module(ctx, "api_keys")
    record, secret = _api_keys.create_key(
        db, ctx, name=body.name, scopes=body.scopes, environment=body.environment
    )
    return _api_key_out(record, secret=secret)


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "api_keys")
    try:
        _api_keys.revoke_key(db, ctx, key_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="api_key_not_found") from None


@router.get("/webhooks", response_model=list[WebhookResponse])
def list_webhooks(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[WebhookResponse]:
    require_module(ctx, "api_keys")
    return [_webhook_out(h) for h in _api_keys.list_webhooks(db, ctx)]


@router.post("/webhooks", response_model=WebhookResponse)
def create_webhook(
    body: WebhookCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WebhookResponse:
    require_module(ctx, "api_keys")
    record, secret = _api_keys.create_webhook(
        db, ctx, url=body.url, events=body.events, encryption_key=settings.jwt_secret
    )
    return _webhook_out(record, signing_secret=secret)


@router.get("/integrations/overview")
def integrations_overview(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    return _integrations.overview(db, ctx, api_base_url=settings.porterchain_api_url)


@router.get("/integrations/documentation")
def integrations_documentation(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    return _integrations.documentation(api_base_url=settings.porterchain_api_url)


@router.get("/integrations/events")
def integrations_events(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    return _integrations.event_catalog()


@router.get("/integrations/usage")
def integrations_usage(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90),
):
    require_module(ctx, "api_keys")
    return _integrations.usage(db, ctx, days=days)


@router.get("/integrations/rate-limits")
def integrations_rate_limits(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "api_keys")
    return _integrations.rate_limits(db, ctx)


@router.get("/integrations/sandbox")
def integrations_sandbox_get(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    return _integrations.sandbox_status(ctx)


@router.patch("/integrations/sandbox")
def integrations_sandbox_patch(
    body: MerchantSandboxRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "api_keys")
    return _integrations.set_sandbox_mode(db, ctx, body.sandbox_mode)


@router.get("/integrations/webhooks/logs")
def integrations_webhook_logs(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    webhook_id: str | None = None,
    limit: int = Query(50, le=200),
):
    require_module(ctx, "api_keys")
    return _integrations.webhook_logs(db, ctx, webhook_id=webhook_id, limit=limit)


@router.get("/integrations/webhooks/{webhook_id}/history")
def integrations_webhook_history(
    webhook_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "api_keys")
    try:
        return _integrations.webhook_history(db, ctx, webhook_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="webhook_not_found") from None


@router.post("/integrations/webhooks/{webhook_id}/test")
def integrations_webhook_test(
    webhook_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    try:
        return _integrations.test_webhook(db, ctx, webhook_id, encryption_key=settings.jwt_secret)
    except LookupError:
        raise HTTPException(status_code=404, detail="webhook_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/integrations/webhooks/deliveries/{delivery_id}/retry")
def integrations_webhook_retry(
    delivery_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    try:
        return _integrations.retry_delivery(db, ctx, delivery_id, encryption_key=settings.jwt_secret)
    except LookupError:
        raise HTTPException(status_code=404, detail="delivery_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/integrations/webhooks/{webhook_id}", response_model=WebhookResponse)
def integrations_webhook_update(
    webhook_id: str,
    body: WebhookUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> WebhookResponse:
    require_module(ctx, "api_keys")
    try:
        hook = _integrations.update_webhook(
            db,
            ctx,
            webhook_id,
            url=body.url,
            events=body.events,
            is_active=body.is_active,
        )
        return _webhook_out(hook)
    except LookupError:
        raise HTTPException(status_code=404, detail="webhook_not_found") from None


@router.delete("/integrations/webhooks/{webhook_id}", status_code=204)
def integrations_webhook_delete(
    webhook_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "api_keys")
    try:
        _integrations.delete_webhook(db, ctx, webhook_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="webhook_not_found") from None


@router.post("/integrations/webhooks/{webhook_id}/rotate-secret", response_model=WebhookResponse)
def integrations_webhook_rotate(
    webhook_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WebhookResponse:
    require_module(ctx, "api_keys")
    try:
        hook, secret = _integrations.rotate_webhook_secret(
            db, ctx, webhook_id, encryption_key=settings.jwt_secret
        )
        return _webhook_out(hook, signing_secret=secret)
    except LookupError:
        raise HTTPException(status_code=404, detail="webhook_not_found") from None


@router.patch("/integrations/api-keys/{key_id}/rate-limit")
def integrations_api_key_rate_limit(
    key_id: str,
    body: MerchantApiKeyRateLimitRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "api_keys")
    try:
        return _integrations.update_api_key_rate_limit(
            db, ctx, key_id, rate_limit_per_minute=body.rate_limit_per_minute
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="api_key_not_found") from None


@router.get("/integrations/erp")
def integrations_erp(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    return _integrations.erp_readiness()


@router.get("/integrations/oauth")
def integrations_oauth(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    return _integrations.oauth_readiness(enabled=settings.oauth_third_party_enabled)


@router.get("/integrations/oauth/clients")
def list_oauth_clients(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    return {"clients": _integrations.list_oauth_clients(ctx)}


@router.post("/integrations/oauth/clients")
def create_oauth_client(
    body: OAuthClientCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "api_keys")
    return _integrations.create_oauth_client(
        db,
        ctx,
        name=body.name,
        scopes=body.scopes,
        environment=body.environment,
        redirect_uris=body.redirect_uris,
    )


@router.get("/integrations/csv-templates")
def integrations_csv_templates(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    return _integrations.csv_templates()


@router.get("/integrations/csv-templates/{template_id}.csv")
def integrations_csv_template_download(
    template_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    try:
        content = _integrations.csv_template_download(template_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="template_not_found") from None
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={template_id}-template.csv"},
    )


@router.post("/integrations/console")
def integrations_console(
    body: MerchantConsoleRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    try:
        return _integrations.console_execute(db, settings, ctx, action=body.action, payload=body.payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
