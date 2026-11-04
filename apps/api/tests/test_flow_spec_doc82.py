"""Doc 82 A-GF: generated guided flows."""
from types import SimpleNamespace

from porterchain_api.flow_engine import flow_spec as fs
from porterchain_api.flow_engine.service import flow_specs_for_order
from porterchain_api.org_engine import packs


def _docs(code, subtype=None, **flags):
    return fs.active_documents(packs.documents_for(code, subtype), flags), flags


def test_parcel_never_shows_id_or_seal():
    docs, flags = _docs("shopify_merchant")
    spec = fs.delivery_flow(docs, flags)
    cards = {s["card"] for s in spec["steps"]}
    assert spec["flow_id"] == "delivery_parcel"
    assert not cards & {"id_check", "seal_check", "temp_read", "signature"}


def test_pharmacy_always_has_seal_id_signature():
    docs, flags = _docs("small_shop", "pharmacy", rx=True)
    spec = fs.delivery_flow(docs, flags)
    caps = fs.all_captures(spec)
    assert spec["flow_id"] == "delivery_pharmacy_custody"
    assert {"seal_no", "id_name_match", "signature"} <= caps
    assert "temp" not in caps  # cold chain only when C6 fires
    docs2, flags2 = _docs("small_shop", "pharmacy", rx=True, cold_chain=True)
    assert "temp" in fs.all_captures(fs.delivery_flow(docs2, flags2))


def test_every_required_capture_appears():
    docs, flags = _docs("shopify_merchant", signature_required=True, age_restricted=True)
    spec = fs.delivery_flow(docs, flags)
    assert "signature_id" in docs and "signature" in fs.all_captures(spec)
    assert "under_19" in [b for s in spec["steps"] for b in s["block_if"]]
    docs, flags = _docs("warehouse_3pl", bol_required=True)
    spec = fs.delivery_flow(docs, flags)
    assert spec["flow_id"] == "delivery_b2b_dock_bol" and "bol_signature" in fs.all_captures(spec)


def test_failed_pharmacy_forces_same_day_return():
    spec = fs.delivery_flow({"rx_custody_log"}, {"failed": True, "rx": True})
    assert "same_day_return_required" in spec["steps"][0]["block_if"]


def test_pickup_modes_and_heavy_truck_dvir():
    assert fs.pickup_flow("on_demand")["steps"][0]["card"] == "accept_offer"
    assert fs.pickup_flow("hub_dropoff")["steps"][1]["card"] == "hub_scan_in"
    heavy = fs.pickup_flow("scheduled_daily", vehicle_gvwr_kg=5000)
    assert heavy["steps"][0]["card"] == "pre_trip_dvir"
    assert fs.pickup_flow("scheduled_daily", vehicle_gvwr_kg=3000)["steps"][0]["card"] == "navigate"
    assert fs.pickup_flow("recurring_route", multi_stop=True)["warn_if"] == ["out_of_sequence"]


def test_service_retail_order_without_org():
    order = SimpleNamespace(merchant_id=None, compliance_metadata={"signature_required": True}, status="assigned", stops=[])
    out = flow_specs_for_order(None, order)  # db unused without a merchant
    assert out["pickup"]["flow_id"] == "pickup_on_demand"
    assert out["delivery"]["flow_id"] == "delivery_parcel"  # retail matrix has no signature doc
    assert out["documents"] == ["pod"]


def test_server_cards_and_checks_exist_in_shared_package():
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[3] / "packages" / "driver-flows" / "src"
    if not root.exists():
        import pytest
        pytest.skip("monorepo package not present")
    copy = (root / "copy.ts").read_text()
    checks = (root / "checks.ts").read_text()
    for card in fs.CARDS:
        assert re.search(rf"\b{card}: \{{ title", copy), card
    specs = [fs.pickup_flow(m, vehicle_gvwr_kg=9000) for m in packs.PICKUP_MODES]
    for flags in ({}, {"failed": True, "rx": True}, {"sealed": True}, {"age_restricted": True}):
        for d in ({"pod"}, {"rx_custody_log", "cold_chain_log"}, {"bol"}, {"dolly"}, {"cold_chain_log"}, {"signature_id"}):
            specs.append(fs.delivery_flow(d, flags))
    for req in (True, False):
        specs.append(fs.with_instructions(fs.with_pickup_docs(fs.batch_pickup_flow(scan_required=req), ["bol"]), True))
        specs.append(fs.batch_delivery_flow(grouped=req, handling=["pharmacy", "signature"] if req else []))
    specs += [fs.batch_handover_flow("give"), fs.batch_handover_flow("receive"), fs.batch_close_flow()]
    for spec in specs:
        for s in spec["steps"]:
            assert s["card"] in fs.CARDS
            for b in s["block_if"]:
                assert re.search(rf"\b{b}: \(", checks), b
