"""Per-vehicle solver cost: per-km cost is honoured and the smaller vehicle wins a tie."""

from porterchain_api.dispatch_engine import vrp
from porterchain_api.dispatch_engine.stop_shapes import StopSpec


def _problem(vehicles: list[vrp.Vehicle]) -> vrp.Problem:
    stops = [StopSpec("o1:p0", "o1", "pickup", 43.65, -79.38, kg=5, boxes=1, m3=0.02),
             StopSpec("o1:d0", "o1", "drop", 43.70, -79.40, kg=5, boxes=1, m3=0.02)]
    n = len(vehicles) + 2
    secs = [[0 if i == j else 600 for j in range(n)] for i in range(n)]
    metres = [[0 if i == j else 8000 for j in range(n)] for i in range(n)]
    return vrp.Problem(stops=stops, pairs=[("o1:p0", "o1:d0")], vehicles=vehicles, matrix=secs, metres=metres,
                       time_limit_s=1)


def _veh(vid: str, cls: str, rank: int, km: int = 0) -> vrp.Vehicle:
    return vrp.Vehicle(id=vid, driver_id=None, vehicle_class=cls, cap_kg=900, cap_boxes=40, start=(43.65, -79.38),
                       rank=rank, km_cents=km)


def test_smaller_vehicle_wins_a_tie():
    prob = _problem([_veh("truck", "box_truck", 3), _veh("sedan", "sedan", 0)])
    assert list(vrp.solve_ortools(prob)) == ["sedan"]


def test_per_km_cost_picks_the_cheaper_vehicle_and_is_scored():
    prob = _problem([_veh("a", "van", 0, km=40), _veh("b", "van", 0, km=5)])
    ev = vrp.evaluate(prob, vrp.solve_ortools(prob))
    assert [r["vehicle_id"] for r in ev["routes"]] == ["b"]
    r = ev["routes"][0]
    assert r["metres"] == 16000
    assert r["cost_cents"] == round(r["seconds"] / 3600 * 2700 + 16 * 5)


def test_arc_cost_is_reference_seconds():
    v = _veh("x", "van", 0)
    assert vrp.arc_cost(600, 0, v) == 600
    assert vrp.arc_cost(0, 1000, vrp.Vehicle(**{**v.__dict__, "km_cents": 27})) == 36
    assert vrp.fixed_cost(_veh("t", "box_truck", 3)) == 1800 + 3 * vrp.RIGHT_SIZE_S


def test_vehicle_costs_from_shared_margin_estimates():
    from porterchain_api.dispatch_engine.vehicle_cost import vehicle_costs

    est = {"driver_hourly_cents": 2700, "vehicle_cents_per_km": 35, "working_days_per_month": 22,
           "working_hours_per_day": 10, "insurance_monthly_cents": {"cargo_van": 60000}}
    assert vehicle_costs(est, {"id": "van"}) == (2973, 35)  # $27 + $600/220 h ≈ $29.73/h
    assert vehicle_costs(est, {"id": "sedan"}) == (2700, 35)
    assert vehicle_costs(est, {"id": "sedan", "cost_per_km_cents": 20}) == (2700, 20)
