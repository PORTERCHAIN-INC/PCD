"""Assignment scoring filters + Valhalla matrix parsing (P1-2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from porterchain_api.admin_engine.control_tower.scoring import (
    WINDOW_MISS_PENALTY,
    hard_filter_driver,
    required_skills,
    window_penalty,
)
from porterchain_services.maps.service import MapsService


def _verified(**kwargs):
    base = dict(
        license_verified=True,
        insurance_verified=True,
        background_check_status="passed",
        medical_transport_certified=False,
        documents={},
        full_name="A",
        id="1",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


class TestHardFilters:
    def test_unverified_license_excluded(self):
        d = _verified(license_verified=False)
        reason = hard_filter_driver(
            d, medical_required=False, required_class=None, classes=set(), skills_needed=[]
        )
        assert reason and "License" in reason

    def test_medical_required_excludes_uncertified(self):
        d = _verified(medical_transport_certified=False)
        assert hard_filter_driver(
            d, medical_required=True, required_class=None, classes=set(), skills_needed=[]
        )

    def test_vehicle_class_mismatch_excluded(self):
        d = _verified()
        reason = hard_filter_driver(
            d,
            medical_required=False,
            required_class="cargoVan",
            classes={"sedan"},
            skills_needed=[],
        )
        assert reason and "cargoVan" in reason

    def test_skills_missing_excluded(self):
        d = _verified(documents={"skills": ["hazmat"]})
        reason = hard_filter_driver(
            d,
            medical_required=False,
            required_class=None,
            classes=set(),
            skills_needed=["cold_chain"],
        )
        assert reason and "cold_chain" in reason

    def test_eligible_when_class_and_medical_ok(self):
        d = _verified(
            medical_transport_certified=True,
            documents={"skills": ["medical"]},
        )
        assert (
            hard_filter_driver(
                d,
                medical_required=True,
                required_class="cargoVan",
                classes={"cargoVan"},
                skills_needed=[],
            )
            is None
        )


class TestWindowPenalty:
    def test_miss_applies_penalty(self):
        now = datetime(2026, 8, 7, 12, 0, 0)
        end = now + timedelta(minutes=10)
        pen, reason = window_penalty(eta_minutes=30, window_end=end, now=now)
        assert pen == WINDOW_MISS_PENALTY
        assert reason

    def test_on_time_no_penalty(self):
        now = datetime(2026, 8, 7, 12, 0, 0)
        end = now + timedelta(minutes=60)
        pen, reason = window_penalty(eta_minutes=15, window_end=end, now=now)
        assert pen == 0.0
        assert reason is None


class TestRequiredSkills:
    def test_cold_chain_flag(self):
        assert required_skills({"cold_chain": {"required": True}}) == ["cold_chain"]

    def test_explicit_list(self):
        assert required_skills({"required_skills": ["Hazmat", "liftgate"]}) == [
            "hazmat",
            "liftgate",
        ]


class TestValhallaMatrixParse:
    def test_parse_sources_to_targets_shape(self, monkeypatch):
        svc = MapsService()
        monkeypatch.setattr(svc.settings, "valhalla_url", "http://valhalla.test", raising=False)
        monkeypatch.setattr(svc.settings, "osrm_url", None, raising=False)
        monkeypatch.setattr(svc.settings, "routing_engine", "valhalla", raising=False)

        class Resp:
            status_code = 200

            def json(self):
                return {
                    "sources_to_targets": [
                        [{"time": 600, "distance": 4.2}],
                        [{"time": 900, "distance": 7.1}],
                    ]
                }

        class Client:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, *a, **k):
                return Resp()

        import porterchain_services.maps.service as maps_mod

        monkeypatch.setattr(maps_mod.httpx, "Client", Client)
        matrix, source = svc.matrix_durations(
            [(43.65, -79.38), (43.66, -79.39)],
            [(43.64, -79.37)],
        )
        assert source == "valhalla"
        assert matrix[0][0] == (600, 4200)
        assert matrix[1][0] == (900, 7100)
