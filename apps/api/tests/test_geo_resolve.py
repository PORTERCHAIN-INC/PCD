"""Shared address resolver (geo_resolve): ambiguity, typo, out-of-area, import wiring."""

from __future__ import annotations

from dataclasses import replace

import pytest
from porterchain_api import geo_resolve as gr
from porterchain_api.geo_resolve import Candidate
from porterchain_api.merchant_engine import import_geocode as ig

# Main St in two different York Region towns (~14 km apart).
MAIN_RH = Candidate(
    "10 Main Street, Richmond Hill, ON L4C 4X1",
    43.876,
    -79.437,
    "Richmond Hill",
    "L4C 4X1",
    score=0.65,
)
MAIN_MK = Candidate(
    "10 Main Street, Markham, ON L3P 1X7",
    43.882,
    -79.262,
    "Markham",
    "L3P 1X7",
    score=0.64,
)
OTTAWA = Candidate(
    "10 Main Street, Ottawa, ON K1S 1B9", 45.41, -75.69, "Ottawa", "K1S 1B9", score=0.9
)
BAY = Candidate(
    "200 Bay Street, Toronto, ON M5J 2J2",
    43.646,
    -79.380,
    "Toronto",
    "M5J 2J2",
    score=0.92,
)


def _fresh(*cs: Candidate) -> list[Candidate]:
    return [replace(c) for c in cs]


@pytest.fixture
def providers(monkeypatch):
    state: dict = {"photon": ([], False), "nominatim": [], "google": [], "calls": []}

    def photon(q):
        state["calls"].append(("photon", q))
        cands, conf = state["photon"]
        return _fresh(*cands), conf

    def nominatim(q):
        state["calls"].append(("nominatim", q))
        return _fresh(*state["nominatim"])

    def google(q):
        state["calls"].append(("google", q))
        return _fresh(*state["google"])

    monkeypatch.setattr(gr, "_photon", photon)
    monkeypatch.setattr(gr, "_nominatim", nominatim)
    monkeypatch.setattr(gr, "_google", google)
    return state


def test_two_areas_main_street_is_ambiguous(providers):
    providers["photon"] = ([MAIN_RH, MAIN_MK], False)
    res = gr.resolve_address("10 Main St")
    assert res.status == gr.STATUS_AMBIGUOUS
    assert "multiple_areas" in res.reasons
    assert {c.city for c in res.candidates} == {"Richmond Hill", "Markham"}
    assert len(res.candidates) <= gr.MAX_CANDIDATES
    assert res.to_dict()["candidates"][0]["fsa"] in {"L4C", "L3P"}


def test_typed_city_breaks_the_tie(providers):
    providers["photon"] = ([MAIN_RH, MAIN_MK], False)
    res = gr.resolve_address("10 Main St, Markham")
    assert res.status != gr.STATUS_AMBIGUOUS
    assert res.best.city == "Markham"


def test_city_typo_is_repaired_before_search(providers):
    providers["photon"] = ([MAIN_RH, MAIN_MK], False)
    res = gr.resolve_address("10 Main St, Richmnd Hil")
    assert res.normalized["city"] == "Richmond Hill"
    assert res.best.city == "Richmond Hill"
    assert res.status != gr.STATUS_AMBIGUOUS


def test_out_of_service_area_dropped_before_ranking(providers):
    providers["photon"] = ([OTTAWA], True)
    res = gr.resolve_address("10 Main St, Ottawa")
    assert res.status == gr.STATUS_FAILED
    assert "dropped_out_of_service_area" in res.reasons


def test_out_of_area_rival_does_not_make_ambiguous(providers):
    providers["photon"] = ([BAY, OTTAWA], True)
    res = gr.resolve_address("200 Bay St")
    assert res.status == gr.STATUS_CONFIDENT
    assert [c.city for c in res.candidates] == ["Toronto"]


def test_confident_photon_skips_nominatim_and_google(providers):
    providers["photon"] = ([BAY], True)
    res = gr.resolve_address("200 Bay St, Toronto")
    assert res.status == gr.STATUS_CONFIDENT and res.source == "photon"
    assert [c[0] for c in providers["calls"]] == ["photon"]


