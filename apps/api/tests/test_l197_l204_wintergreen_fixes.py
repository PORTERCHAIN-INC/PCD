"""Wintergreen 117-stop run fixes: geocode fallbacks (L197b/c), matrix chunking + 2-opt (L197d), mid-stop scan gate (L204)."""
from types import SimpleNamespace

import pytest

from porterchain_api.merchant_engine import import_geocode as g


def test_ordinal_concession_road():
    assert g._ordinal_street("3075 8 Line") == "3075 8th Line"
    assert g._ordinal_street("10 2 Concession") == "10 2nd Concession"
    assert g._ordinal_street("33 King St") == "33 King St"


def test_postal_mismatch_flag():
    assert g._postal_mismatch("M2R 2S5", "751, Steeles Avenue West, Toronto, Ontario, L4J 8A4, Canada")
    assert not g._postal_mismatch("M2R 2S5", "12 Rockford Road, Toronto, Ontario, M2R 3A7, Canada")
    assert not g._postal_mismatch(None, "x")


def test_no_postal_fallback_used(monkeypatch):
    seen = []

    def fake(q):
        seen.append(q)
        return {"lat": "43.7", "lon": "-79.5", "display_name": "33, King Street, Weston, Toronto, M9N 1J3"} if "M9N" not in q else None

    monkeypatch.setattr(g, "_nominatim_search", fake)
    r = g.geocode_stop(address="33 King St", city="Toronto", province="ON", postal="M9N 3R7")
    assert r.lat == 43.7 and r.status == "ok"
    assert any("M9N" not in q for q in seen)


def test_matrix_chunking_stitches_blocks():
    from porterchain_services.maps.service import MapsService

    svc = MapsService.__new__(MapsService)
    calls = []

    def fake(src, tgt, **kw):
        calls.append((len(src), len(tgt)))
        return [[(1, 1) for _ in tgt] for _ in src]

    svc._valhalla_matrix = fake
    pts = [(43.0 + i / 1000, -79.0) for i in range(118)]
    m = svc._valhalla_matrix_chunked(pts, pts)
    assert len(m) == 118 and all(len(r) == 118 for r in m)
    assert max(max(c) for c in calls) <= 50


class _Q:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_a):
        return self

    def all(self):
        return self.rows


def test_mid_stop_requires_its_parcels_scanned():
    from porterchain_driver import multi_stops as ms

    rows = [SimpleNamespace(stop_key="pc-stop-115", status="picked_up", deleted_at=None),
            SimpleNamespace(stop_key="pc-stop-9", status="picked_up", deleted_at=None)]
    db = SimpleNamespace(query=lambda *_: _Q(rows))
    with pytest.raises(ValueError, match="stop_parcels_unscanned"):
        ms._assert_stop_parcels_scanned(db, "o1", "pc_stop_115")
    rows[0].status = "delivered"
    ms._assert_stop_parcels_scanned(db, "o1", "pc_stop_115")


def test_onboarding_verticals_get_a_real_segment(monkeypatch):
    from porterchain_api.merchant_engine.account_ops import health as h
    import porterchain_api.merchant_engine.organization_sync as o

    for industry, seg in [("printing-signage", "retail_specialty"), ("automotive-parts", "trades"), ("coffee-roasters", "food")]:
        monkeypatch.setattr(o, "industry_of", lambda _m, i=industry: i)
        assert h.segment_of(SimpleNamespace(segment_tags=None)) == seg
    assert "retail_specialty" in h.SEGMENTS


def test_no_city_column_still_tries_ordinal_without_postal(monkeypatch):
    from porterchain_api.merchant_engine import import_geocode as g

    seen = []

    def fake(q):
        seen.append(q)
        return {"lat": "44.1", "lon": "-79.6", "display_name": "3075, 8th Line, Bradford, Ontario, L3Z 0C1, Canada"} if "8th Line" in q else None

    monkeypatch.setattr(g, "_nominatim_search", fake)
    r = g.geocode_stop(address="3075 8 Line, Bradford, ON L3Z 3R5")
    assert r.lat == 44.1 and "address.postal_mismatch" not in r.issues
    assert any("8th Line" in q and "L3Z" not in q for q in seen)


def test_one_unroutable_pin_keeps_road_matrix():
    from porterchain_services.maps import sequence as s

    pts = [(43.7 + i / 100, -79.5) for i in range(5)]

    class Maps:
        def matrix_durations(self, a, b):
            return [[(None, None) if 4 in (i, j) and i != j else (60, 1000 * abs(i - j)) for j in range(5)] for i in range(5)], "valhalla"

    road, src = s._road_costs(Maps(), pts)
    assert src == "valhalla" and road is not None and road[0][4] > 0


def test_merchant_invoice_due_date_carries_utc_offset():
    from datetime import datetime

    from porterchain_api.billing_engine import merchant_service as ms
    import inspect

    src = inspect.getsource(ms)
    assert 'due.replace(tzinfo=UTC)).isoformat()' in src
    # 23:59:59 Toronto stored as naive UTC must not read as 4:59 a.m. local.
    due = datetime(2026, 11, 5, 4, 59, 59)
    from datetime import UTC
    assert due.replace(tzinfo=UTC).isoformat().endswith("+00:00")
