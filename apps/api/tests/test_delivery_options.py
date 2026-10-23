"""Shared delivery options: capture (all surfaces), driver view, Shopify note, label line."""

from __future__ import annotations

import shutil
import subprocess
from types import SimpleNamespace

import pytest

from porterchain_api.domain.delivery_options import (
    apply,
    from_shopify,
    label_line,
    normalize,
    summary_lines,
)
from porterchain_api.integrations.shopify_orders import map_shopify_order
from porterchain_api.reporting.thermal_pdf import render_thermal_labels
from porterchain_api.schemas_admin import AdminCreateOrderRequest
from porterchain_api.schemas_booking import AddressInput as BookingAddress
from porterchain_api.schemas_merchant import AddressInput as MerchantAddress
from porterchain_driver.next_stop import _access_fields

FULL = {
    "drop_method": "concierge",
    "unit": " 1204 ",
    "buzzer": "1204#",
    "call_on_arrival": True,
    "load_help": "yes",
    "note": "  Fragile,   glass top ",
}


def test_normalize_cleans_and_drops_empty() -> None:
    assert normalize({}) is None
    assert normalize({"drop_method": "nope", "unit": "  "}) is None
    assert normalize(FULL) == {
        "drop_method": "concierge",
        "unit": "1204",
        "buzzer": "1204#",
        "call_on_arrival": True,
        "load_help": True,
        "note": "Fragile, glass top",
    }


def test_summary_lines_include_site_access_and_skip_pickup_noise() -> None:
    drop = apply({"formatted": "1 King St W", "site_access_notes": "Gate 7, ask foreman Bo"}, FULL)
    assert summary_lines(drop) == [
        "Leave with concierge / reception",
        "Unit 1204",
        "Buzzer 1204#",
        "Call on arrival",
        "Needs help loading / unloading",
        "Fragile, glass top",
        "Site access: Gate 7, ask foreman Bo",
    ]
    assert apply({"formatted": "x", "delivery_options": {"unit": "1"}}, {}) == {"formatted": "x"}


def test_label_line_is_short_and_has_no_free_text() -> None:
    line = label_line(apply({"formatted": "x"}, FULL))
    assert line is not None and line.startswith("Leave with concierge / reception · Unit 1204 · Buzz 1204#")
    assert "Fragile" not in line and len(line) <= 90
    assert label_line({"formatted": "x"}) is None


@pytest.mark.parametrize("model", [BookingAddress, MerchantAddress])
def test_address_input_round_trip(model) -> None:
    plain = model(formatted="1 King St W")
    assert "delivery_options" not in plain.model_dump()
    rich = model(formatted="1 King St W", delivery_options={"drop_method": "leave_at_door", "buzzer": "12"})
    assert rich.model_dump()["delivery_options"] == {"drop_method": "leave_at_door", "buzzer": "12"}
    empty = model(formatted="1 King St W", delivery_options={"unit": " "})
    assert "delivery_options" not in empty.model_dump()


def test_admin_create_accepts_delivery_options() -> None:
    body = AdminCreateOrderRequest(
        merchant_id="m", order_kind="single", scheduled_at="2026-10-22T12:00:00Z",
        stops=[{"type": "pickup", "formatted": "A"}, {"type": "dropoff", "formatted": "B"}],
        delivery_options={"drop_method": "hand_to_recipient"},
    )
    assert apply({"formatted": "B"}, body.delivery_options)["delivery_options"] == {
        "drop_method": "hand_to_recipient"
    }


def test_shopify_order_note_and_attributes_reach_the_dropoff() -> None:
    pickup = MerchantAddress(formatted="100 Britannia Rd E, Mississauga ON L4Z 1S3", postal="L4Z 1S3")
    payload = {
        "id": 999002,
        "name": "#1002",
        "note": "Please leave with the concierge",
        "note_attributes": [{"name": "Buzzer code", "value": "0412"}, {"name": "quote_id", "value": "q1"}],
        "shipping_address": {"address1": "1 King St W", "address2": "Apt 4", "city": "Toronto",
                             "province_code": "ON", "zip": "M5V 2T6", "name": "Ada"},
        "line_items": [{"grams": 500, "quantity": 1}],
    }
    body = map_shopify_order(payload, pickup=pickup)
    opts = body.dropoff.model_dump()["delivery_options"]
    assert opts == {"note": "Please leave with the concierge", "buzzer": "0412"}
    assert from_shopify({"note": " ", "note_attributes": []}) is None
    assert "delivery_options" not in map_shopify_order({**payload, "note": None, "note_attributes": []},
                                                       pickup=pickup).dropoff.model_dump()


def test_driver_sees_options_and_site_access_on_the_drop_only() -> None:
    addr = apply({"formatted": "1 King St W", "site_access_notes": "Gate 7"}, FULL)
    drop = SimpleNamespace(address=addr, stop_type="dropoff", special_instructions="Receiver: Ada")
    f = _access_fields(drop)
    assert f["access_unit"] == "1204" and f["access_buzzer"] == "1204#" and f["call_on_arrival"] is True
    assert f["drop_method"] == "concierge" and f["load_help"] is True
    assert "Site access: Gate 7" in f["delivery_notes"]
    pick = SimpleNamespace(address=addr, stop_type="pickup", special_instructions=None)
    assert _access_fields(pick)["delivery_notes"] == []


@pytest.mark.skipif(not shutil.which("pdftotext"), reason="poppler not installed")
def test_label_prints_delivery_line(tmp_path) -> None:
    pdf = render_thermal_labels([{
        "route_hint": "R1", "stop_sequence": 1, "from_line": "A", "to_line": "B", "order_number": "ORD-1",
        "tracking_base": "PC1", "qr_payload": "x", "tracking_suffix": "PC1-1",
        "parcel_index": 1, "total_parcels": 1, "delivery_line": "Leave at door · Buzz 12",
    }])
    path = tmp_path / "l.pdf"
    path.write_bytes(pdf)
    text = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True, check=True).stdout
    assert "Leave at door" in text and "Buzz 12" in text


@pytest.mark.usefixtures("quiet_pool")
def test_driver_job_list_and_route_card_carry_delivery_notes(db, monkeypatch) -> None:
    from porterchain_api.dispatch_engine.driver_route import _stop_notes
    from porterchain_driver.jobs import JobsService
    from porterchain_driver.next_stop import NextStopResolver
    from tests.test_dispatch_phase2 import S, W, _driver, _order

    monkeypatch.setattr("porterchain_driver.sequence_store.read_sequence", lambda *_a, **_k: None)
    monkeypatch.setattr(NextStopResolver, "_driver_origin", lambda *_a, **_k: None)
    d = _driver(db)
    o = _order(db, W, apply(dict(S), {"drop_method": "leave_at_door", "load_help": True}),
               state="DRIVER_ACCEPTED", assigned_driver_id=d.id, special_instructions="Side door")
    db.commit()
    jobs = JobsService().list_jobs(db, d)
    rows = [j for j in [jobs.get("current"), *jobs.get("upcoming", [])] if j and j["order_id"] == o.id]
    assert rows and rows[0]["delivery_notes"] == ["Leave at door", "Needs help loading / unloading"]
    assert _stop_notes(o, "drop") == "Leave at door · Needs help loading / unloading · Side door"
    assert _stop_notes(o, "pickup") == "Side door"
