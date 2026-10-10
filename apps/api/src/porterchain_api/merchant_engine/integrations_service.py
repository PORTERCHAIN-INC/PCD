"""Merchant integrations — orchestrates API keys, webhooks, gateway (masterrule §3)."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.gateway_engine import merchant_api as gateway
from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.orders_service import MerchantOrdersService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.secrets import (
    decrypt_signing_secret,
    encrypt_signing_secret,
)
from porterchain_api.merchant_engine.webhook_delivery_service import (
    deliver_webhook_payload,
    log_delivery,
)
from porterchain_api.merchant_models import MerchantWebhook, MerchantWebhookDelivery
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest

_BACKOFF_SECONDS = (1, 4, 16)


class MerchantIntegrationsService:
    def __init__(self) -> None:
        self._keys = MerchantApiKeyService()
        self._orders = MerchantOrdersService()
        self._booking = MerchantBookingService()

    def overview(self, db: Session, ctx: MerchantContext, *, api_base_url: str) -> dict[str, Any]:
        keys = self._keys.list_keys(db, ctx)
        hooks = self._keys.list_webhooks(db, ctx)
        usage = gateway.usage_summary(db, ctx.merchant.id)
        limits = gateway.rate_limits_for_merchant(db, ctx.merchant.id)
        recent_logs = self.webhook_logs(db, ctx, limit=10)
        return {
            "sandbox_mode": gateway.sandbox_mode_enabled(ctx.merchant),
            "booking_env_preference": gateway.booking_env_preference(ctx.merchant),
            "api_keys_count": len(keys),
            "sandbox_keys": sum(1 for k in keys if k.environment == "sandbox"),
            "production_keys": sum(1 for k in keys if k.environment == "production"),
            "webhooks_count": len(hooks),
            "active_webhooks": sum(1 for h in hooks if h.is_active),
            "usage": usage,
            "rate_limits": limits,
            "recent_webhook_deliveries": recent_logs,
            "documentation_url": f"{api_base_url}/v1/merchant/integrations/documentation",
            "erp_platforms": [],
            "erp_marketplace": False,
            "available_integrations": ["shopify", "merchant-api"],
        }

    def sandbox_status(self, ctx: MerchantContext) -> dict[str, Any]:
        enabled = gateway.sandbox_mode_enabled(ctx.merchant)
        return {
            "sandbox_mode": enabled,
            "booking_env_preference": gateway.booking_env_preference(ctx.merchant),
        }

    def set_sandbox_mode(self, db: Session, ctx: MerchantContext, enabled: bool) -> dict[str, Any]:
        from porterchain_api.merchant_engine.rbac import require_owner
        from porterchain_api.merchant_models import MerchantAuditLog

        # Turning the reminder off is a go-live signal — Owner only.
        if not enabled:
            require_owner(ctx)
        previous = gateway.sandbox_mode_enabled(ctx.merchant)
        gateway.set_sandbox_mode(ctx.merchant, enabled)
        db.add(
            MerchantAuditLog(
                merchant_id=ctx.merchant.id,
                actor_user_id=ctx.user.id,
                action="sandbox.preference_changed",
                resource_type="sandbox",
                resource_id=ctx.merchant.id,
                payload={"from": previous, "to": enabled},
            )
        )
        db.commit()
        db.refresh(ctx.merchant)
        return self.sandbox_status(ctx)

    def simulate_lifecycle(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        *,
        order_id: str,
        deliver_webhooks: bool = True,
        until_state: str | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.merchant_engine.sandbox_simulator import (
            simulate_sandbox_lifecycle,
        )

        return simulate_sandbox_lifecycle(
            db,
            settings,
            ctx,
            order_id,
            deliver_webhooks=deliver_webhooks,
            until_state=until_state,
        )

    def purge_sandbox_orders(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        confirm: str,
    ) -> dict[str, Any]:
        """Cancel merchant-owned open sandbox orders."""
        from porterchain_api.booking_models import Order
        from porterchain_api.domain.states import OrderState

        if (confirm or "").strip().upper() != "PURGE TEST":
            raise ValueError("type_PURGE_TEST_to_confirm")
        rows = (
            db.query(Order)
            .filter(
                Order.merchant_id == ctx.merchant.id,
                Order.is_sandbox.is_(True),
                Order.state.notin_(
                    (
                        OrderState.CANCELLED.value,
                        OrderState.CLOSED.value,
                        OrderState.REFUNDED.value,
                    )
                ),
            )
            .all()
        )
        for order in rows:
            order.state = OrderState.CANCELLED.value
        db.commit()
        return {"cancelled": len(rows), "message": "Sandbox orders without dispatch were cancelled."}

    def usage(self, db: Session, ctx: MerchantContext, *, days: int = 7) -> dict[str, Any]:
        return gateway.usage_summary(db, ctx.merchant.id, days=days)

    def rate_limits(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        return {"limits": gateway.rate_limits_for_merchant(db, ctx.merchant.id)}

    def documentation(self, *, api_base_url: str) -> dict[str, Any]:
        return gateway.documentation_bundle(api_base_url=api_base_url)

    def event_catalog(self) -> dict[str, Any]:
        return {"events": gateway.MERCHANT_API_EVENTS}

    def erp_readiness(self) -> dict[str, Any]:
        return {"platforms": gateway.ERP_READINESS}

    def integration_depth(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        from porterchain_api.reporting.switching_costs import integration_depth

        return integration_depth(db, ctx.merchant.id)

    def oauth_readiness(self, *, enabled: bool) -> dict[str, Any]:
        return {
            "providers": gateway.OAUTH_PROVIDERS,
            "enabled": enabled,
            "authorization_endpoint": "/v1/oauth/authorize",
            "token_endpoint": "/v1/oauth/token",
            "metadata_endpoint": "/v1/oauth/.well-known/oauth-authorization-server",
        }

    def list_oauth_clients(self, ctx: MerchantContext) -> dict[str, Any]:
        from porterchain_api.oauth_engine.oauth_service import OAuthService

        profile = ctx.merchant.profile if isinstance(ctx.merchant.profile, dict) else {}
        return {"clients": OAuthService().list_clients(profile)}

    def create_oauth_client(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        name: str,
        scopes: list[str],
        environment: str,
        redirect_uris: list[str] | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.oauth_engine.oauth_service import OAuthService

        profile = ctx.merchant.profile if isinstance(ctx.merchant.profile, dict) else {}
        public, secret, updated = OAuthService().create_client(
            profile,
            merchant_id=ctx.merchant.id,
            name=name,
            scopes=scopes,
            environment=environment,
            redirect_uris=redirect_uris,
        )
        ctx.merchant.profile = updated
        db.commit()
        db.refresh(ctx.merchant)
        return {**public, "client_secret": secret}

    def csv_templates(self) -> dict[str, Any]:
        return {"templates": gateway.CSV_IMPORT_TEMPLATES}

    def csv_template_download(self, template_id: str) -> str:
        return gateway.csv_template_content(template_id)

    def webhook_logs(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        webhook_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = db.query(MerchantWebhookDelivery).filter(
            MerchantWebhookDelivery.merchant_id == ctx.merchant.id
        )
        if webhook_id:
            query = query.filter(MerchantWebhookDelivery.webhook_id == webhook_id)
        rows = query.order_by(MerchantWebhookDelivery.created_at.desc()).limit(limit).all()
        return [self._serialize_delivery(r) for r in rows]

    def webhook_history(self, db: Session, ctx: MerchantContext, webhook_id: str) -> list[dict[str, Any]]:
        hook = self._require_webhook(db, ctx, webhook_id)
        return self.webhook_logs(db, ctx, webhook_id=hook.id, limit=100)

    def update_webhook(
        self,
        db: Session,
        ctx: MerchantContext,
        webhook_id: str,
        *,
        url: str | None = None,
        events: list[str] | None = None,
        is_active: bool | None = None,
        environment: str | None = None,
    ) -> MerchantWebhook:
        hook = self._require_webhook(db, ctx, webhook_id)
        if url is not None:
            hook.url = url
        if events is not None:
            hook.events = events
        if is_active is not None:
            hook.is_active = is_active
        if environment is not None:
            env = environment.lower()
            if env not in {"sandbox", "production"}:
                raise ValueError("invalid_webhook_environment")
            hook.environment = env
        hook.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(hook)
        return hook

    def delete_webhook(self, db: Session, ctx: MerchantContext, webhook_id: str) -> None:
        hook = self._require_webhook(db, ctx, webhook_id)
        db.delete(hook)
        db.commit()

    def rotate_webhook_secret(
        self,
        db: Session,
        ctx: MerchantContext,
        webhook_id: str,
        *,
        encryption_key: str,
    ) -> tuple[MerchantWebhook, str]:
        import hashlib
        import secrets

        hook = self._require_webhook(db, ctx, webhook_id)
        secret = secrets.token_urlsafe(24)
        hook.secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        hook.encrypted_signing_secret = encrypt_signing_secret(secret, encryption_key=encryption_key)
        hook.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(hook)
        return hook, secret

    def test_webhook(
        self,
        db: Session,
        ctx: MerchantContext,
        webhook_id: str,
        *,
        encryption_key: str,
    ) -> dict[str, Any]:
        hook = self._require_webhook(db, ctx, webhook_id)
        body = {
            "event_type": "webhook.test",
            "merchant_id": ctx.merchant.id,
            "occurred_at": datetime.now(UTC).isoformat(),
            "payload": {"message": "Porterchain webhook test"},
        }
        return self._deliver_and_log(db, hook, body, encryption_key=encryption_key)

    def retry_delivery(
        self,
        db: Session,
        ctx: MerchantContext,
        delivery_id: str,
        *,
        encryption_key: str,
    ) -> dict[str, Any]:
        delivery = (
            db.query(MerchantWebhookDelivery)
            .filter(
                MerchantWebhookDelivery.id == delivery_id,
                MerchantWebhookDelivery.merchant_id == ctx.merchant.id,
            )
            .first()
        )
        if not delivery:
            raise LookupError("delivery_not_found")
        hook = self._require_webhook(db, ctx, delivery.webhook_id)
        return self._deliver_and_log(
            db,
            hook,
            delivery.request_body,
            encryption_key=encryption_key,
            attempt=delivery.attempt + 1,
        )

    def update_api_key_rate_limit(
        self, db: Session, ctx: MerchantContext, key_id: str, *, rate_limit_per_minute: int
    ) -> dict[str, Any]:
        from porterchain_api.merchant_engine.api_key_limits import set_rate_limit

        return set_rate_limit(db, ctx.merchant.id, key_id, rate_limit_per_minute)

    def console_execute(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        *,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merchant API testing console — uses service layer (no raw key required)."""
        data = payload or {}
        if action == "list_orders":
            orders = self._orders.list_orders(
                db,
                ctx,
                state=data.get("state"),
                search=data.get("search"),
                limit=int(data.get("limit") or 10),
                offset=int(data.get("offset") or 0),
            )
            return {
                "action": action,
                "count": len(orders),
                "result": [
                    {
                        "id": o.id,
                        "order_number": o.order_number,
                        "tracking_number": o.tracking_number,
                        "state": o.state,
                    }
                    for o in orders
                ],
            }
        if action == "get_order":
            order_id = str(data.get("order_id") or "")
            order = self._orders.get_order(db, ctx, order_id)
            if not order:
                raise LookupError("order_not_found")
            return {
                "action": action,
                "result": {
                    "id": order.id,
                    "order_number": order.order_number,
                    "state": order.state,
                    "amount_cents": order.amount_cents,
                },
            }
        if action == "track":
            tracking = str(data.get("tracking_number") or "")
            order = self._orders.get_by_tracking(db, ctx, tracking)
            if not order:
                raise LookupError("order_not_found")
            timeline = self._orders.get_tracking_timeline(db, ctx, order.id)
            return {"action": action, "result": {"order_id": order.id, "timeline": timeline}}
        if action == "create_booking":
            if gateway.sandbox_mode_enabled(ctx.merchant) and data.get("environment") == "production":
                raise ValueError("sandbox_mode_blocks_production_writes")
            body = MerchantBookDeliveryRequest.model_validate(data.get("booking") or data)
            env = str(data.get("environment") or "").lower()
            is_sandbox = bool(getattr(body, "is_sandbox", False)) or env == "sandbox"
            order = self._booking.create_shipment(
                db, settings, ctx, body, sandbox=is_sandbox
            )
            return {
                "action": action,
                "result": {
                    "id": order.id,
                    "order_number": order.order_number,
                    "tracking_number": order.tracking_number,
                    "state": order.state,
                    "is_sandbox": bool(getattr(order, "is_sandbox", False)),
                },
            }
        if action == "simulate_lifecycle":
            order_id = str(data.get("order_id") or "")
            if not order_id:
                raise ValueError("order_id_required")
            result = self.simulate_lifecycle(
                db,
                settings,
                ctx,
                order_id=order_id,
                deliver_webhooks=bool(data.get("deliver_webhooks", True)),
                until_state=data.get("until_state"),
            )
            return {"action": action, "result": result}
        raise ValueError(f"unsupported_console_action:{action}")

    def _deliver_and_log(
        self,
        db: Session,
        hook: MerchantWebhook,
        body: dict[str, Any],
        *,
        encryption_key: str,
        attempt: int = 1,
    ) -> dict[str, Any]:
        if not hook.encrypted_signing_secret:
            raise ValueError("webhook_missing_secret")
        signing_secret = decrypt_signing_secret(hook.encrypted_signing_secret, encryption_key=encryption_key)
        start = time.perf_counter()
        status, response_text, error = deliver_webhook_payload(hook.url, body, signing_secret)
        duration_ms = int((time.perf_counter() - start) * 1000)
        success = status is not None and status < 400
        next_retry = None
        if not success and attempt < 3:
            next_retry = datetime.now(UTC).replace(tzinfo=None)
            from datetime import timedelta

            next_retry = next_retry + timedelta(seconds=_BACKOFF_SECONDS[min(attempt - 1, 2)])
        delivery = log_delivery(
            db,
            merchant_id=hook.merchant_id,
            webhook_id=hook.id,
            event_type=str(body.get("event_type") or "unknown"),
            request_body=body,
            response_status=status,
            response_body=response_text,
            attempt=attempt,
            success=success,
            error_message=error,
            duration_ms=duration_ms,
            next_retry_at=next_retry,
        )
        return self._serialize_delivery(delivery)

    def netsuite_setup(self, *, api_base_url: str) -> dict[str, Any]:
        from porterchain_api.integrations.netsuite_adapter import netsuite_setup_bundle

        return netsuite_setup_bundle(api_base_url=api_base_url)

    def connect_netsuite(self, db: Session, ctx: MerchantContext, *, account_id: str) -> dict[str, Any]:
        profile = dict(ctx.merchant.profile or {})
        integrations = dict(profile.get("integrations") or {})
        integrations["netsuite"] = {
            "account_id": account_id.strip(),
            "connected": True,
            "connected_at": datetime.now(UTC).isoformat(),
        }
        profile["integrations"] = integrations
        ctx.merchant.profile = profile
        db.commit()
        db.refresh(ctx.merchant)
        return integrations["netsuite"]

    def sync_netsuite(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        from porterchain_api.integrations.netsuite_adapter import (
            map_netsuite_fulfillment,
        )

        body = map_netsuite_fulfillment(payload)
        is_sandbox = bool(payload.get("is_sandbox") or payload.get("sandbox"))
        order = self._booking.create_shipment(
            db, settings, ctx, body, sandbox=is_sandbox
        )
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "state": order.state,
            "is_sandbox": bool(getattr(order, "is_sandbox", False)),
            "external_id": payload.get("external_id") or payload.get("tranid"),
        }

    def zapier_templates(self) -> dict[str, Any]:
        from porterchain_api.integrations.zapier_catalog import zapier_catalog

        return zapier_catalog()

    def _require_webhook(self, db: Session, ctx: MerchantContext, webhook_id: str) -> MerchantWebhook:
        hook = (
            db.query(MerchantWebhook)
            .filter(MerchantWebhook.id == webhook_id, MerchantWebhook.merchant_id == ctx.merchant.id)
            .first()
        )
        if not hook:
            raise LookupError("webhook_not_found")
        return hook

    def _serialize_delivery(self, row: MerchantWebhookDelivery) -> dict[str, Any]:
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
            "request_body": row.request_body,
            "response_body": (row.response_body or "")[:500],
        }
