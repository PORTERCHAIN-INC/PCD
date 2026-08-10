"""Dispatch suggestions — pure scoring + Fleetbase payload parsing contracts."""

from porterchain_api.admin_engine.dispatch_suggestions_service import (
    CAPABILITY_PENALTY_MIN,
    NO_POSITION_ETA_MIN,
    OFFLINE_PENALTY_MIN,
    _coords,
    _driver_location,
    _driver_online,
    score_candidate,
)


class TestScoring:
    def test_closer_driver_scores_lower(self):
        near = score_candidate(
            eta_minutes=8, active_orders=0, rating=4.5, online=True, capability_match=None
        )
        far = score_candidate(
            eta_minutes=30, active_orders=0, rating=4.5, online=True, capability_match=None
        )
        assert near < far

    def test_missing_eta_uses_no_position_penalty(self):
        score = score_candidate(
            eta_minutes=None, active_orders=0, rating=None, online=True, capability_match=None
        )
        baseline = NO_POSITION_ETA_MIN - 1.5 * 3.0
        assert score == round(baseline, 1)

    def test_load_penalizes_busy_driver(self):
        free = score_candidate(
            eta_minutes=10, active_orders=0, rating=4.0, online=True, capability_match=None
        )
        busy = score_candidate(
            eta_minutes=10, active_orders=3, rating=4.0, online=True, capability_match=None
        )
        assert busy > free

    def test_offline_penalty_applied(self):
        online = score_candidate(
            eta_minutes=10, active_orders=0, rating=None, online=True, capability_match=None
        )
        offline = score_candidate(
            eta_minutes=10, active_orders=0, rating=None, online=False, capability_match=None
        )
        assert offline == round(online + OFFLINE_PENALTY_MIN, 1)

    def test_capability_mismatch_penalized_but_match_is_not(self):
        matched = score_candidate(
            eta_minutes=10, active_orders=0, rating=None, online=True, capability_match=True
        )
        mismatched = score_candidate(
            eta_minutes=10, active_orders=0, rating=None, online=True, capability_match=False
        )
        assert mismatched == round(matched + CAPABILITY_PENALTY_MIN, 1)

    def test_higher_rating_wins_tie(self):
        a = score_candidate(
            eta_minutes=10, active_orders=0, rating=5.0, online=True, capability_match=None
        )
        b = score_candidate(
            eta_minutes=10, active_orders=0, rating=3.0, online=True, capability_match=None
        )
        assert a < b


class TestCoordsParsing:
    def test_coords_from_lat_lng_variants(self):
        assert _coords({"lat": 43.65, "lng": -79.38}) == (43.65, -79.38)
        assert _coords({"latitude": "43.65", "longitude": "-79.38"}) == (43.65, -79.38)
        assert _coords({"lat": 43.65, "lon": -79.38}) == (43.65, -79.38)

    def test_coords_missing_or_invalid(self):
        assert _coords(None) is None
        assert _coords({}) is None
        assert _coords({"lat": "north", "lng": -79.38}) is None


class TestFleetbaseDriverPayloadParsing:
    def test_location_wrapped_resource(self):
        payload = {"driver": {"location": {"lat": 43.65, "lng": -79.38}, "online": True}}
        assert _driver_location(payload) == (43.65, -79.38)

    def test_location_geojson_coordinates(self):
        payload = {"driver": {"location": {"coordinates": [-79.38, 43.65]}}}
        assert _driver_location(payload) == (43.65, -79.38)

    def test_location_flat_lat_lng(self):
        payload = {"latitude": 43.65, "longitude": -79.38}
        assert _driver_location(payload) == (43.65, -79.38)

    def test_location_absent(self):
        assert _driver_location({"driver": {"name": "A"}}) is None
        assert _driver_location(None) is None

    def test_online_prefers_live_payload(self):
        class D:
            is_online = False
            availability = "offline"

        assert _driver_online({"driver": {"online": True}}, D()) is True
        assert _driver_online({"driver": {"status": "offline"}}, D()) is False

    def test_online_falls_back_to_mirror(self):
        class D:
            is_online = True
            availability = "offline"

        assert _driver_online(None, D()) is True
