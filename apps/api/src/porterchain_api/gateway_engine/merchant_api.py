"""Merchant API gateway — rate limits, usage, docs, ERP readiness."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant, MerchantApiKey, MerchantApiUsageLog

DEFAULT_RATE_LIMIT = 60
DEFAULT_SCOPES = ["shipments:read", "shipments:write"]

MERCHANT_API_SCOPES: list[dict[str, str]] = [
    {
        "id": "shipments:read",
        "description": "List orders, fetch order detail, and track by public tracking number.",
    },
    {
        "id": "shipments:write",
        "description": "Create bookings and cancel orders via the merchant API gateway.",
    },
]

SCOPE_ENDPOINT_MAP: dict[str, list[str]] = {
    "shipments:read": [
        "GET /v1/merchant-api/orders",
        "GET /v1/merchant-api/orders/{order_id}",
        "GET /v1/merchant-api/track/{tracking_number}",
    ],
    "shipments:write": [
        "POST /v1/merchant-api/bookings",
        "POST /v1/merchant-api/orders/{order_id}/cancel",
    ],
}

MERCHANT_API_EVENTS: list[dict[str, str]] = [
    {"event": "order.created", "description": "Order created after booking confirmation"},
    {"event": "order.booked", "description": "Merchant booking confirmed and scheduled"},
    {"event": "order.dispatch_requested", "description": "Dispatch requested from operations"},
    {"event": "order.dispatch_ready", "description": "Order ready for driver assignment"},
    {"event": "order.driver_assigned", "description": "Driver assigned to order"},
    {"event": "order.driver_accepted", "description": "Driver accepted assignment"},
    {"event": "order.arrived_pickup", "description": "Driver arrived at pickup"},
    {"event": "order.pickup_completed", "description": "Parcel picked up"},
    {"event": "order.in_transit", "description": "Delivery in progress"},
    {"event": "order.delivered", "description": "Parcel delivered"},
    {"event": "order.pod_completed", "description": "Proof of delivery captured"},
    {"event": "order.cancelled", "description": "Order cancelled"},
    {"event": "order.tracking_updated", "description": "Live tracking location update"},
    {"event": "claim.opened", "description": "Claim filed against order"},
    {"event": "claim.resolved", "description": "Claim resolved"},
    {"event": "merchant.invoice_generated", "description": "Invoice generated for merchant"},
    {"event": "webhook.test", "description": "Test ping from integrations console"},
]

API_DOCUMENTATION: list[dict[str, Any]] = [
    {
        "method": "POST",
        "path": "/v1/merchant-api/bookings",
        "scope": "shipments:write",
        "description": "Create a shipment booking",
    },
    {
        "method": "GET",
        "path": "/v1/merchant-api/orders",
        "scope": "shipments:read",
        "description": "List orders with optional state/search filters",
    },
    {
        "method": "GET",
        "path": "/v1/merchant-api/orders/{order_id}",
        "scope": "shipments:read",
        "description": "Get order by ID",
    },
    {
        "method": "GET",
        "path": "/v1/merchant-api/track/{tracking_number}",
        "scope": "shipments:read",
        "description": "Track by public tracking number",
    },
    {
        "method": "POST",
        "path": "/v1/merchant-api/orders/{order_id}/cancel",
        "scope": "shipments:write",
        "description": "Cancel an order",
    },
]

CSV_IMPORT_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "bulk_orders",
        "name": "Bulk order import",
        "description": "CSV/Excel template for bulk booking uploads",
        "required_columns": ["pickup", "dropoff", "scheduled_at"],
        "optional_columns": [
            "internal_reference",
            "purchase_order_number",
            "cost_centre",
            "pickup_lat",
            "pickup_lng",
            "dropoff_lat",
            "dropoff_lng",
            "recipient_id",
            "vehicle_class",
            "package_type",
            "weight_kg",
        ],
    },
    {
        "id": "erp_shipments",
        "name": "ERP shipment export",
        "description": "Standard shipment fields for ERP sync",
        "required_columns": ["external_id", "pickup", "dropoff", "scheduled_at", "reference"],
        "optional_columns": ["cost_centre", "vehicle_class", "weight_kg"],
    },
]

ERP_READINESS: list[dict[str, Any]] = [
    {
        "id": "shopify",
        "name": "Shopify",
        "status": "ready",
        "capabilities": ["webhooks", "api_keys", "order_sync", "tracking"],
        "notes": "Connect via custom app + Porterchain API keys. Webhook events for fulfillment updates.",
    },
    {
        "id": "woocommerce",
        "name": "WooCommerce",
        "status": "ready",
        "capabilities": ["webhooks", "api_keys", "bulk_csv", "tracking"],
        "notes": "Use REST hooks or CSV bulk import for order handoff.",
    },
    {
        "id": "netsuite",
        "name": "NetSuite",
        "status": "ready",
        "capabilities": ["webhooks", "api_keys", "fulfillment_sync", "tracking"],
        "notes": "MVP RESTlet → POST /v1/merchant/integrations/netsuite/sync. See integrations/netsuite/.",
    },
    {
        "id": "custom_erp",
        "name": "Custom ERP",
        "status": "ready",
        "capabilities": ["api_keys", "webhooks", "bulk_csv", "sandbox"],
        "notes": "Full programmatic API + HMAC webhooks. Map your ERP fields to bulk CSV template.",
    },
]

OAUTH_PROVIDERS: list[dict[str, Any]] = [
    {
        "id": "porterchain",
        "name": "Porterchain OAuth",
        "status": "ready",
        "authorization_url": "/v1/oauth/authorize",
        "token_url": "/v1/oauth/token",
        "scopes": ["shipments:read", "shipments:write", "tracking:read"],
    },
    {
        "id": "shopify",
        "name": "Shopify OAuth",
        "status": "coming_soon",
        "authorization_url": None,
        "scopes": ["read_orders", "write_fulfillments"],
    },
    {
        "id": "google",
        "name": "Google Workspace",
        "status": "coming_soon",
        "authorization_url": None,
        "scopes": ["email"],
    },
]


def _integrations_profile(merchant: Merchant) -> dict[str, Any]:
    profile = merchant.profile if isinstance(merchant.profile, dict) else {}
    integrations = profile.get("integrations")
    return integrations if isinstance(integrations, dict) else {}


def sandbox_mode_enabled(merchant: Merchant) -> bool:
    integrations = _integrations_profile(merchant)
    return bool(integrations.get("sandbox_mode", True))


def set_sandbox_mode(merchant: Merchant, enabled: bool) -> dict[str, Any]:
    profile = dict(merchant.profile or {})
    integrations = dict(profile.get("integrations") or {})
    integrations["sandbox_mode"] = enabled
    profile["integrations"] = integrations
    merchant.profile = profile
    return integrations


def check_rate_limit(db: Session, api_key: MerchantApiKey) -> tuple[bool, int, int]:
    """Return (allowed, current_count, limit)."""
    limit = api_key.rate_limit_per_minute or DEFAULT_RATE_LIMIT
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
    count = (
        db.query(func.count(MerchantApiUsageLog.id))
        .filter(MerchantApiUsageLog.api_key_id == api_key.id, MerchantApiUsageLog.created_at >= since)
        .scalar()
        or 0
    )
    return count < limit, int(count), limit


def record_usage(
    db: Session,
    *,
    api_key: MerchantApiKey,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
) -> None:
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


def usage_summary(db: Session, merchant_id: str, *, days: int = 7) -> dict[str, Any]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    rows = (
        db.query(MerchantApiUsageLog)
        .filter(MerchantApiUsageLog.merchant_id == merchant_id, MerchantApiUsageLog.created_at >= since)
        .order_by(MerchantApiUsageLog.created_at.desc())
        .limit(500)
        .all()
    )
    by_day: dict[str, int] = {}
    by_path: dict[str, int] = {}
    by_env: dict[str, int] = {"sandbox": 0, "production": 0}
    errors = 0
    for row in rows:
        day = row.created_at.strftime("%Y-%m-%d") if row.created_at else "unknown"
        by_day[day] = by_day.get(day, 0) + 1
        by_path[row.path] = by_path.get(row.path, 0) + 1
        by_env[row.environment] = by_env.get(row.environment, 0) + 1
        if row.status_code >= 400:
            errors += 1
    return {
        "total_requests": len(rows),
        "error_requests": errors,
        "by_day": [{"date": k, "count": v} for k, v in sorted(by_day.items())],
        "by_path": sorted([{"path": k, "count": v} for k, v in by_path.items()], key=lambda x: x["count"], reverse=True)[:15],
        "by_environment": by_env,
        "recent": [
            {
                "method": r.method,
                "path": r.path,
                "status_code": r.status_code,
                "duration_ms": r.duration_ms,
                "environment": r.environment,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows[:50]
        ],
    }


def rate_limits_for_merchant(db: Session, merchant_id: str) -> list[dict[str, Any]]:
    keys = (
        db.query(MerchantApiKey)
        .filter(MerchantApiKey.merchant_id == merchant_id, MerchantApiKey.is_active.is_(True))
        .all()
    )
    result: list[dict[str, Any]] = []
    for key in keys:
        allowed, current, limit = check_rate_limit(db, key)
        result.append(
            {
                "api_key_id": key.id,
                "name": key.name,
                "environment": key.environment,
                "rate_limit_per_minute": limit,
                "requests_last_minute": current,
                "remaining": max(0, limit - current),
                "throttled": not allowed,
            }
        )
    return result


def csv_template_content(template_id: str) -> str:
    template = next((t for t in CSV_IMPORT_TEMPLATES if t["id"] == template_id), None)
    if not template:
        raise LookupError("template_not_found")
    columns = list(template["required_columns"]) + list(template["optional_columns"])
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    sample = {col: "" for col in columns}
    for col in template["required_columns"]:
        if col == "pickup":
            sample[col] = "123 Main St, Toronto ON"
        elif col == "dropoff":
            sample[col] = "456 Queen St, Toronto ON"
        elif col == "scheduled_at":
            sample[col] = "2026-07-01T10:00:00"
        elif col == "external_id":
            sample[col] = "ERP-1001"
        elif col == "reference":
            sample[col] = "PO-500"
    writer.writerow(sample)
    return buffer.getvalue()


def documentation_bundle(*, api_base_url: str) -> dict[str, Any]:
    return {
        "base_url": api_base_url,
        "auth_header": "X-Api-Key",
        "auth_note": "Pass your API key in the X-Api-Key header. Keys are shown once at creation.",
        "sandbox_prefix": "pk_sandbox_",
        "production_prefix": "pk_production_",
        "default_rate_limit_per_minute": DEFAULT_RATE_LIMIT,
        "rate_limit_is_per_api_key": True,
        "rate_limit_scope": "/v1/merchant-api/*",
        "default_scopes": DEFAULT_SCOPES,
        "scopes": MERCHANT_API_SCOPES,
        "scope_endpoint_map": SCOPE_ENDPOINT_MAP,
        "scope_enforcement": (
            "Each API key stores a list of scope strings. Route handlers call require_scope(); "
            "missing scope returns HTTP 403 with detail api_key_missing_scope:{scope}."
        ),
        "endpoints": API_DOCUMENTATION,
        "webhook_signature_header": "X-Porterchain-Signature",
        "webhook_timestamp_header": "X-Porterchain-Timestamp",
        "webhook_signature_verification": {
            "algorithm": "HMAC-SHA256",
            "message_format": "timestamp + '.' + body_bytes",
            "body_serialization": "json.dumps(body, separators=(',', ':'), default=str).encode('utf-8')",
            "signature_hex": "lowercase hex digest (hexdigest)",
            "secret_source": "signing_secret returned when creating the webhook in POST /v1/merchant/integrations/webhooks",
        },
    }
