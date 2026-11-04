"""Billing consumes doc 72 §9.4 per-order adjustments; pricing_quote_sent template is registered."""
from __future__ import annotations

import uuid

from porterchain_api.billing_engine import accessorials as acc
from porterchain_api.notification_engine.templates import TEMPLATE_META, TEMPLATES, render_template
from porterchain_api.pricing_engine.models import PricingOrderAdjustment
from tests.fk_parents import make_order


def test_adjustments_become_signed_invoice_lines(db):
    order = make_order(db)
    db.add_all([PricingOrderAdjustment(id=str(uuid.uuid4()), order_id=order.id, cents=750, category="waiting",
                                       reason="30 min at dock", actor_role="admin"),
                PricingOrderAdjustment(id=str(uuid.uuid4()), order_id=order.id, cents=-500, category="goodwill",
                                       reason="late", actor_role="super_admin")])
    db.flush()
    lines = acc.adjustment_lines(db, [order])
    assert sorted(x.amount_cents for x in lines) == [-500, 750]
    assert all(x.code.startswith("adjustment:") and x.evidence["source"] == "pricing_order_adjustments" for x in lines)
    assert any("waiting: 30 min at dock" in x.description for x in lines)
    splits = {x.amount_cents: acc._signed_split(db, x.order, x.amount_cents) for x in lines}
    assert splits[750].pretax_cents == 750 and splits[-500].pretax_cents == -500
    assert splits[-500].tax_cents == -round(splits[750].tax_cents * 500 / 750) or splits[-500].tax_cents <= 0
    assert acc.adjustment_lines(db, []) == []


def test_fee_specs_include_adjustments(db, monkeypatch):
    order = make_order(db)
    db.add(PricingOrderAdjustment(id=str(uuid.uuid4()), order_id=order.id, cents=300, category="extra_stop",
                                  reason="second dock"))
    db.flush()
    monkeypatch.setattr(acc, "accessorial_lines", lambda *_a, **_k: [])
    specs = acc.fee_specs(db, object(), [order])
    assert [(x.code.split(":")[0], s.pretax_cents) for x, s in specs] == [("adjustment", 300)]


def test_pricing_quote_sent_template_registered():
    assert TEMPLATE_META["pricing_quote_sent"]["category"] == "crm"
    assert "pricing_quote_sent" in TEMPLATES
    subject, body = render_template("pricing_quote_sent", {"total": "$20.34", "quote_link": "https://x.test/q/abc",
                                                           "valid_hours": 72, "expires_at": "2026-11-01T18:00:00-04:00"})
    assert "$20.34" in subject and "https://x.test/q/abc" in body and "72 hours" in body
