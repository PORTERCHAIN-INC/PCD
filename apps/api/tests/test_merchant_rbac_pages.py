"""AJ — roles map to English pages; no internal module keys in copy."""

from __future__ import annotations

from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import (
    forbidden_message,
    module_label,
    modules_for_role,
    permissions_catalog,
)


def test_viewer_cannot_open_billing_or_team() -> None:
    mods = modules_for_role(MerchantRole.READONLY)
    assert "dashboard" in mods
    assert "orders" in mods
    assert "billing" not in mods
    assert "invoices" not in mods
    assert "reports" not in mods
    assert "settings" not in mods
    assert "users" not in mods
    assert "book" not in mods
    assert "orders_write" not in mods
    assert "claims" not in mods


def test_accounting_can_bill_not_book() -> None:
    mods = modules_for_role(MerchantRole.FINANCE)
    assert "billing" in mods
    assert "claims" in mods
    assert "book" not in mods
    assert "routes" not in mods
    assert "users" not in mods
    assert "settings" not in mods


def test_forbidden_and_catalog_are_english() -> None:
    assert module_label("billing") == "Billing"
    assert module_label("claims") == "Claims"
    assert forbidden_message("billing") == "Ask your owner for Accounting access."
    for module in ("billing", "users", "claims", "book", "orders_write"):
        text = forbidden_message(module)
        assert module not in text
        assert "_" not in text

    catalog = permissions_catalog()
    viewer = next(r for r in catalog["roles"] if r["label"] == "Viewer")
    assert "Billing" not in viewer["module_labels"]
    assert "Overview" in viewer["module_labels"]
    assert all("merchant_" not in label for label in viewer["module_labels"])

    billing = next(m for m in catalog["modules"] if m["module"] == "billing")
    assert billing["label"] == "Billing"
    assert billing["role_labels"] == ["Owner", "Manager", "Accounting"]
    assert "merchant_finance" not in billing["role_labels"]
