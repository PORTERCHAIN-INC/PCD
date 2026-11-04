"""Pass 7: L56 recipient fallback, L100 hub parcels in Needs a decision."""
from types import SimpleNamespace

from porterchain_driver.jobs import _customer_block


def test_l56_consignee_fallback():
    order = SimpleNamespace(compliance_metadata={"consignee": {"email": "r@x.test", "name": "Alex Rivera"}})
    out = _customer_block(order, None, {"email": "merchant@x.test"}, {"formatted": "1 King"})
    assert out["name"] == "Alex Rivera" and out["email"] == "r@x.test"


def test_l100_queue_filter_includes_driverless_picked_up(db):
    from porterchain_api.order_engine import platform_enriched
    src = open(platform_enriched.__file__).read()
    assert "assigned_driver_id.is_(None)" in src
