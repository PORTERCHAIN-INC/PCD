from types import SimpleNamespace

from porterchain_api.pricing_engine import smart_apply, smart_pricing
from porterchain_pricing import GeoPoint, PricingRequest
from porterchain_pricing.types import PriceBreakdown, PriceLineItem


def _base():
    b = PriceBreakdown(items=[PriceLineItem("stop_price", "Stop", 2500), PriceLineItem("liftgate", "Liftgate", 5000)])
    return b.finalize()


def _req():
    return PricingRequest(pickup=GeoPoint(lat=43.6, lng=-79.6, formatted="a", postal="L4Z"),
                          dropoff=GeoPoint(lat=43.65, lng=-79.38, formatted="b", postal="M5V"),
                          vehicle_class="cargo_van", channel="merchant", merchant_id="m1")


class DB:
    def __init__(self, m):
        self.m = m

    def get(self, _model, _id):
        return self.m


def test_not_opted_in_keeps_exact_price(monkeypatch):
    m = SimpleNamespace(id="m1", pricing_config={})
    monkeypatch.setattr(smart_pricing, "merchant_opted_in", lambda db, mm: False)
    base = _base()
    assert smart_apply.apply_smart(DB(m), _req(), base) is base


def test_opted_in_replaces_route_keeps_addons(monkeypatch):
    m = SimpleNamespace(id="m1", pricing_config={})
    monkeypatch.setattr(smart_pricing, "merchant_opted_in", lambda db, mm: True)
    monkeypatch.setattr(smart_pricing, "quote_route", lambda db, **kw: {
        "total_cents": 3100, "shape": "1P-1D", "custom_quote": False, "route_km": 25.0, "confidence": 0.9})
    out = smart_apply.apply_smart(DB(m), _req(), _base())
    assert out.final_cents == 3100 + 5000
    assert {i.code for i in out.items} == {"route_price", "liftgate"}
    assert out.metadata["smart_pricing"]["previous_final_cents"] == 7500


def test_custom_quote_falls_back(monkeypatch):
    m = SimpleNamespace(id="m1", pricing_config={})
    monkeypatch.setattr(smart_pricing, "merchant_opted_in", lambda db, mm: True)
    monkeypatch.setattr(smart_pricing, "quote_route", lambda db, **kw: {"total_cents": 1, "custom_quote": True})
    base = _base()
    assert smart_apply.apply_smart(DB(m), _req(), base) is base


def test_opt_in_state_records_who_and_when():
    m = SimpleNamespace(pricing_config={"other": 1})
    st = smart_apply.set_opt_in(m, enabled=True, actor="ops@shop.ca")
    assert st["opted_in"] and st["opted_in_at"] and m.pricing_config["other"] == 1
    assert m.pricing_config["smart_pricing"]["opted_by"] == "ops@shop.ca"
    assert smart_apply.dismiss_banner(m)["dismissed_at"]
