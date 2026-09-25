#!/usr/bin/env python3
"""§2.5.6 / DD-24 — list endpoints must expose pagination (limit) or be allowlisted."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTERS = ROOT / "apps/api/src/porterchain_api/routers"

# Service-capped or bounded-domain lists — shrink over time; no new entries.
_LEGACY_UNPAGINATED_LISTS: frozenset[str] = frozenset(
    {
        "operations.py:board",
        "operations.py:assignable_drivers",
        "drivers_admin.py:driver_orders",
        "drivers_admin.py:driver_vehicles",
        "drivers_admin.py:driver_timeline",
        "drivers_admin.py:driver_activities",
        "drivers_admin.py:driver_tasks",
        "merchant/billing.py:list_invoices",
        "merchant/billing.py:list_billing_payments",
        "merchant/billing.py:list_credit_notes",
        "merchant/billing.py:billing_history",
        "merchant/profile_team.py:list_addresses",
        "merchant/profile_team.py:list_recipients",
        "merchant/profile_team.py:list_contacts",
        "merchant/profile_team.py:list_team",
        "merchant/integrations.py:list_api_keys",
        "merchant/integrations.py:list_webhooks",
        "merchant/dashboard_booking.py:booking_list_templates",
        "merchant/dashboard_booking.py:booking_saved_addresses",
        "merchant/dashboard_booking.py:booking_recipients",
        "merchants.py:merchant_unprovisioned_signups",
        "merchant/route_imports.py:list_route_import_profiles",        "merchants.py:merchant_orders",
        "merchants.py:merchant_team",
        "merchants.py:merchant_timeline",
        "merchants.py:merchant_contacts",
        "merchants.py:merchant_contracts",
        "merchants.py:merchant_invoices",
        "merchants.py:merchant_activities",
        "merchants.py:merchant_tasks",
        "customers.py:list_my_support_tickets",
        "orders.py:list_customer_orders",
        "driver/support.py:list_support",
        "driver/support.py:list_driver_claims",
        "driver/support.py:list_incidents",
        "driver/shift.py:list_documents",
        "notifications_admin.py:templates",
        "admin/claims.py:list_claims",
        "admin/dashboard.py:dispatch_queue",
        "admin/finance.py:finance_collections",
        "admin/finance.py:finance_export_gl",
        "admin/finance.py:finance_list_invoices",
        "admin/finance.py:finance_list_payments",
        "admin/finance.py:finance_list_payouts",
        "admin/finance.py:finance_ledger",
        # Moved from admin/orders.py — still service-capped / bounded drafts.
        "admin/booking_drafts.py:booking_draft_abandoned",
        "admin/booking_drafts.py:list_booking_drafts",
        # Moved from admin/settings.py when staff routes split out. Active staff only.
        "admin/settings_directory.py:list_staff",
        "collaboration.py:list_tasks",
        "merchant/standing_orders.py:list_standing_orders",
        "merchants.py:merchant_subsidiaries",
        "merchants.py:merchant_standing_orders",
        "merchants.py:merchant_credit_notes",
        "merchants.py:merchant_webhook_deliveries",
        "merchants.py:list_merchant_billing_contacts",
        "admin/leads.py:leads_pipeline_board",
        "admin/leads.py:list_lead_identities",
        "admin/leads.py:list_lead_conversations",
        "pricing_components.py:list_fsa_rates",
        "admin/route_templates.py:list_route_templates",
        # Bounded author directories (small catalog, not unbounded ops lists).
        "admin/blog_authors.py:list_blog_authors",
        "public_blog.py:list_public_authors",
    }
)


def _rel_router(path: Path) -> str:
    return str(path.relative_to(ROUTERS))


def _has_router_get(decorators: list[ast.expr]) -> bool:
    for dec in decorators:
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
            if dec.func.attr == "get":
                return True
        if isinstance(dec, ast.Attribute) and dec.attr == "get":
            return True
    return False


def _returns_list(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if node.returns is None:
        return False
    try:
        ann = ast.unparse(node.returns)
    except Exception:
        return False
    return ann.startswith("list") or "list[" in ann


def _param_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    args = node.args
    for arg in args.posonlyargs + args.args + args.kwonlyargs:
        names.add(arg.arg)
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    return names


def _scan_file(path: Path) -> list[tuple[str, bool, bool]]:
    rel = _rel_router(path)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    rows: list[tuple[str, bool, bool]] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _has_router_get(node.decorator_list):
            continue
        if not _returns_list(node):
            continue
        has_limit = "limit" in _param_names(node)
        key = f"{rel}:{node.name}"
        rows.append((key, has_limit, key in _LEGACY_UNPAGINATED_LISTS))
    return rows


def main() -> int:
    failures: list[str] = []
    paginated = 0
    legacy = 0
    for path in sorted(ROUTERS.rglob("*.py")):
        if path.name.startswith("_"):
            continue
        for key, has_limit, is_legacy in _scan_file(path):
            if has_limit:
                paginated += 1
                continue
            if is_legacy:
                legacy += 1
                continue
            failures.append(f"list GET without limit param: {key}")

    print("List pagination guard (§2.5.6)")
    print(f"  paginated: {paginated}")
    print(f"  legacy allowlist: {legacy}")
    if failures:
        print("  FAIL:")
        for item in failures:
            print(f"    - {item}")
        return 1
    print("  PASS: no new unpaginated list endpoints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
