"""NetSuite adapter tests (§7.2.3)."""

from __future__ import annotations

import pytest

from porterchain_api.integrations.netsuite_adapter import map_netsuite_fulfillment
from porterchain_api.integrations.zapier_catalog import zapier_catalog


def test_map_netsuite_fulfillment():
    body = map_netsuite_fulfillment(
        {
            "external_id": "IF-99",
            "ship_date": "2026-07-09T14:00:00Z",
            "pickup_address": {"formatted": "1 King St W, Toronto", "lat": 43.65, "lng": -79.38},
            "ship_address": {"formatted": "2 Bay St, Toronto", "lat": 43.64, "lng": -79.37},
            "purchase_order": "PO-1",
        }
    )
    assert body.internal_reference == "IF-99"
    assert body.purchase_order_number == "PO-1"
    assert body.pickup.formatted.startswith("1 King")


def test_map_netsuite_requires_external_id():
    with pytest.raises(ValueError, match="external_id_required"):
        map_netsuite_fulfillment({"ship_address": {"formatted": "x"}, "pickup_address": {"formatted": "y"}})


def test_zapier_catalog_loads_templates():
    catalog = zapier_catalog()
    assert catalog["template_count"] >= 4
    assert any(t["id"] == "new-shipment-webhook" for t in catalog["templates"])
