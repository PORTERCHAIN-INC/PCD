"""Integration adapter protocol — ERP / platform inbound (§7 · PLT-G4)."""

from __future__ import annotations

from typing import Any, Protocol

from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest


class ErpFulfillmentAdapter(Protocol):
    """Map external ERP fulfillment payload to a merchant booking request."""

    def map_fulfillment(self, payload: dict[str, Any]) -> MerchantBookDeliveryRequest:
        """Raise ValueError with stable code (e.g. address_required) on invalid input."""
        ...