def test_same_spot_from_two_providers_is_not_ambiguous(providers):
    providers["photon"] = ([replace(BAY, score=0.7)], False)
    providers["nominatim"] = [replace(BAY, lat=43.6462, source="nominatim", score=0.7)]
    res = gr.resolve_address("200 Bay St, Toronto")
    assert res.status != gr.STATUS_AMBIGUOUS
    assert len(res.candidates) == 1


def test_postal_disagrees_with_street_is_ambiguous(providers):
    providers["photon"] = ([BAY], True)
    res = gr.resolve_address("200 Bay St, Toronto, L4C 1A1")
    assert res.status == gr.STATUS_AMBIGUOUS
    assert "postal_disagrees" in res.reasons


def test_google_only_when_still_weak(providers):
    providers["google"] = [replace(BAY, source="google")]
    res = gr.resolve_address("200 Bay Stret Toronto")
    assert [c[0] for c in providers["calls"]] == ["photon", "nominatim", "google"]
    assert res.source == "google"


def test_google_stub_is_dark_without_182(monkeypatch):
    monkeypatch.setattr(gr, "_google_module", lambda: None)
    assert gr.google_available() is False
    assert gr._google("anything") == []


def test_google_respects_flag(monkeypatch):
    class Fake:
        @staticmethod
        def enabled():
            return False

    monkeypatch.setattr(gr, "_google_module", lambda: Fake)
    assert gr.google_available() is False


def test_cleaning_helpers():
    assert gr.repair_postal("L4C OA1") == "L4C 0A1"
    assert gr.repair_postal("m5j2j2") == "M5J 2J2"
    assert gr.expand_abbrev("12 Maple Cres") == "12 Maple Crescent"
    assert gr.fuzzy_city("Missisauga") == "Mississauga"
    assert gr.fuzzy_city("Springfield") == "Springfield"


def test_import_geocode_maps_ambiguous_to_needs_review(providers, monkeypatch):
    monkeypatch.setenv("GEO_RESOLVE_IMPORT", "1")
    providers["photon"] = ([MAIN_RH, MAIN_MK], False)
    geo = ig.geocode_stop(address="10 Main St", smart=True)
    assert geo.status == "needs_review"
    assert "address.ambiguous" in geo.issues
    assert len(geo.candidates) == 2


def test_resolve_stops_flags_row_and_blocks_quote(providers, monkeypatch):
    from porterchain_api.merchant_engine import import_quote

    monkeypatch.setenv("GEO_RESOLVE_IMPORT", "1")

    def photon(q):
        if "Main" in q:
            return _fresh(MAIN_RH, MAIN_MK), False
        return _fresh(BAY), True

    monkeypatch.setattr(gr, "_photon", photon)
    stops, errors = import_quote.resolve_stops(
        [
            {"address": "200 Bay St, Toronto", "stop_type": "pickup"},
            {"address": "10 Main St", "stop_type": "drop"},
        ],
        geocode_now=True,
    )
    assert stops[0]["geocode_status"] == "ok"
    assert stops[1]["geocode_status"] == "needs_review"
    assert len(stops[1]["candidates"]) == 2
    assert any(e["error"] == "address.ambiguous" for e in errors)
    assert import_quote.quote_if_ready(None, None, "van", None, stops) is None


def test_kill_switch_keeps_legacy_path(monkeypatch):
    monkeypatch.setenv("GEO_RESOLVE_IMPORT", "0")
    monkeypatch.setattr(
        ig,
        "_nominatim_search",
        lambda q: {"lat": "43.65", "lon": "-79.38", "display_name": q},
    )
    geo = ig.geocode_stop(address="200 Bay St, Toronto", smart=True)
    assert geo.source == "nominatim" and geo.candidates is None


def test_csv_semicolon_and_cp1252_sniffed():
    from porterchain_api.merchant_engine.import_ingest import parse_csv_bytes

    sheet = parse_csv_bytes(
        "address;stop_type\n12 Rue Café, Toronto;pickup\n".encode("cp1252")
    )
    assert sheet.headers == ["address", "stop_type"]
    assert sheet.rows[0]["address"] == "12 Rue Café, Toronto"
