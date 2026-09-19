"""AX — dispatcher books, accounting bills, viewer tracks; English 403; schema parity."""

from __future__ import annotations

import re
from pathlib import Path

from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import (
    forbidden_message,
    modules_for_role,
    organization_permission_roles,
    permissions_catalog,
)

_SCHEMA = Path(__file__).resolve().parents[1] / "src/porterchain_api/authz/schema.zed"


def test_dispatcher_books_not_bills_or_invites() -> None:
    mods = modules_for_role(MerchantRole.OPS)
    assert {"dashboard", "book", "routes", "orders", "orders_write", "tracking", "claims"} <= mods
    assert "billing" not in mods
    assert "users" not in mods
    assert "api_keys" not in mods
    assert "settings" not in mods
    assert "reports" not in mods


def test_accounting_bills_not_routes() -> None:
    mods = modules_for_role(MerchantRole.FINANCE)
    assert {"dashboard", "billing", "invoices", "statements", "reports"} <= mods
    assert "book" not in mods
    assert "routes" not in mods
    assert "orders_write" not in mods
    assert "users" not in mods
    assert "api_keys" not in mods
    assert "settings" not in mods


def test_viewer_tracks_read_only() -> None:
    mods = modules_for_role(MerchantRole.READONLY)
    assert {"dashboard", "orders", "tracking"} <= mods
    assert "book" not in mods
    assert "orders_write" not in mods
    assert "billing" not in mods
    assert "invoices" not in mods
    assert "reports" not in mods
    assert "api_keys" not in mods
    assert "settings" not in mods


def test_forbidden_names_the_job() -> None:
    assert forbidden_message("billing") == "Ask your owner for Accounting access."
    assert forbidden_message("book") == "Ask your owner for Dispatcher access."
    assert forbidden_message("users") == "Ask your owner for Manager access."
    assert forbidden_message("claims") == "Ask your owner for access to Claims."
    catalog = permissions_catalog()
    dispatcher = next(r for r in catalog["roles"] if r["label"] == "Dispatcher")
    assert "Booking" in dispatcher["module_labels"]
    assert "Billing" not in dispatcher["module_labels"]
    accounting = next(r for r in catalog["roles"] if r["label"] == "Accounting")
    assert "Billing" in accounting["module_labels"]
    assert "Route planner" not in accounting["module_labels"]


def test_organization_schema_matches_module_matrix() -> None:
    schema = _SCHEMA.read_text(encoding="utf-8")
    block = re.search(r"definition organization \{(.*?)\}", schema, flags=re.DOTALL)
    assert block, "organization definition missing"
    declared: dict[str, set[str]] = {}
    for name, expr in re.findall(r"(?m)^\s*permission\s+(\w+)\s*=\s*(.+)$", block.group(1)):
        declared[name] = {part.strip() for part in expr.split("+")}
    expected = organization_permission_roles()
    missing = [perm for perm in expected if perm not in declared]
    assert not missing, f"schema.zed missing organization permissions: {missing}"
    drifted = []
    for perm, roles in expected.items():
        got = declared[perm] - {"member"}
        want = set(roles) - {"member"}
        if got != want:
            drifted.append(f"{perm}: schema={sorted(got)} matrix={sorted(want)}")
    assert not drifted, "schema.zed organization permissions drifted from MODULE_PERMISSIONS: " + "; ".join(
        drifted
    )
