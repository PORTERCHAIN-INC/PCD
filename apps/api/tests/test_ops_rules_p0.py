"""Doc 84 §7 P0 gaps (open questions in §8 deliberately not decided)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from porterchain_api.batch_engine import service as B
from porterchain_api.batch_engine import vrp
from porterchain_api.ops_rules import codes, rules
from porterchain_api.ops_rules import service as OS
from porterchain_shared.events.catalog import DomainEventType


def test_single_exception_code_list():
    assert len({c.code for c in codes.CODES}) == len(codes.CODES)
    assert codes.canonical("short") == "count_short" and codes.canonical("PARCEL_DAMAGED") == "parcel_damaged"
    with pytest.raises(ValueError):
        codes.canonical("made_up")
    from porterchain_api.admin_engine.dispatch_board_service import EXCEPTION_SEVERITY
    assert EXCEPTION_SEVERITY["suspicious_parcel"] == "critical" and EXCEPTION_SEVERITY["DRIVER_TIMEOUT"] == "high"


def test_custody_event_types_in_catalog():
    for k in ("pickup", "handover_out", "handover_in", "depot_in", "sorted", "delivered", "return", "held"):
        assert OS.custody_event_type(k) in {e.value for e in DomainEventType}
    with pytest.raises(ValueError):
        OS.custody_event_type("teleported")


def test_rules_pure():
    assert rules.ui_locked(15) and not rules.ui_locked(8) and not rules.ui_locked(None)
    w = rules.duplicate_warnings([{"row_no": 1, "address": "1 King St", "reference": "#100"},
                                  {"row_no": 2, "address": "1 king st.", "reference": "#100"},
                                  {"row_no": 3, "address": "1 King St", "reference": ""}])
    assert w == [{"code": "duplicate_in_file", "row_no": 2, "same_as_row": 1}]
    assert rules.change_decision("OUT_FOR_DELIVERY", None, None)["allowed"] is False
    assert rules.change_decision("BOOKED", (43.65, -79.38), (43.66, -79.39))["action"] == "reroute_live"
    assert rules.change_decision("BOOKED", (43.65, -79.38), (43.25, -79.87))["action"] == "fee_or_next_day"
    assert rules.short_code().startswith("PC-") and len(rules.unlabelled_requirements()) == 3
    req = rules.required_equipment(["cold", "pharmacy"])
    assert req == ["insulated_bag", "lockbox"]
    assert rules.eligible_drivers(req, [{"id": "a", "equipment": ["lockbox"]},
                                        {"id": "b", "equipment": ["lockbox", "insulated_bag"]}]) == ["b"]
    assert rules.carry_check(40) == {"ok": True, "dolly": True, "equipment": ["dolly"]}
    assert rules.carry_check(20)["dolly"] is False and not rules.carry_check(90)["ok"]
    eos = rules.end_of_shift([{"barcode": "A", "handling": ["pharmacy"]}, {"barcode": "B", "handling": []}])
    assert not eos["can_end_shift"] and eos["must_return_to_pharmacy"] == ["A"]
    assert eos["must_return_to_sender_same_day"] == ["B"]  # no overnight for anyone
    assert not rules.end_of_shift([{"barcode": "B"}])["can_end_shift"] and rules.end_of_shift([])["can_end_shift"]
    now = datetime.now(UTC)
    assert rules.CLAIM_DEADLINES["concealed_damage_report_days"] == 5
    assert rules.concealed_damage_check(now - timedelta(days=4), now, ["p"])["late"] is False
    assert rules.concealed_damage_check(now - timedelta(days=9), now, ["p"])["late"] is True
    with pytest.raises(ValueError):
        rules.concealed_damage_check(now, now, [])


def test_locations_access_and_unsafe_flag(db):
    loc = OS.upsert_location(db, f"{uuid.uuid4().hex[:5]} Bay St, Toronto", access_notes="Buzz 1234")
    OS.set_unit_notes(db, loc.id, "1203", "Leave with concierge desk B")
    a = OS.access_for(db, loc.building_key, "1203")
    assert a["access_notes"] == "Buzz 1234" and a["unit_notes"].startswith("Leave") and not a["unsafe"]
    with pytest.raises(ValueError):
        OS.safety_stop(db, "suspicious_parcel", "d1")  # photo required
    r = OS.safety_stop(db, "unsafe_location", "d1", address=loc.address, note="loose dog")
    assert r["stop"] and r["location_flagged"] and OS.access_for(db, loc.building_key)["unsafe"]
    with pytest.raises(ValueError):
        OS.safety_stop(db, "theft_from_vehicle", "d1")  # parcels required


def test_equipment_store_and_check(db):
    did = str(uuid.uuid4())
    OS.set_equipment(db, did, ["lockbox", "dolly"])
    assert OS.equipment_check(db, did, ["lockbox", "insulated_bag"]) == {"ok": False, "missing": ["insulated_bag"],
                                                                       "code": "equipment_missing"}
    with pytest.raises(ValueError):
        OS.set_equipment(db, did, ["jetpack"])


def test_batch_duplicate_warning_requires_confirm(db):
    mid = str(uuid.uuid4())
    csv = "address,client_label\n10 King St W Toronto,#5001\n"
    B.create_batch(db, mid, csv)
    with pytest.raises(B.DuplicateRows) as e:
        B.create_batch(db, mid, csv)
    assert e.value.warnings[0]["code"] == "duplicate_of_existing"
    b = B.create_batch(db, mid, csv, confirm_duplicates=True)
    assert b.plan["warnings"]


def test_valhalla_matrix_used_when_reachable():
    class H:
        def post(self, url, json, timeout):
            assert url.endswith("/sources_to_targets") and json["costing"] == "truck"
            n = len(json["sources"])
            return type("R", (), {"json": lambda s: {"sources_to_targets": [[{"time": 0 if i == j else 111}
                                                                                for j in range(n)] for i in range(n)]}})()
    t = vrp.valhalla_travel([(43.6, -79.4), (43.7, -79.3)], "http://valhalla.test", http=H())
    assert t.matrix[((43.6, -79.4), (43.7, -79.3))] == 111.0
    class Down:
        def post(self, *a, **k):
            raise OSError("down")
    assert vrp.valhalla_travel([(1, 1), (2, 2)], "http://x", http=Down()) is None


def test_routes_registered():
    from porterchain_api.main import app
    paths = set(app.openapi()["paths"])
    for p in ("/safety-stop", "/end-of-shift", "/equipment-check", "/batches/routes/{route_id}/unlabelled"):
        assert any(x.endswith(p) for x in paths), p
    for p in ("/v1/admin/ops-rules/exception-codes",
              "/v1/admin/ops-rules/locations", "/v1/admin/ops-rules/orders/{order_id}/change-check",
              "/v1/merchant/claims/orders/{order_id}/concealed-damage"):
        assert p in paths, p


def test_alcohol_and_lq_dangerous_goods():
    assert rules.alcohol_problem(text="Red wine 6 bottles") == "alcohol_not_carried"
    assert rules.alcohol_problem(contains_alcohol=True) and rules.alcohol_problem(text="Ginger tea") is None
    ok = rules.lq_check([{"kind": "perfume", "inner_l": 0.1}, {"kind": "aerosol", "inner_l": 0.4}],
                        package_gross_kg=4, lq_mark_photo="k")
    assert ok["ok"] and ok["un_numbers"] == ["UN1266", "UN1950"]
    bad = rules.lq_check([{"kind": "paint", "inner_l": 1}, {"kind": "aerosol", "inner_l": 2}],
                         package_gross_kg=31, lq_mark_photo=None)
    assert set(bad["problems"]) == {"dg_not_accepted:paint", "inner_over_limit:aerosol", "package_over_30kg",
                                    "lq_mark_missing"}
    assert rules.lq_check([{"kind": "aerosol", "inner_l": 0.1, "contains": ["6.1"]}], package_gross_kg=1,
                          lq_mark_photo="k")["problems"] == ["aerosol_with_toxic_corrosive_or_oxygen"]
    assert "lq_mark_too_small" in rules.lq_check([{"kind": "perfume", "inner_l": 0.1}], package_gross_kg=1,
                                                 lq_mark_photo="k", mark_side_mm=60)["problems"]
    assert rules.lq_check([{"kind": "perfume", "inner_l": 0.1}], package_gross_kg=1, lq_mark_photo="k",
                          mark_side_mm=60, small_package=True)["ok"]
    from types import SimpleNamespace as NS

    from porterchain_api.merchant_engine.booking_validation import BookingValidationError, check_declarations
    with pytest.raises(BookingValidationError):
        check_declarations(NS(contains_alcohol=True))
    check_declarations(NS(dangerous_goods=True, dg_limited_quantity={
        "items": [{"kind": "perfume", "inner_l": 0.1}], "package_gross_kg": 2, "lq_mark_photo": "k"}))
    with pytest.raises(BookingValidationError):
        check_declarations(NS(dangerous_goods=True, dg_limited_quantity={"items": [{"kind": "perfume"}]}))


def test_no_overnight_failed_and_same_day_transfer():
    from porterchain_api.batch_engine import scenarios as S
    assert S.failed_disposition({"attempts": 1}, None) == {"action": "reattempt", "attempt": 2, "same_day": True}
    assert S.failed_disposition({"attempts": 2}, None) == {"action": "return_to_sender", "same_day": True}
    assert S.failed_disposition({"attempts": 2}, {"order": ["depot"]})["action"] == "return_to_sender"
    x = S.cross_dock([{"barcode": "A", "zone": "Z1"}, {"barcode": "B", "zone": "Z9"}], {"Z1": "r1"})
    assert x["depot_storage"] is False and x["return_to_sender_same_day"] == ["B"] and x["outbound"] == {"r1": ["A"]}


def test_dolly_replaces_two_person_price_unchanged():
    from porterchain_pricing.standard_card import STANDARD_V1_LINES as L
    from porterchain_pricing.standard_card import Item, quote
    assert L["add_ons"]["dolly"]["cents"] == 2000 and "price_pending" not in L["add_ons"]["dolly"]  # Ravi: $20
    q = quote([Item(kind="furniture", furniture_class="F3", weight_kg=50)], "Z1", add_ons={"two_person": 1})
    assert any(x["key"] == "addon:dolly" for x in q["lines"])
    with pytest.raises(ValueError):
        quote([Item(kind="furniture", furniture_class="F1", weight_kg=5)], "Z1", add_ons={"white_glove": 1})


def test_edi_214_and_856():
    from porterchain_api.ops_rules import edi
    at = datetime(2026, 10, 29, 14, 5, tzinfo=UTC)
    ps = [{"id": "p1", "barcode": "PCB1", "client_labels": ["#77"], "recipient": "Ann", "address": "1 King St"}]
    t = edi.x12_214(ps, [{"parcel_id": "p1", "kind": "pickup", "at": at},
                         {"parcel_id": "p1", "kind": "delivered", "at": at + timedelta(hours=1)}], now=at)
    assert t.startswith("ISA*") and "ST*214*" in t and "AT7*AF*NS" in t and "AT7*D1*NS" in t and t.endswith("IEA*1*000000001~")
    m = edi.x12_856({"id": "b1"}, ps, now=at)
    assert "ST*856*" in m and "MAN*GM*PCB1" in m and "REF*CR*#77" in m and "TD1*CTN*1" in m
    from porterchain_api.main import app
    assert "/v1/admin/ops-rules/edi/batches/{batch_id}/{kind}" in app.openapi()["paths"]
