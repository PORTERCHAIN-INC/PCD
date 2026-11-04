"""Doc 79 §8 A-FIN acceptance checks on the formulas."""
from __future__ import annotations

import pytest

from porterchain_api.metrics_engine import formulas as f
from porterchain_api.metrics_engine.baseline import baseline

approx = pytest.approx


def test_a_fin_01_03_ebitda_top_down_equals_bottom_up_3pl():
    lines = [("4100", 10_000_000_00), ("5100", 7_500_000_00), ("6500", 1_000_000_00), ("7100", 400_000_00),
             ("8200", 250_000_00)]
    p = f.pnl(lines)
    assert p.gross_profit == 2_500_000_00 and p.ebit == 1_100_000_00 and p.net_income == 850_000_00
    assert p.ebitda_top_down == p.ebitda_bottom_up == 1_500_000_00
    assert p.ebitda_margin == approx(0.15)


def test_a_fin_02_hst_never_revenue_or_cost():
    p = f.pnl([("4100", 100_00), ("2200", 13_00), ("5200", 20_00)])
    assert p.revenue == 100_00 and p.direct == 20_00
    with pytest.raises(ValueError, match="unknown_account"):
        f.pnl([("9999", 1)])


def test_a_fin_04_asrs_returns():
    assert f.roi(150_000, 500_000) == approx(-0.70)
    assert f.simple_annual_return(150_000, 500_000) == approx(0.30)
    assert f.payback_years(500_000, 150_000) == approx(3.333, abs=1e-3)
    assert f.roi(750_000, 500_000) == approx(0.50)


def test_a_fin_05_capital_project():
    n = f.nopat(400_000, 0.30)
    assert n == approx(280_000)
    assert f.roic(n, 2_000_000) == approx(0.14)
    assert f.eva(n, 2_000_000, 0.10) == approx(80_000)
    assert f.capm(0.032, 1.5, 0.087) == approx(0.1145)
    assert f.wacc(1, 0, 0.18, 0.08, 0.122) == approx(0.18)


def test_a_fin_06_07_baseline_and_gta_route():
    b = baseline()
    assert b["annual_da"] == approx(19_666.67, abs=0.01)
    r = b["route"]
    assert r["revenue"] == approx(194.40) and r["direct_cost"] == approx(97.65)
    assert r["contribution"] == approx(96.75) and r["margin"] == approx(0.498, abs=1e-3) and r["colour"] == "yellow"
    assert r["contribution_per_stop"] == approx(8.06)
    be = b["break_even_stops_per_day"]
    assert be["cash"] == approx(2.4) and be["accounting"] == approx(11.7) and be["eva"] == approx(19.1)
    assert b["payback_months"] == {"12": 45.3, "20": 24.7, "40": 11.6}
    y = b["year"]
    assert y["revenue"] == approx(85_536) and y["ebitda"] == approx(37_410) and y["ebit"] == approx(17_743.33, abs=0.01)
    assert y["nopat"] == approx(15_578.65, abs=0.01) and y["eva"] == approx(1_718.65, abs=0.01)
    assert y["roic"] == approx(0.202, abs=1e-3)
    dense = f.route_economics(16.20 * 16, 3.5, 55, 16)
    assert dense["contribution"] == approx(144.85) and dense["colour"] == "green"


def test_a_fin_08_kingman_alert():
    assert f.kingman_wq(1, 0.5, 0.85, 10) == approx(42.5)
    assert f.kingman_wq(1, 0.5, 0.95, 10) == approx(142.5)
    assert f.utilisation_alert(0.85) == "ok" and f.utilisation_alert(0.86) == "yellow" and f.utilisation_alert(0.91) == "red"
    assert f.littles_law(40, 0.25) == approx(10)


def test_a_fin_09_safety_stock_and_eoq():
    assert f.safety_stock(1.65, 4, 20, 100, 1) == approx(177.7, abs=0.05)
    assert f.eoq_backorders(36_500, 50, 2, 8) == approx(1510.4, abs=0.1)


def test_a_fin_10_ccc():
    assert f.ccc(0, f.dso_days([30, 30]), 10) == approx(20)


def test_a_fin_11_margin_colours_match_doc72():
    assert f.margin_colour(0.50) == "green" and f.margin_colour(0.499) == "yellow"
    assert f.margin_colour(0.35) == "red" and f.margin_colour(0.351) == "yellow"


def test_a_fin_13_service_and_claims():
    o = f.otif(200, 191)
    assert o == approx(0.955) and f.otif_colour(o) == "yellow"
    over, cost = f.dwell_leakage(52)
    assert over == 22 and cost == approx(11.00)
    assert f.claim_payable(300, 12, None) == approx(52.92)
    assert f.claim_payable(300, 12, 1000) == approx(52.92)  # declared but no cover bought
    assert f.claim_payable(300, 12, 1000, covered=True) == approx(52.92)  # no proof of value
    assert f.claim_payable(300, 12, 1000, covered=True, proof_of_value=True) == 300
    assert f.claim_cap(12, 9000, covered=True, proof_of_value=True) == 2500
    lines = [("4100", 1000_00), ("5700", 52_92)]
    assert f.pnl(lines).gross_profit == 1000_00 - 52_92


def test_a_fin_14_compliance_money():
    assert round(f.compliance_gap_cost(0.02, 0.30, 310, 96.75), 2) == 2.44
    assert f.oos_margin_loss(12, 96.75 / 12) == approx(96.75)
    assert f.oos_margin_loss(12, 96.75 / 12, n_sub=12, cm_sub=3.0) == approx(60.75)


def test_metrics_route_requires_finance_role():
    from fastapi.testclient import TestClient

    from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.auth.admin import get_admin_context
    from porterchain_api.main import app

    try:
        for role, code in (("admin", 200), ("support", 403)):
            ctx = AdminContext(user=AdminUser(auth_subject=f"m-{role}", email=f"{role}@porterchain.com", role=role),
                               role=parse_admin_role(role))
            app.dependency_overrides[get_admin_context] = lambda ctx=ctx: ctx
            r = TestClient(app).get("/v1/admin/metrics/baseline?stops_per_day=20")
            assert r.status_code == code, (role, r.text)
            if code == 200:
                assert r.json()["route"]["colour"] == "yellow"
                assert r.json()["kingman"]["0.85"] == 42.5
    finally:
        app.dependency_overrides.clear()
