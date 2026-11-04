"""Doc 72: one Standard card — engine examples and the pricing admin API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_pricing.standard_card import (
    Item,
    ManualQuoteRequired,
    OrgPricing,
    band_for,
    margin_colour,
    quote,
    sample_basket_preview,
    standard_v1,
)

L = standard_v1()


def test_worked_examples():
    sofa = quote([Item(kind="furniture", furniture_class="F3", weight_kg=50)], "Z1", add_ons={"dolly": 1, "stairs_floor": 2})
    assert sofa["subtotal_cents"] == 16900  # XL 129 + dolly 20 + stairs 2x10
    assert sofa["hst_cents"] == 2197
    flowers = quote([Item(weight_kg=2, length_cm=40, width_cm=30, height_cm=20)], "Z1", add_ons={"same_day": 1, "signature": 1})
    assert flowers["subtotal_cents"] == 4100
    pallet = quote([Item(kind="pallet", weight_kg=300, length_cm=120, width_cm=100, height_cm=150)], "Z2")
    assert pallet["subtotal_cents"] == 11000
    b2b = quote([Item(weight_kg=4, length_cm=40, width_cm=30, height_cm=20)], "Z1", audience="b2b", apply_minimum=False)
    assert b2b["subtotal_cents"] == 1620


def test_f4_includes_two_person_and_extra_furniture_half_price():
    q = quote([Item(kind="furniture", furniture_class="F4", weight_kg=90), Item(kind="furniture", furniture_class="F1", weight_kg=10)], "Z1", add_ons={"dolly": 1})
    assert [line["cents"] for line in q["lines"]] == [22900, 2450]


def test_limits_and_minimum():
    with pytest.raises(ManualQuoteRequired):
        band_for(Item(weight_kg=500, length_cm=300, width_cm=200, height_cm=200), L)
    with pytest.raises(ManualQuoteRequired):
        quote([Item(weight_kg=1, length_cm=10, width_cm=10, height_cm=1)], "Z9")
    q = quote([Item(weight_kg=1, length_cm=30, width_cm=20, height_cm=2)], "Z1", audience="b2b")
    assert q["subtotal_cents"] == 6000 and q["lines"][-1]["key"] == "route_minimum"
    assert margin_colour(10000, 4000) == "green" and margin_colour(10000, 6000) == "yellow" and margin_colour(10000, 8000) == "red"


def test_custom_presets_and_guardrails():
    rows = sample_basket_preview(L, OrgPricing(mode="custom", preset_pct=-10))
    s = next(r for r in rows if r["sample"] == "S")
    assert s["custom_cents"] == round(s["standard_cents"] * 0.9)
    with pytest.raises(ValueError):
        sample_basket_preview(L, OrgPricing(mode="custom", band_overrides={"S:Z1": 100}))


def _client(db, role):
    ctx = AdminContext(user=AdminUser(auth_subject=f"pc-{role}", email=f"{role}@porterchain.com", role=role), role=parse_admin_role(role))
    app.dependency_overrides[get_admin_context] = lambda: ctx
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_admin_api_flow(db):
    try:
        c = _client(db, "super_admin")
        r = c.get("/v1/pricing/rate-cards/standard")
        assert r.status_code == 200 and r.json()["published"]["version"] == 1
        lines = r.json()["published"]["lines"]
        lines["bands"]["S"]["z1_cents"] = 1900
        r = c.post("/v1/pricing/rate-cards/standard/draft", json={"lines": lines, "notes": "S up"})
        assert r.status_code == 200 and r.json()["version"] == 2
        r = c.post("/v1/pricing/rate-cards/standard/preview", json={"lines": lines})
        assert "bands.S.z1_cents" in r.json()["diff"]
        assert c.post("/v1/pricing/rate-cards/standard/publish", json={"reason": "fuel"}).status_code == 200
        q = c.post("/v1/pricing/standard/quote", json={"items": [{"weight_kg": 4, "length_cm": 40, "width_cm": 30, "height_cm": 20}]})
        assert q.json()["subtotal_cents"] == 1900
        assert c.post("/v1/pricing/rate-cards/standard/rollback", json={"version": 1, "reason": "undo"}).json()["version"] == 3
        r = c.put("/v1/pricing/orgs/org-1", json={"mode": "custom", "preset_pct": -10})
        assert r.status_code == 200 and r.json()["mode"] == "custom"
        assert c.put("/v1/pricing/orgs/org-1", json={"mode": "custom", "band_overrides": {"S:Z1": 1500}}).json()["detail"] == "contract_required_for_overrides"
        assert c.post("/v1/pricing/orgs/org-1/preview", json={"mode": "custom", "preset_pct": 49}).status_code == 200
        actions = [a["action"] for a in c.get("/v1/pricing/audit").json()["items"]]
        assert {"draft_saved", "published", "rollback", "updated"} <= set(actions)

        a = _client(db, "admin")
        assert a.post("/v1/pricing/rate-cards/standard/publish", json={"reason": "nope"}).status_code == 403
        assert a.get("/v1/pricing/orgs/org-1").json()["mode"] == "custom"
        assert _client(db, "dispatcher").get("/v1/pricing/audit").status_code == 403
    finally:
        app.dependency_overrides.clear()
