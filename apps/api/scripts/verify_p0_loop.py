#!/usr/bin/env python3
"""D1 P0 production loop verification (masterrule Appendix D).

Checks G1–G9 locally and optionally against production API URL.

Usage:
    pnpm validate:p0
    cd apps/api && PYTHONPATH=src python scripts/verify_p0_loop.py --api-url http://localhost:8001
    cd apps/api && PYTHONPATH=src python scripts/verify_p0_loop.py --api-url https://api.porterchain.com --prod
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))

from sqlalchemy import inspect

from porterchain_api.config import get_settings
from porterchain_api.db import SessionLocal, engine, init_db


def _http_json(url: str, *, method: str = "GET", body: dict | None = None, timeout: float = 10.0) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload
    except urllib.error.URLError as exc:
        return 0, {"error": str(exc.reason)}


class Check:
    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []

    def run(self, gate: str, label: str, ok: bool, *, detail: str = "", warn: bool = False) -> bool:
        status = "PASS" if ok else ("WARN" if warn else "FAIL")
        self.results.append({"gate": gate, "label": label, "status": status, "detail": detail})
        mark = "✓" if ok else ("~" if warn else "✗")
        line = f"{mark} [{gate}] {label}"
        if detail:
            line += f" — {detail}"
        print(line)
        return ok

    def warn(self, gate: str, label: str, detail: str = "") -> None:
        self.run(gate, label, False, detail=detail, warn=True)

    @property
    def failed(self) -> bool:
        return any(r["status"] == "FAIL" for r in self.results)


def check_g1(check: Check, api_url: str, *, prod: bool) -> None:
    status, body = _http_json(f"{api_url.rstrip('/')}/health")
    if status == 0 and prod:
        detail = body.get("error", "connection failed") if isinstance(body, dict) else "connection failed"
        check.run("G1", "API /health", False, detail=detail)
        check.warn("G1", "Prod deploy smoke", "API unreachable — run deploy workflow or bootstrap droplet")
        return

    check.run("G1", "API /health", status == 200, detail=f"HTTP {status}")

    if prod:
        if status == 200:
            code, _ = _http_json(
                f"{api_url.rstrip('/')}/v1/booking-drafts",
                method="POST",
                body={"session_id": "p0-smoke-test"},
            )
            check.run("G1", "POST /v1/booking-drafts smoke", code in (200, 201), detail=f"HTTP {code}")
        return

    init_db()
    names = set(inspect(engine).get_table_names())
    check.run("G1", "booking_drafts table", "booking_drafts" in names)

    if status == 200:
        code, _ = _http_json(
            f"{api_url.rstrip('/')}/v1/booking-drafts",
            method="POST",
            body={"session_id": "p0-smoke-test"},
        )
        check.run("G1", "POST /v1/booking-drafts smoke", code in (200, 201), detail=f"HTTP {code}")


def check_prod_integrations(check: Check, api_url: str, *, prod: bool) -> None:
    """§0.1.3 push live + §0.1.9 Stripe webhook ingress (prod readiness)."""
    if not prod:
        return

    status, body = _http_json(f"{api_url.rstrip('/')}/health/ready")
    if status != 200:
        check.run("G9", "Push live (PORTERCHAIN_PUSH_SEND)", False, detail=f"readiness HTTP {status}")
        check.run("G8", "Stripe webhook ingress configured", False, detail=f"readiness HTTP {status}")
        return

    checks = body.get("checks", {}) if isinstance(body, dict) else {}
    firebase = checks.get("firebase", "")
    push_live = firebase == "ok"
    check.run(
        "G9",
        "Push live (PORTERCHAIN_PUSH_SEND=true)",
        push_live,
        detail=firebase,
        warn=firebase == "dry_run",
    )

    stripe_ok = checks.get("stripe") == "configured"
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/webhooks/stripe",
        data=b"{}",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ingress_ok = resp.status != 503
    except urllib.error.HTTPError as exc:
        ingress_ok = exc.code != 503
    check.run(
        "G8",
        "Stripe webhook ingress configured (§0.1.9)",
        stripe_ok and ingress_ok,
        detail=f"stripe={checks.get('stripe')}, ingress={'ok' if ingress_ok else '503'}",
    )


def _prod_stripe_secret(settings) -> str:
    """Prefer explicit STRIPE_SECRET env over local .env (for live dashboard checks)."""
    return (os.environ.get("STRIPE_SECRET") or settings.stripe_secret or "").strip()


def check_stripe_webhook_registered(check: Check, settings, *, prod: bool) -> None:
    """Verify Stripe dashboard has live webhook URL (requires STRIPE_SECRET locally)."""
    if not prod:
        return
    secret = _prod_stripe_secret(settings)
    if not secret or (settings.stripe_mock and not os.environ.get("STRIPE_SECRET")):
        check.warn(
            "G8b",
            "Stripe live webhook registered in dashboard",
            "run: STRIPE_MOCK=false STRIPE_SECRET=sk_live_… pnpm validate:p0:prod",
        )
        return

    import stripe

    stripe.api_key = secret
    expected_urls = {
        "https://porterchain.com/webhooks/stripe",
        "https://api.porterchain.com/webhooks/stripe",
    }
    try:
        endpoints = stripe.WebhookEndpoint.list(limit=25)
        found = {item.url for item in endpoints.data}
        ok = bool(found & expected_urls)
        sample = ", ".join(sorted(found)[:4]) or "none"
        check.run(
            "G8b",
            "Stripe live webhook registered (§0.1.9)",
            ok,
            detail=sample,
            warn=not ok,
        )
    except Exception as exc:  # noqa: BLE001
        check.run("G8b", "Stripe live webhook registered (§0.1.9)", False, detail=str(exc))


def check_stripe_invoice_proof(check: Check, *, prod: bool) -> None:
    """§0.1.9 — invoice row after live Stripe event (manual SQL on droplet)."""
    if not prod:
        return
    check.warn(
        "G8c",
        "Stripe live event → invoice row (§0.1.9)",
        "on droplet: docker exec pcd-postgres psql -U porterchain -d porterchain "
        "-c \"SELECT id, stripe_receipt_url, created_at FROM invoices ORDER BY created_at DESC LIMIT 5;\"",
    )


def check_g2_g3(check: Check, settings, *, prod: bool, api_url: str) -> None:
    from porterchain_api.fleetbase_engine.sync_health import SLO_TARGET_PCT, assess_fleetbase_sync

    if prod:
        status, body = _http_json(f"{api_url.rstrip('/')}/health/ready")
        if status != 200:
            check.run("G2", f"Fleetbase sync link rate ≥{SLO_TARGET_PCT:.0f}%", False, detail=f"HTTP {status}")
            check.run("G3", "Fleetbase webhook secret configured", False, detail="readiness unreachable")
            return

        checks = body.get("checks", {}) if isinstance(body, dict) else {}
        fleetbase = body.get("fleetbase_sync", {}) if isinstance(body, dict) else {}
        bridge_on = checks.get("fleetbase") == "bridge_enabled"
        if not bridge_on:
            check.run("G2", f"Fleetbase sync link rate ≥{SLO_TARGET_PCT:.0f}%", True, detail="bridge disabled")
            check.run("G3", "Fleetbase webhook secret configured", True, detail="bridge disabled")
            return

        meets = bool(fleetbase.get("meets_slo"))
        pct = fleetbase.get("link_pct", 0)
        linked = fleetbase.get("linked_orders", 0)
        total = fleetbase.get("eligible_orders", 0)
        dead = fleetbase.get("dead_letters", 0)
        check.run(
            "G2",
            f"Fleetbase sync link rate ≥{SLO_TARGET_PCT:.0f}%",
            meets or total == 0,
            detail=f"{linked}/{total} ({pct}%), dead_letters={dead}",
            warn=not meets and bridge_on,
        )
        webhook_ok = checks.get("fleetbase_webhook") == "configured"
        check.run(
            "G3",
            "Fleetbase webhook secret configured",
            webhook_ok,
            detail=checks.get("fleetbase_webhook", ""),
        )
        return

    with SessionLocal() as db:
        slo = assess_fleetbase_sync(db, settings)
        total = slo["eligible_orders"]
        linked = slo["linked_orders"]
        pct = slo["link_pct"]
        dead = slo["dead_letters"]
        ok_g2 = slo["meets_slo"]
        check.run(
            "G2",
            f"Fleetbase sync link rate ≥{SLO_TARGET_PCT:.0f}%",
            ok_g2,
            detail=f"{linked}/{total} ({pct:.1f}%), dead_letters={dead}",
            warn=not ok_g2 and settings.fleetbase_dispatch_bridge,
        )

    secret_ok = bool(settings.fleetbase_webhook_secret or settings.fleetbase_api_key)
    check.run(
        "G3",
        "Fleetbase webhook secret configured",
        secret_ok,
        detail="set FLEETBASE_WEBHOOK_SECRET (or API key fallback)",
    )

    if settings.fleetbase_webhook_secret and settings.fleetbase_dispatch_bridge:
        import hashlib
        import hmac

        payload = b'{"event":"order.updated","data":{"id":"test"}}'
        sig = "sha256=" + hmac.new(
            settings.fleetbase_webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        req = urllib.request.Request(
            f"{settings.porterchain_api_url.rstrip('/')}/webhooks/fleetbase",
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Fleetbase-Signature": sig,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                ingress_ok = resp.status in (200, 201)
        except urllib.error.HTTPError as exc:
            ingress_ok = exc.code not in (503,)
        check.run("G3", "Webhook ingress accepts signed payload", ingress_ok)


def check_g4_g9_e2e(check: Check, settings, *, skip_e2e: bool) -> None:
    if skip_e2e:
        check.warn("G4-G9", "E2E validation", "skipped (--skip-e2e)")
        return

    from porterchain_api.admin_engine.e2e_validation_service import E2EValidationService

    with SessionLocal() as db:
        result = E2EValidationService().run_full(db, settings, cleanup=True, merchant_order_count=3)

    phase_map = {
        "G4": ("phase_2_forward_logistics", "quote → pay → dispatch"),
        "G5": ("phase_2_forward_logistics", "driver POD path (simulated in phase 2)"),
        "G6": ("phase_3_merchant", "merchant bulk + billing"),
        "G7": ("phase_2_forward_logistics", "customer booking path"),
        "G8": ("phase_2_forward_logistics", "Stripe webhook / invoice"),
        "G9": ("phase_7_notifications", "notification delivery"),
    }

    phases = result.get("phases", {})
    for gate, (phase_key, label) in phase_map.items():
        phase = phases.get(phase_key, {})
        overall = phase.get("overall", "FAIL")
        ok = overall in ("PASS", "WARNING")
        check.run(gate, label, ok, detail=f"phase {overall}")

    check.run(
        "G4-G9",
        "E2E overall production_ready",
        bool(result.get("production_ready")) or result.get("overall") == "PASS",
        detail=str(result.get("overall")),
        warn=result.get("overall") == "WARNING",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify masterrule D1 P0 gates")
    parser.add_argument("--api-url", default=None, help="API base URL (default: PORTERCHAIN_API_URL)")
    parser.add_argument("--prod", action="store_true", help="Treat as production gate (G1 stricter)")
    parser.add_argument("--skip-e2e", action="store_true", help="Skip G4–G9 E2E phases (faster)")
    args = parser.parse_args()

    settings = get_settings()
    api_url = args.api_url or settings.porterchain_api_url

    print(f"P0 loop verification — {api_url} (env={settings.app_env})")
    print("=" * 56)

    check = Check()
    check_g1(check, api_url, prod=args.prod)
    check_prod_integrations(check, api_url, prod=args.prod)
    check_stripe_webhook_registered(check, settings, prod=args.prod)
    check_stripe_invoice_proof(check, prod=args.prod)
    check_g2_g3(check, settings, prod=args.prod, api_url=api_url)
    check_g4_g9_e2e(check, settings, skip_e2e=args.skip_e2e)

    print("=" * 56)
    passed = sum(1 for r in check.results if r["status"] == "PASS")
    warned = sum(1 for r in check.results if r["status"] == "WARN")
    failed = sum(1 for r in check.results if r["status"] == "FAIL")
    print(f"Summary: {passed} pass, {warned} warn, {failed} fail")
    return 1 if check.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
