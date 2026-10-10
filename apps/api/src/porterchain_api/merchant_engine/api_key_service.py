"""Merchant API keys and webhooks."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.merchant_engine import events as E
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.secrets import encrypt_signing_secret
from porterchain_api.merchant_models import MerchantApiKey, MerchantAuditLog, MerchantWebhook


class MerchantApiKeyService:
    def create_key(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        name: str,
        scopes: list[str],
        environment: str,
    ) -> tuple[MerchantApiKey, str]:
        from porterchain_api.merchant_engine.rbac import require_owner

        if environment == "production":
            require_owner(ctx)
        raw = f"pk_{environment}_{secrets.token_urlsafe(32)}"
        prefix = raw[:12]
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        record = MerchantApiKey(
            merchant_id=ctx.merchant.id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
            environment=environment,
        )
        db.add(record)
        db.flush()
        self._audit(db, ctx, "api_key.created", "api_key", record.id, {"name": name})
        emit_event(
            db,
            event_type=E.API_KEY_GENERATED,
            aggregate_type="api_key",
            aggregate_id=record.id,
            correlation_id=ctx.merchant.id,
            actor_type="merchant",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(record)
        return record, raw

    def list_keys(self, db: Session, ctx: MerchantContext) -> list[MerchantApiKey]:
        return (
            db.query(MerchantApiKey)
            .filter(MerchantApiKey.merchant_id == ctx.merchant.id, MerchantApiKey.is_active.is_(True))
            .order_by(MerchantApiKey.created_at.desc())
            .all()
        )

    def authenticate_key(self, db: Session, raw_key: str) -> MerchantApiKey | None:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        record = (
            db.query(MerchantApiKey)
            .filter(MerchantApiKey.key_hash == key_hash, MerchantApiKey.is_active.is_(True))
            .first()
        )
        if not record:
            return None
        now = datetime.now(UTC)
        expires = record.expires_at
        if expires is not None and (expires if expires.tzinfo else expires.replace(tzinfo=UTC)) <= now:
            # Rotated key past its grace window: retire it on first use.
            record.is_active = False
            db.commit()
            return None
        record.last_used_at = now
        db.commit()
        db.refresh(record)
        return record

    def revoke_key(self, db: Session, ctx: MerchantContext, key_id: str) -> None:
        record = db.query(MerchantApiKey).filter(MerchantApiKey.id == key_id, MerchantApiKey.merchant_id == ctx.merchant.id).first()
        if not record:
            raise LookupError("api_key_not_found")
        record.is_active = False
        self._audit(db, ctx, "api_key.revoked", "api_key", key_id, {})
        db.commit()

    def create_webhook(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        url: str,
        events: list[str],
        encryption_key: str,
        environment: str = "sandbox",
    ) -> tuple[MerchantWebhook, str]:
        env = (environment or "sandbox").lower()
        if env not in {"sandbox", "production"}:
            raise ValueError("invalid_webhook_environment")
        from porterchain_api.platform.outbound_url import assert_public_https_url

        assert_public_https_url(url)  # SSRF: public https only (raises ValueError)
        secret = secrets.token_urlsafe(24)
        record = MerchantWebhook(
            merchant_id=ctx.merchant.id,
            url=url,
            events=events,
            environment=env,
            secret_hash=hashlib.sha256(secret.encode()).hexdigest(),
            encrypted_signing_secret=encrypt_signing_secret(secret, encryption_key=encryption_key),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record, secret

    def list_webhooks(self, db: Session, ctx: MerchantContext) -> list[MerchantWebhook]:
        return db.query(MerchantWebhook).filter(MerchantWebhook.merchant_id == ctx.merchant.id).all()

    def deactivate_webhook(self, db: Session, ctx: MerchantContext, webhook_id: str) -> None:
        record = (
            db.query(MerchantWebhook)
            .filter(MerchantWebhook.id == webhook_id, MerchantWebhook.merchant_id == ctx.merchant.id)
            .first()
        )
        if not record:
            raise LookupError("webhook_not_found")
        record.is_active = False
        self._audit(db, ctx, "webhook.disabled", "webhook", webhook_id, {})
        db.commit()

    def activate_webhook(self, db: Session, ctx: MerchantContext, webhook_id: str) -> None:
        record = (
            db.query(MerchantWebhook)
            .filter(MerchantWebhook.id == webhook_id, MerchantWebhook.merchant_id == ctx.merchant.id)
            .first()
        )
        if not record:
            raise LookupError("webhook_not_found")
        record.is_active = True
        self._audit(db, ctx, "webhook.enabled", "webhook", webhook_id, {})
        db.commit()

    def _audit(
        self,
        db: Session,
        ctx: MerchantContext,
        action: str,
        resource_type: str,
        resource_id: str,
        payload: dict,
    ) -> None:
        db.add(
            MerchantAuditLog(
                merchant_id=ctx.merchant.id,
                actor_user_id=ctx.user.id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                payload=payload,
            )
        )


def record_usage(
    db: Session,
    *,
    api_key: MerchantApiKey,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
) -> None:
    from porterchain_api.merchant_models import MerchantApiUsageLog

    db.add(
        MerchantApiUsageLog(
            merchant_id=api_key.merchant_id,
            api_key_id=api_key.id,
            method=method.upper(),
            path=path[:255],
            status_code=status_code,
            duration_ms=duration_ms,
            environment=api_key.environment,
        )
    )
    db.commit()
