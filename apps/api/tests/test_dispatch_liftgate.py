"""Liftgate is a hard constraint: only liftgate vehicles take liftgate orders."""

from types import SimpleNamespace as NS

from porterchain_api.admin_engine.fleet_plan_service import FleetPlanService
from porterchain_api.dispatch_engine import capabilities, exception_fixes, vrp
from porterchain_api.dispatch_engine.stop_shapes import StopSpec


def _problem(lift_vehicle: bool):
    stops = [StopSpec("o1:p0", "o1", "pickup", 43.65, -79.38, kg=50, boxes=1, liftgate=True),
             StopSpec("o1:d0", "o1", "drop", 43.70, -79.40, kg=50, boxes=1, liftgate=True)]
    vs = [vrp.Vehicle(id="near", driver_id=None, vehicle_class="van", cap_kg=900, cap_boxes=40, start=(43.65, -79.38)),
          vrp.Vehicle(id="far", driver_id=None, vehicle_class="box_truck", cap_kg=2500, cap_boxes=140,
                      start=(43.80, -79.60), liftgate=lift_vehicle)]
    m = [[0 if i == j else (900 if 1 in (i, j) else 300) for j in range(4)] for i in range(4)]
    return vrp.Problem(stops=stops, pairs=[("o1:p0", "o1:d0")], vehicles=vs, matrix=m, time_limit_s=1)


def test_liftgate_order_goes_to_the_liftgate_truck_even_when_farther():
    prob = _problem(True)
    ev = vrp.evaluate(prob, vrp.solve_ortools(prob))
    assert [r["vehicle_id"] for r in ev["routes"]] == ["far"] and ev["feasible"]


def test_no_liftgate_vehicle_drops_the_order_and_evaluate_flags_misuse():
    prob = _problem(False)
    assert vrp.evaluate(prob, vrp.solve_ortools(prob))["dropped"] == ["o1:p0"]
    assert not vrp.evaluate(prob, {"near": ["o1:p0", "o1:d0"]})["feasible"]


def test_gap_moves_orders_to_skipped_with_reason():
    prob, skipped = _problem(False), []
    stops, pairs = FleetPlanService._liftgate_gap(prob.stops, prob.pairs, prob.vehicles, skipped)
    assert stops == [] and pairs == [] and skipped[0]["reason"] == "no_liftgate_vehicle"


def test_flags_and_fix():
    assert capabilities.order_needs_liftgate(NS(compliance_metadata={"requires_liftgate": True}))
    assert not capabilities.order_needs_liftgate(NS(compliance_metadata=None))
    assert capabilities.has_liftgate(["liftgate"]) and not capabilities.has_liftgate(None)
    fixes = exception_fixes.suggest({"kind": "liftgate", "type": "NO_LIFTGATE_VEHICLE", "state": "DISPATCH_READY"},
                                    plan_id=None, best_driver=None, next_slot=None)
    assert fixes[-1]["action"] == "contact"
