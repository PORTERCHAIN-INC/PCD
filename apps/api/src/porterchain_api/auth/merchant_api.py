"""API-key authentication for /v1/merchant-api/* programmatic access."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantApiKey, MerchantUser
from porterchain_api.oauth_engine.oauth_service import OAuthService

_api_keys = MerchantApiKeyService()
_oauth = OAuthService()


@dataclass(frozen=True)
class MerchantApiKeyContext:
    merchant: Merchant
    api_key: MerchantApiKey

    def require_scope(self, scope: str) -> None:
        scopes = set(self.api_key.scopes or [])
        if scope not in scopes:
            raise PermissionError(f"api_key_missing_scope:{scope}")

    def to_service_context(self, db: Session) -> MerchantContext:
        """Map API-key auth to MerchantContext for existing services."""
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == self.merchant.id, MerchantUser.is_active.is_(True))
            .order_by(MerchantUser.created_at.asc())
            .first()
        )
        if not user:
            raise HTTPException(status_code=403, detail="merchant_user_not_found")
        return MerchantContext(merchant=self.merchant, user=user, role=MerchantRole.OPS)


def get_merchant_api_context(
    request: Request,
    db: Session = Depends(get_db),
    x_api_key: Annotated[str | None, Header(alias="X-Api-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> MerchantApiKeyContext:
    record = getattr(request.state, "merchant_api_key", None)
    if record is None and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        payload = _oauth.resolve_bearer_token(token)
        if payload:
            merchant = db.query(Merchant).filter(Merchant.id == payload.get("merchant_id")).first()
            if not merchant:
                raise HTTPException(status_code=401, detail="oauth_token_invalid")
            if merchant.status != MerchantStatus.ACTIVE.value:
                raise HTTPException(status_code=403, detail="merchant_not_active")
            shim = _oauth.api_key_shim(payload, merchant.id)
            return MerchantApiKeyContext(merchant=merchant, api_key=shim)

    if record is None:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="api_key_required")
        record = _api_keys.authenticate_key(db, x_api_key)
        if not record:
            raise HTTPException(status_code=401, detail="api_key_invalid")

    merchant = db.query(Merchant).filter(Merchant.id == record.merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="merchant_not_found")
    if merchant.status != MerchantStatus.ACTIVE.value:
        raise HTTPException(status_code=403, detail="merchant_not_active")

    return MerchantApiKeyContext(merchant=merchant, api_key=record)
