"""OAuth 2.0 — third-party merchant API access."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from porterchain_shared.redis_client import get_redis_client
from sqlalchemy.orm import Session

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine.lookups import get_merchant
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.oauth_engine.oauth_service import OAuthService
from porterchain_api.routers.merchant._deps import require_module
from porterchain_api.schemas_oauth import (
    OAuthAuthorizeRequest,
    OAuthAuthorizeResponse,
    OAuthTokenRequest,
    OAuthTokenResponse,
)

router = APIRouter(prefix="/v1/oauth", tags=["oauth"])
_oauth = OAuthService()


def _merchant_profile(merchant: Any) -> dict:
    return merchant.profile if isinstance(merchant.profile, dict) else {}


@router.get("/.well-known/oauth-authorization-server")
def oauth_metadata(settings: Settings = Depends(get_settings)) -> dict:
    return _oauth.metadata(settings.porterchain_api_url)


@router.get("/authorize")
def oauth_authorize_redirect(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(default="code"),
    scope: str | None = Query(default=None),
    state: str | None = Query(default=None),
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)] = None,
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    if not settings.oauth_third_party_enabled:
        raise HTTPException(status_code=503, detail="oauth_disabled")
    if response_type != "code":
        raise HTTPException(status_code=400, detail="unsupported_response_type")
    require_module(ctx, "api_keys")
    try:
        code = _oauth.issue_authorization_code(
            _merchant_profile(ctx.merchant),
            client_id=client_id,
            merchant_id=ctx.merchant.id,
            redirect_uri=redirect_uri,
            scope=scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    separator = "&" if "?" in redirect_uri else "?"
    location = f"{redirect_uri}{separator}code={code}"
    if state:
        location += f"&state={state}"
    return RedirectResponse(url=location, status_code=302)


@router.post("/authorize", response_model=OAuthAuthorizeResponse)
def oauth_authorize(
    body: OAuthAuthorizeRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    settings: Settings = Depends(get_settings),
) -> OAuthAuthorizeResponse:
    if not settings.oauth_third_party_enabled:
        raise HTTPException(status_code=503, detail="oauth_disabled")
    require_module(ctx, "api_keys")
    try:
        code = _oauth.issue_authorization_code(
            _merchant_profile(ctx.merchant),
            client_id=body.client_id,
            merchant_id=ctx.merchant.id,
            redirect_uri=body.redirect_uri,
            scope=body.scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OAuthAuthorizeResponse(code=code, state=body.state)


@router.post("/token", response_model=OAuthTokenResponse)
def oauth_token(
    body: OAuthTokenRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OAuthTokenResponse:
    if not settings.oauth_third_party_enabled:
        raise HTTPException(status_code=503, detail="oauth_disabled")

    try:
        if body.grant_type == "client_credentials":
            merchant_id = get_redis_client().get(f"oauth:client:{body.client_id}")
            if not merchant_id:
                raise HTTPException(status_code=400, detail="invalid_client")
            merchant = get_merchant(db, merchant_id)
            if not merchant:
                raise HTTPException(status_code=400, detail="invalid_client")
            token = _oauth.client_credentials_token(
                _merchant_profile(merchant),
                merchant_id=merchant.id,
                client_id=body.client_id,
                client_secret=body.client_secret,
                scope=body.scope,
            )
            return OAuthTokenResponse(**token)

        if body.grant_type == "authorization_code":
            if not body.code:
                raise HTTPException(status_code=400, detail="code_required")
            code_raw = get_redis_client().get(f"oauth:code:{body.code}")
            if not code_raw:
                raise HTTPException(status_code=400, detail="invalid_grant")
            payload = json.loads(code_raw)
            merchant = get_merchant(db, payload.get("merchant_id"))
            if not merchant:
                raise HTTPException(status_code=400, detail="invalid_grant")
            token = _oauth.authorization_code_token(
                _merchant_profile(merchant),
                client_id=body.client_id,
                client_secret=body.client_secret,
                code=body.code,
                redirect_uri=body.redirect_uri,
            )
            return OAuthTokenResponse(**token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    raise HTTPException(status_code=400, detail="unsupported_grant_type")
