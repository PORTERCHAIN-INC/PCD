#!/usr/bin/env python3
"""
Deep Shopify infusion probe — dummy Partner/shop credentials against local API + DB.

Simulates Shopify-side HMAC (shop webhook secret) for:
  - carrier-service/rates (checkout)
  - orders/create → enqueue → book parcel
  - orders/cancelled
  - connection / go-live readiness
  - ingress pause → DLQ hold
  - non-sandbox BOOKED hold (auto_dispatch=false)

Usage (API running on :8001, API venv + .env loaded):

  cd apps/api && set -a && source .env && set +a
  PYTHONPATH=src .venv/bin/python scripts/shopify_deep_infusion_probe.py

Env:
  PORTERCHAIN_API_URL   default http://127.0.0.1:8001
  SHOPIFY_PROBE_KEEP=1  keep infused rows (default: cleanup)

Exit 0 when all hard checks pass (SKIPs allowed). Exit 1 on any FAIL.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

# Register FK targets before any Session flush (addresses, porterchain_users, …).
import porterchain_api.booking_models  # noqa: E402, F401
import porterchain_api.user_models  # noqa: E402, F401

from porterchain_api.booking_models import Order  # noqa: E402
from porterchain_api.config import get_settings  # noqa: E402
from porterchain_api.db import SessionLocal  # noqa: E402
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus  # noqa: E402
from porterchain_api.domain.states import OrderSource  # noqa: E402
from porterchain_api.merchant_engine import shopify_service as shopify  # noqa: E402
from porterchain_api.merchant_engine.rbac import MerchantContext  # noqa: E402
from porterchain_api.merchant_engine.secrets import encrypt_signing_secret  # noqa: E402
from porterchain_api.merchant_engine.shopify_ingress_dlq import (  # noqa: E402
    REASON_INGRESS_PAUSED,
    list_ingress_dlq,
)
from porterchain_api.merchant_models import (  # noqa: E402
    Merchant,
    SavedAddress,
    ShopifyRateQuote,
    ShopifyShop,
)

API = os.environ.get("PORTERCHAIN_API_URL", "http://127.0.0.1:8001").rstrip("/")
KEEP = os.environ.get("SHOPIFY_PROBE_KEEP", "").strip() in {"1", "true", "yes"}
DUMMY_SHOP_WEBHOOK_SECRET = "whsec_dummy_shopify_infusion_2026_probe"
DUMMY_ADMIN_TOKEN = "shpat_dummy_admin_access_token_infusion_probe"

Result = tuple[str, str, str]  # step, status, detail


def _sign(body: bytes, secret: str) -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def _order_payload(*, suffix: str, order_id: int, test: bool) -> dict[str, Any]:
    return {
        "id": order_id,
        "name": f"#INF-{suffix}",
        "test": test,
        "shipping_address": {
            "address1": "250 Yonge St",
            "city": "Toronto",
            "province_code": "ON",
            "province": "Ontario",
            "zip": "M5B2L7",
            "country": "CA",
            "name": "Probe Customer",
            "phone": "+14165550100",
            "latitude": 43.6544,
            "longitude": -79.3807,
        },
        "line_items": [
            {"name": "Parcel A", "grams": 1500, "quantity": 1},
            {"name": "Parcel B", "grams": 800, "quantity": 2},
        ],
    }


def _rate_payload() -> dict[str, Any]:
    return {
        "rate": {
            "currency": "CAD",
            "origin": {
                "postal_code": "M5H2N2",
                "country": "CA",
                "province": "ON",
                "city": "Toronto",
                "address1": "100 Queen St W",
            },
            "destination": {
                "postal_code": "M5B2L7",
                "country": "CA",
                "province": "ON",
                "city": "Toronto",
                "address1": "250 Yonge St",
            },
            "items": [{"name": "Box", "quantity": 1, "grams": 2000}],
        }
    }


def _cleanup_merchant(db: Session, merchant_id: str) -> None:
    """Delete probe merchant and dependent rows (FK-safe)."""
    bind = db.get_bind()
    refs = db.execute(
        text(
            """
            select conrelid::regclass::text as tbl, a.attname as col
            from pg_constraint co
            join pg_attribute a on a.attrelid = co.conrelid and a.attnum = any(co.conkey)
            where co.confrelid = 'orders'::regclass and co.contype = 'f'
            """
        )
    ).mappings().all()
    oids = [
        row[0]
        for row in db.execute(
            text("select id from orders where merchant_id = :m"), {"m": merchant_id}
        )
    ]
    for oid in oids:
        for r in refs:
            db.execute(
                text(f'delete from "{r["tbl"]}" where "{r["col"]}" = :o'),
                {"o": oid},
            )
        db.execute(text("delete from orders where id = :o"), {"o": oid})
    db.execute(text("delete from shopify_ingress_dlq where merchant_id = :m"), {"m": merchant_id})
    db.execute(text("delete from shopify_rate_quotes where merchant_id = :m"), {"m": merchant_id})
    db.execute(text("delete from shopify_shops where merchant_id = :m"), {"m": merchant_id})
    db.execute(text("delete from merchant_audit_logs where merchant_id = :m"), {"m": merchant_id})
    db.execute(text("delete from merchant_users where merchant_id = :m"), {"m": merchant_id})
    db.execute(text("delete from saved_addresses where merchant_id = :m"), {"m": merchant_id})
    db.execute(text("delete from merchants where id = :m"), {"m": merchant_id})
    db.commit()
    _ = bind  # silence unused if dialect quirks


def main() -> int:
    results: list[Result] = []

    def ok(step: str, detail: str = "") -> None:
        results.append((step, "PASS", detail))
        print(f"PASS {step}: {detail}")

    def fail(step: str, detail: str = "") -> None:
        results.append((step, "FAIL", detail))
        print(f"FAIL {step}: {detail}")

    def skip(step: str, detail: str = "") -> None:
        results.append((step, "SKIP", detail))
        print(f"SKIP {step}: {detail}")

    settings = get_settings()
    shop_domain = f"pc-dummy-{uuid.uuid4().hex[:8]}.myshopify.com"
    print(
        json.dumps(
            {
                "api": API,
                "app_env": settings.app_env,
                "shopify_api_key_set": bool(settings.shopify_api_key),
                "shopify_api_secret_set": bool(settings.shopify_api_secret),
                "shopify_api_version": settings.shopify_api_version,
                "shopify_scopes": settings.shopify_api_scopes,
                "fo_enabled": settings.shopify_fulfillment_service_enabled,
                "shop_domain": shop_domain,
                "keep": KEEP,
            },
            indent=2,
        )
    )

    try:
        r = httpx.get(f"{API}/health", timeout=5)
        assert r.status_code == 200 and r.json().get("status") == "ok"
        ok("API health", r.text[:80])
    except Exception as exc:  # noqa: BLE001
        fail("API health", str(exc))
        return 1

    db: Session = SessionLocal()
    merchant_id: str | None = None
    shop_id: str | None = None
    sandbox_order_id: str | None = None
    live_order_id: str | None = None

    try:
        suffix = uuid.uuid4().hex[:8]
        merchant = Merchant(
            status=MerchantStatus.ACTIVE.value,
            company_name=f"Shopify Infusion Co {suffix}",
            email=f"shopify-infusion-{suffix}@test.invalid",
            payment_terms="NET_30",
            profile={},
            pricing_model="distance",
            pricing_config={
                "schedule": {"timezone": "America/Toronto"},
                "size_tiers": [
                    {"id": "small", "label": "Small", "max_weight_kg": 5},
                    {"id": "medium", "label": "Medium", "max_weight_kg": 20},
                    {"id": "large", "label": "Large", "max_weight_kg": 50},
                ],
            },
        )
        db.add(merchant)
        db.flush()
        pickup = SavedAddress(
            merchant_id=merchant.id,
            label="Warehouse",
            address_type="pickup",
            formatted="100 Queen St W, Toronto, ON M5H 2N2, Canada",
            postal="M5H2N2",
            lat=43.6532,
            lng=-79.3832,
            is_default=True,
        )
        db.add(pickup)
        db.flush()
        shop = ShopifyShop(
            merchant_id=merchant.id,
            shop_domain=shop_domain,
            encrypted_access_token=encrypt_signing_secret(
                DUMMY_ADMIN_TOKEN, encryption_key=settings.jwt_secret
            ),
            encrypted_webhook_secret=encrypt_signing_secret(
                DUMMY_SHOP_WEBHOOK_SECRET, encryption_key=settings.jwt_secret
            ),
            default_pickup_address_id=pickup.id,
            scopes=settings.shopify_api_scopes
            or "read_orders,write_fulfillments,write_shipping",
            installed_at=datetime.now(UTC),
            auto_dispatch=False,
            default_vehicle_class="cargo_van",
            default_package_type="looseParcel",
        )
        db.add(shop)
        db.commit()
        db.refresh(shop)
        merchant_id, shop_id = merchant.id, shop.id
        ok("Infuse dummy Shopify credentials", f"merchant={merchant_id} shop={shop_domain}")

        # --- Merchant connection / go-live surface ---
        try:
            payload = shopify.connection_payload(db, merchant.id, settings)
            shops = payload.get("shops") or []
            go_live = payload.get("go_live") or {}
            token_leaked = any(
                "access_token" in json.dumps(s).lower() or "shpat_" in json.dumps(s)
                for s in shops
            )
            if (
                payload.get("oauth_configured")
                and payload.get("webhook_url")
                and payload.get("carrier_rates_url")
                and shops
                and shops[0].get("connected")
                and shops[0].get("has_webhook_secret")
                and go_live.get("ready") is True
                and not token_leaked
            ):
                ok(
                    "connection_payload + go_live ready",
                    json.dumps(
                        {
                            "webhook_url": payload.get("webhook_url"),
                            "carrier_rates_url": payload.get("carrier_rates_url"),
                            "go_live": go_live,
                            "shop": shops[0],
                        },
                        default=str,
                    )[:400],
                )
            else:
                fail(
                    "connection_payload + go_live ready",
                    json.dumps(payload, default=str)[:500],
                )
        except Exception as exc:  # noqa: BLE001
            fail(
                "connection_payload + go_live ready",
                f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-600:]}",
            )

        try:
            actor = shopify._actor(db, merchant)
            db.commit()
            ctx = MerchantContext(merchant=merchant, user=actor, role=MerchantRole.OWNER)
            # Dummy Admin API token → Shopify Admin 404 must surface in hooks.errors
            live = shopify.go_live(
                db, ctx, settings, shop_id=shop.id, pickup_address_id=pickup.id
            )
            hooks = live.get("hooks") or {}
            errors = hooks.get("errors") or []
            if hooks.get("ok") is False and errors:
                ok(
                    "go_live surfaces Admin API hook failures",
                    json.dumps({"hooks": hooks, "go_live": live.get("go_live")}, default=str)[
                        :350
                    ],
                )
            else:
                fail(
                    "go_live surfaces Admin API hook failures",
                    f"expected hooks.ok=false with errors; got {json.dumps(hooks)[:300]}",
                )
        except Exception as exc:  # noqa: BLE001
            fail("go_live", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-600:]}")

        # --- Security / enqueue ---
        body = b'{"id":1}'
        r = httpx.post(
            f"{API}/v1/integrations/shopify/webhooks",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Shop-Domain": shop_domain,
                "X-Shopify-Topic": "orders/create",
                "X-Shopify-Hmac-Sha256": "not-valid",
            },
            timeout=10,
        )
        (ok if r.status_code == 401 else fail)(
            "Live webhook rejects bad HMAC", f"{r.status_code} {r.text[:120]}"
        )

        unknown = b'{"id":2}'
        if settings.shopify_api_secret:
            r = httpx.post(
                f"{API}/v1/integrations/shopify/webhooks",
                content=unknown,
                headers={
                    "Content-Type": "application/json",
                    "X-Shopify-Shop-Domain": "never-connected-xyz.myshopify.com",
                    "X-Shopify-Topic": "orders/create",
                    "X-Shopify-Hmac-Sha256": _sign(unknown, settings.shopify_api_secret),
                },
                timeout=10,
            )
            (ok if r.status_code == 404 else fail)(
                "Unknown shop → 404", f"{r.status_code} {r.text[:160]}"
            )
        else:
            skip("Unknown shop → 404", "SHOPIFY_API_SECRET empty")

        sandbox_id = int(str(uuid.uuid4().int)[:10])
        sandbox_payload = _order_payload(suffix=suffix, order_id=sandbox_id, test=True)
        sandbox_body = json.dumps(sandbox_payload).encode()
        r = httpx.post(
            f"{API}/v1/integrations/shopify/webhooks",
            content=sandbox_body,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Shop-Domain": shop_domain,
                "X-Shopify-Topic": "orders/create",
                "X-Shopify-Hmac-Sha256": _sign(sandbox_body, DUMMY_SHOP_WEBHOOK_SECRET),
            },
            timeout=15,
        )
        try:
            wh = r.json()
        except Exception:  # noqa: BLE001
            wh = {"raw": r.text}
        if r.status_code == 200 and wh.get("queued"):
            ok("Live orders/create enqueue", json.dumps(wh)[:200])
        elif r.status_code == 503:
            skip("Live orders/create enqueue", f"503 queue unavailable: {r.text[:160]}")
        else:
            fail("Live orders/create enqueue", f"{r.status_code} {r.text[:300]}")

        # --- Carrier rates ---
        rate_body = json.dumps(_rate_payload()).encode()
        r = httpx.post(
            f"{API}/v1/integrations/shopify/carrier-service/rates",
            content=rate_body,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Shop-Domain": shop_domain,
                "X-Shopify-Hmac-Sha256": _sign(rate_body, DUMMY_SHOP_WEBHOOK_SECRET),
            },
            timeout=45,
        )
        try:
            rate_json = r.json()
        except Exception:  # noqa: BLE001
            rate_json = {"raw": r.text}
        rates = rate_json.get("rates") if isinstance(rate_json, dict) else None
        if r.status_code == 200 and isinstance(rates, list) and rates:
            ok("Live CarrierService rates", f"n={len(rates)} first={json.dumps(rates[0])[:240]}")
        elif r.status_code == 200 and rates == []:
            skip("Live CarrierService rates", f"empty rates: {rate_json}")
        else:
            fail("Live CarrierService rates", f"{r.status_code} {str(rate_json)[:300]}")

        # --- Book sandbox parcel ---
        try:
            book = shopify.process_queued_webhook(
                db,
                settings,
                {
                    "action": "shopify_orders_create",
                    "shop_domain": shop_domain,
                    "topic": "orders/create",
                    "raw_body": sandbox_body.decode(),
                },
            )
            if book.get("ok") and book.get("order_id"):
                sandbox_order_id = book["order_id"]
                ok("Book sandbox parcel", json.dumps(book, default=str)[:320])
            else:
                fail("Book sandbox parcel", json.dumps(book, default=str)[:400])
        except Exception as exc:  # noqa: BLE001
            fail(
                "Book sandbox parcel",
                f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-800:]}",
            )

        if sandbox_order_id:
            replay = shopify.process_queued_webhook(
                db,
                settings,
                {
                    "action": "shopify_orders_create",
                    "shop_domain": shop_domain,
                    "topic": "orders/create",
                    "raw_body": sandbox_body.decode(),
                },
            )
            (ok if replay.get("replayed") and replay.get("order_id") == sandbox_order_id else fail)(
                "Idempotent replay", json.dumps(replay, default=str)[:250]
            )

            db.expire_all()
            order = db.get(Order, sandbox_order_id)
            if not order:
                fail("PorterChain sandbox order fields", "missing row")
            else:
                meta = (order.compliance_metadata or {}).get("shopify") or {}
                good = (
                    order.order_source == OrderSource.SHOPIFY.value
                    and (order.idempotency_key or "").startswith(f"shopify:{shop_domain}:")
                    and str(order.purchase_order_number) == str(sandbox_id)
                    and meta.get("shop_domain") == shop_domain
                    and bool(order.is_sandbox)
                )
                (ok if good else fail)(
                    "PorterChain sandbox order fields",
                    json.dumps(
                        {
                            "order_source": order.order_source,
                            "idempotency_key": order.idempotency_key,
                            "po": order.purchase_order_number,
                            "tracking": order.tracking_number,
                            "state": order.state,
                            "is_sandbox": order.is_sandbox,
                            "shopify_meta": meta,
                        },
                        default=str,
                    )[:500],
                )

        # --- Non-sandbox: held_for_ops when auto_dispatch=false ---
        live_id = int(str(uuid.uuid4().int)[:10])
        live_payload = _order_payload(suffix=f"{suffix}-live", order_id=live_id, test=False)
        live_body = json.dumps(live_payload).encode()
        try:
            live_book = shopify.process_queued_webhook(
                db,
                settings,
                {
                    "action": "shopify_orders_create",
                    "shop_domain": shop_domain,
                    "topic": "orders/create",
                    "raw_body": live_body.decode(),
                },
            )
            if live_book.get("ok") and live_book.get("order_id"):
                live_order_id = live_book["order_id"]
                held = live_book.get("held_for_ops") is True
                (ok if held else fail)(
                    "Non-sandbox held_for_ops (auto_dispatch=false)",
                    json.dumps(live_book, default=str)[:320],
                )
            else:
                fail("Non-sandbox book", json.dumps(live_book, default=str)[:400])
        except Exception as exc:  # noqa: BLE001
            fail(
                "Non-sandbox book",
                f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-800:]}",
            )

        # --- Ingress pause → DLQ ---
        shop.ingress_paused = True
        db.commit()
        paused_id = int(str(uuid.uuid4().int)[:10])
        paused_payload = _order_payload(suffix=f"{suffix}-pause", order_id=paused_id, test=True)
        paused_body = json.dumps(paused_payload).encode()
        paused_res = shopify.process_queued_webhook(
            db,
            settings,
            {
                "action": "shopify_orders_create",
                "shop_domain": shop_domain,
                "topic": "orders/create",
                "raw_body": paused_body.decode(),
            },
        )
        dlq = list_ingress_dlq(db, merchant.id, status="held")
        pause_ok = (
            paused_res.get("skipped") == "ingress_paused"
            and any(
                row.reason_code == REASON_INGRESS_PAUSED
                and str(row.shopify_order_id) == str(paused_id)
                for row in dlq
            )
        )
        (ok if pause_ok else fail)(
            "Ingress pause → DLQ hold",
            json.dumps(
                {
                    "result": paused_res,
                    "dlq": [
                        {
                            "reason": d.reason_code,
                            "shopify_order_id": d.shopify_order_id,
                            "status": d.status,
                        }
                        for d in dlq
                    ],
                },
                default=str,
            )[:400],
        )
        shop.ingress_paused = False
        db.commit()

        # --- Cancel ---
        cancel_payload = {"id": sandbox_id, "name": sandbox_payload["name"]}
        cancel_body = json.dumps(cancel_payload).encode()
        r = httpx.post(
            f"{API}/v1/integrations/shopify/webhooks",
            content=cancel_body,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Shop-Domain": shop_domain,
                "X-Shopify-Topic": "orders/cancelled",
                "X-Shopify-Hmac-Sha256": _sign(cancel_body, DUMMY_SHOP_WEBHOOK_SECRET),
            },
            timeout=15,
        )
        (ok if r.status_code in (200, 503) else fail)(
            "Cancel webhook HTTP", f"{r.status_code} {r.text[:160]}"
        )
        if sandbox_order_id:
            try:
                cancel_res = shopify.process_queued_webhook(
                    db,
                    settings,
                    {
                        "action": "shopify_orders_cancelled",
                        "shop_domain": shop_domain,
                        "topic": "orders/cancelled",
                        "raw_body": cancel_body.decode(),
                    },
                )
                ok("Cancel from Shopify payload", json.dumps(cancel_res, default=str)[:250])
            except Exception as exc:  # noqa: BLE001
                fail("Cancel from Shopify payload", f"{type(exc).__name__}: {exc}")

        # --- OAuth install + FO gate + quotes ---
        r = httpx.get(
            f"{API}/v1/integrations/shopify/install",
            params={"shop": shop_domain, "merchant_id": merchant_id},
            follow_redirects=False,
            timeout=10,
        )
        loc = r.headers.get("location") or ""
        if r.status_code in (302, 307) and "myshopify.com" in loc:
            ok("OAuth install redirect", f"{r.status_code} → {loc.split('?')[0]}?…")
        elif r.status_code == 400:
            skip("OAuth install redirect", r.text[:160])
        else:
            fail("OAuth install redirect", f"{r.status_code} {loc[:120]} {r.text[:120]}")

        quotes = (
            db.query(ShopifyRateQuote).filter(ShopifyRateQuote.shop_id == shop_id).all()
            if shop_id
            else []
        )
        if quotes:
            ok(
                "ShopifyRateQuote persisted",
                "; ".join(f"cents={q.total_cents}" for q in quotes),
            )
        else:
            skip("ShopifyRateQuote persisted", "none")

        fo_body = b'{"kind":"FULFILLMENT_REQUEST"}'
        r = httpx.post(
            f"{API}/v1/integrations/shopify/fulfillment-order-notification",
            content=fo_body,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Shop-Domain": shop_domain,
                "X-Shopify-Hmac-Sha256": _sign(fo_body, DUMMY_SHOP_WEBHOOK_SECRET),
            },
            timeout=10,
        )
        ok(
            "FO notification endpoint",
            f"fo_enabled={settings.shopify_fulfillment_service_enabled} "
            f"status={r.status_code} body={r.text[:180]}",
        )

        app_toml = Path(__file__).resolve().parents[3] / "integrations" / "shopify" / "app.toml"
        toml_text = app_toml.read_text() if app_toml.exists() else ""
        scopes = set(x.strip() for x in (settings.shopify_api_scopes or "").split(",") if x.strip())
        required = {"read_orders", "write_fulfillments", "write_shipping"}
        readiness = {
            "oauth_keys_in_api_env": bool(settings.shopify_api_key and settings.shopify_api_secret),
            "scopes_missing": sorted(required - scopes),
            "app_toml_client_id_empty_intentional": 'client_id = ""' in toml_text,
            "fo_accept_enabled": bool(settings.shopify_fulfillment_service_enabled),
            "sandbox_order_id": sandbox_order_id,
            "live_held_order_id": live_order_id,
        }
        (ok if not readiness["scopes_missing"] else fail)(
            "Provider readiness snapshot", json.dumps(readiness)
        )

    except Exception as exc:  # noqa: BLE001
        fail("Probe crashed", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-1000:]}")
    finally:
        if merchant_id and not KEEP:
            try:
                _cleanup_merchant(db, merchant_id)
                ok("Cleanup", "removed infusion rows")
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                fail("Cleanup", str(exc)[:400])
        elif merchant_id and KEEP:
            skip("Cleanup", f"SHOPIFY_PROBE_KEEP=1 merchant_id={merchant_id}")
        db.close()

    print("\n=== SUMMARY ===")
    for step, status, _detail in results:
        print(f"{status:4} | {step}")
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    skipped = sum(1 for _, s, _ in results if s == "SKIP")
    print(f"\nPASS={passed} FAIL={failed} SKIP={skipped}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
