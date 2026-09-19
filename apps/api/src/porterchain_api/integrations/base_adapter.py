"""Integration adapter protocol — ERP / platform inbound (§7 · PLT-G4)."""

from __future__ import annotations

from typing import Any, Protocol

from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest


class ErpFulfillmentAdapter(Protocol):
    """Map external ERP fulfillment payload to a merchant booking request."""

    def map_fulfillment(self, payload: dict[str, Any]) -> MerchantBookDeliveryRequest:
        """Raise ValueError with stable code (e.g. address_required) on invalid input."""
        ...


def adapter_module_version(module_name: str) -> str:
    """Parse ``Adapter-Version:`` from module docstring if present."""
    import importlib

    mod = importlib.import_module(module_name)
    doc = mod.__doc__ or ""
    for line in doc.splitlines():
        if "Adapter-Version:" in line:
            return line.split(":", 1)[1].strip()
    return "0.1.0"
