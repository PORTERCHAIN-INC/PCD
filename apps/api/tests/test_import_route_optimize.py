"""Drop-order optimization for route import."""

from porterchain_api.merchant_engine.import_route_optimize import optimize_drop_order


def test_optimize_keeps_pickup_first_and_shortens_path():
    # Pickup at origin; drops in bad file order (far then near then mid)
    stops = [
        {"sequence": 1, "stop_type": "pickup", "lat": 43.65, "lng": -79.38, "address": "P"},
        {"sequence": 2, "stop_type": "drop", "lat": 43.75, "lng": -79.50, "address": "Far"},
        {"sequence": 3, "stop_type": "drop", "lat": 43.651, "lng": -79.381, "address": "Near"},
        {"sequence": 4, "stop_type": "drop", "lat": 43.70, "lng": -79.42, "address": "Mid"},
    ]
    out = optimize_drop_order(stops)
    assert out[0]["stop_type"] == "pickup"
    assert out[0]["sequence"] == 1
    # Nearest drop should come before farthest
    assert out[1]["address"] == "Near"
    assert [s["sequence"] for s in out] == [1, 2, 3, 4]
