"""Driver live-GPS switch (global + per driver) and self-hosted map extras."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from porterchain_api.platform import gps_policy
from porterchain_api.platform.last_known import read_last_known


class FakeRedis:
    def __init__(self):
        self.h = {
            "porterchain:gps:last:d1": {
                "lat": "43.5",
                "lng": "-79.8",
                "recorded_at": "2026-10-10T12:00:00+00:00",
            }
        }

    def hgetall(self, k):
        return self.h.get(k, {})

    def delete(self, k):
        return 1 if self.h.pop(k, None) is not None else 0

    def scan_iter(self, pattern):
        return list(self.h)


@pytest.fixture(autouse=True)
def _reset():
    yield
    gps_policy.set_policy_cache(None)


def test_normalize_and_defaults():
    assert gps_policy.normalize_driver_gps(None)["require_consent"] is True
    with pytest.raises(ValueError):
        gps_policy.normalize_driver_gps({"disabled_driver_ids": "x"})


def test_read_paths_hide_positions_when_off():
    r = FakeRedis()
    gps_policy.set_policy_cache({"enabled": True})
    assert read_last_known("d1", client=r) is not None
    gps_policy.set_policy_cache({"enabled": True, "disabled_driver_ids": ["d1"]})
    assert read_last_known("d1", client=r) is None
    gps_policy.set_policy_cache({"enabled": False})
    assert read_last_known("d1", client=r) is None


def test_ping_refused_and_driver_told(db):
    from porterchain_api.routers.driver.jobs import location_ping

    gps_policy.set_policy_cache({"enabled": False})
    ctx = SimpleNamespace(
        driver=SimpleNamespace(
            id="d1",
            status=__import__(
                "porterchain_api.domain.admin_states", fromlist=["DriverStatus"]
            ).DriverStatus.APPROVED.value,
        )
    )
    body = SimpleNamespace(
        lat=43.5,
        lng=-79.8,
        accuracy_m=5,
        heading=None,
        speed_mps=None,
        recorded_at=None,
    )
    out = location_ping(body, ctx, db, SimpleNamespace(gps_write_ping_table=True))
    assert (
        out["accepted"] is False
        and out["gps_enabled"] is False
        and "turned off" in out["message"]
    )
    assert gps_policy.driver_gps_status("d1")["enabled"] is False


def test_saving_off_forgets_pins(monkeypatch):
    from porterchain_api.admin_engine.settings_extra import EXTRA_NORMALIZERS

    r = FakeRedis()
    monkeypatch.setattr("porterchain_api.platform.last_known._client", lambda: r)
    EXTRA_NORMALIZERS["driver_gps"]({"enabled": False})
    assert r.h == {}
    assert gps_policy.gps_enabled_for("d1") is False


def test_track_is_empty_when_off_and_matched_when_on(db):
    from porterchain_api.platform.maps_extras import driver_track

    gps_policy.set_policy_cache({"enabled": False})
    assert driver_track(db, "d1")["path"] == []
    gps_policy.set_policy_cache({"enabled": True})

    class Maps:
        def map_match(self, pts):
            return {"path": [[1, 2], [3, 4]], "distance_m": 10, "source": "valhalla"}

    out = driver_track(db, "nobody", maps=Maps())
    assert (
        out["gps_enabled"] is True and out["source"] == "raw"
    )  # no pings → nothing to match


def test_service_area_parses_isochrone():
    from porterchain_api.platform import maps_extras

    maps_extras._AREA_CACHE.clear()

    class Maps:
        def isochrone(self, origin, **kw):
            ring = [[-79.9, 43.5], [-79.8, 43.6], [-79.7, 43.5], [-79.9, 43.5]]
            return {
                "features": [
                    {
                        "properties": {"contour": 30},
                        "geometry": {"type": "Polygon", "coordinates": [ring]},
                    }
                ]
            }

    out = maps_extras.service_area([30], maps=Maps())
    assert out["source"] == "valhalla" and out["areas"][0]["minutes"] == 30
    assert out["areas"][0]["path"][0] == [43.5, -79.9]


def test_snap_uses_locate_and_rejects_far_jumps(monkeypatch):
    from porterchain_services.maps.service import MapsService

    class R:
        status_code = 200

        def __init__(self, lat, lon):
            self._j = [{"edges": [{"correlated_lat": lat, "correlated_lon": lon}]}]

        def json(self):
            return self._j

    m = MapsService()
    monkeypatch.setattr(m, "_osrm_base", lambda: None)
    monkeypatch.setattr(m.settings, "valhalla_url", "http://v")
    target = {"r": R(43.5186, -79.8772)}

    class C:
        def post(self, url, json):
            return target["r"]

    monkeypatch.setattr(m, "_client", lambda: C())
    assert m.snap((43.5185, -79.8770)) == (43.5186, -79.8772)
    target["r"] = R(43.60, -79.80)  # ~10 km away: keep the original point
    assert m.snap((43.5185, -79.8770)) == (43.5185, -79.8770)


def test_consent_record_withdraw_and_require(db):
    from porterchain_api.platform.gps_policy import driver_gps_status, record_consent

    d = SimpleNamespace(id="d9", documents={})
    gps_policy.set_policy_cache({"enabled": True})
    assert driver_gps_status("d9", driver=d)["consent_required"] is True  # required by default
    gps_policy.set_policy_cache({"enabled": True, "require_consent": False})
    assert driver_gps_status("d9", driver=d)["enabled"] is True
    gps_policy.set_policy_cache({"enabled": True, "require_consent": True})
    s = driver_gps_status("d9", driver=d)
    assert s["enabled"] is False and s["consent_required"] is True and "on shift" in s["consent_text"]
    record_consent(d, accepted=True)
    assert driver_gps_status("d9", driver=d)["enabled"] is True and d.documents["gps_consent"]["at"]
    gps_policy.set_policy_cache({"enabled": True, "require_consent": False})
    record_consent(d, accepted=False)  # withdrawal stops collection even when not required
    assert driver_gps_status("d9", driver=d)["enabled"] is False
    assert len(d.documents["gps_consent_history"]) == 2
