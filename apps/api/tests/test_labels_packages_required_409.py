"""Labels on an order with no packages → 409 + actionable copy (was a silent 404)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from porterchain_api.reporting.label_service import PackagesRequired


def _raise_packages_required(*_a, **_k):
    raise PackagesRequired("packages_required")


def test_merchant_labels_without_packages_is_409(monkeypatch):
    from porterchain_api.routers.merchant import orders_tracking as mod

    monkeypatch.setattr(mod, "require_module", lambda *_a, **_k: None)
    with pytest.raises(HTTPException) as exc:
        mod._invoke(object(), "orders", _raise_packages_required)  # type: ignore[arg-type]
    assert exc.value.status_code == 409
    assert "Add packages" in str(exc.value.detail)


def test_admin_labels_without_packages_is_409(monkeypatch):
    from porterchain_api.routers.admin import orders as mod

    monkeypatch.setattr(mod, "require_module", lambda *_a, **_k: None)
    with pytest.raises(HTTPException) as exc:
        mod._invoke(object(), "orders_read", _raise_packages_required)
    assert exc.value.status_code == 409
    assert "packages" in str(exc.value.detail).lower()


def test_other_lookup_errors_stay_404(monkeypatch):
    from porterchain_api.routers.merchant import orders_tracking as mod

    def _missing(*_a, **_k):
        raise LookupError("order_not_found")

    monkeypatch.setattr(mod, "require_module", lambda *_a, **_k: None)
    with pytest.raises(HTTPException) as exc:
        mod._invoke(object(), "orders", _missing)  # type: ignore[arg-type]
    assert exc.value.status_code == 404
