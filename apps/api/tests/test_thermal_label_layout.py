"""4×6 label layout: no overlaps, inside the page, scan codes unchanged."""

from __future__ import annotations

import itertools

import pytest

from porterchain_api.reporting.thermal_pdf import (
    FOOTER_RESERVE,
    HRI_GAP,
    LABEL_HEIGHT,
    LABEL_WIDTH,
    MARGIN,
    layout_page,
    render_thermal_labels,
)

LONG_ADDR = (
    "Alexandra Montgomery-Fitzgerald-Worthington, 3059 Max Khan Blvd Unit 1204 Buzz 9981, "
    "Oakville, ON L6H 0S6, Canada, Oakville, L6H 0S6"
)


def _page(**over):
    base = {
        "route_hint": "",
        "stop_sequence": 1,
        "from_line": "KAYLULU",
        "to_line": "3059 Max Khan Blvd, Oakville, ON L6H 0S6",
        "order_number": "ORD-20261015-71FB4B",
        "tracking_base": "PC-20261015-F4BC86",
        "qr_payload": "PC1.signed-opaque-code-0123456789abcdef",
        "tracking_suffix": "PC-20261015-F4BC86-02",
        "parcel_index": 2,
        "total_parcels": 2,
        "item_line": "Item 1 · box 2 of 2",
    }
    base.update(over)
    return base


CASES = [
    _page(),
    _page(
        to_line=LONG_ADDR,
        from_line="Some Very Long Merchant Name Incorporated, 10 Merton Rd, Brampton, L6T 0A1",
    ),
    _page(
        to_line="X" * 400,
        route_hint="WAVE-NORTH-0042",
        stop_sequence=17,
        item_line="Item 3 · box 1 of 4",
        parcel_index=7,
        total_parcels=12,
        is_sandbox=True,
        delivery_line="Help load/unload · Unit 1204 · Concierge · Buzz 9981 · Call on arrival · "
        + "Note: side door by the garage, ring twice, dog is friendly " * 3,
    ),
    _page(delivery_line="Leave at door · Unit 4 · Buzz 1234"),
    _page(
        to_line=None,
        from_line=None,
        order_number=None,
        tracking_suffix="",
        qr_payload="",
    ),
]


@pytest.mark.parametrize("page", CASES)
def test_no_overlap_and_inside_page(page):
    boxes = [b for b in layout_page(page) if b.kind != "rule"]
    for b in boxes:
        assert b.x0 >= MARGIN - 0.01 and b.x1 <= LABEL_WIDTH - MARGIN + 0.01, b
        assert b.y1 <= LABEL_HEIGHT - MARGIN + 0.01, b
        assert b.y0 >= MARGIN + FOOTER_RESERVE - 0.01, b
    for a, b in itertools.combinations(boxes, 2):
        assert not a.overlaps(b), (a, b)


def test_long_address_keeps_postal_code():
    texts = " ".join(
        b.text for b in layout_page(_page(to_line=LONG_ADDR)) if b.kind == "text"
    )
    assert "L6H 0S6" in texts
    assert "Oakville" in texts


def test_hri_text_sits_below_barcode_with_gap():
    boxes = layout_page(_page())
    bar = next(b for b in boxes if b.kind == "barcode")
    hri = next(
        b for b in boxes if b.kind == "text" and b.text == "PC-20261015-F4BC86-02"
    )
    assert hri.y1 <= bar.y0 - HRI_GAP + 0.01


def test_empty_placeholders_hidden_and_single_box_count():
    texts = [b.text for b in layout_page(_page()) if b.kind == "text"]
    joined = " | ".join(texts)
    assert "ROUTE" not in joined and "STOP" not in joined and "COD" not in joined
    assert texts.count("BOX 2 of 2") == 1
    assert "Parcel" not in joined and "Item 1 · box 2 of 2" not in joined


def test_route_stop_and_extra_item_shown_when_real_and_never_cod():
    texts = " | ".join(
        b.text
        for b in layout_page(
            _page(
                route_hint="R12",
                stop_sequence=3,
                cod_line="$45.00",  # legacy key from an old caller: never printed
                item_line="Item 2 · box 1 of 3",
                parcel_index=4,
                total_parcels=6,
            )
        )
        if b.kind == "text"
    )
    assert "ROUTE R12" in texts and "STOP #3" in texts and "COD" not in texts
    assert "BOX 4 of 6" in texts and "Item 2 · box 1 of 3" in texts


def test_scan_payloads_unchanged():
    boxes = layout_page(_page())
    assert (
        next(b for b in boxes if b.kind == "qr").payload
        == "PC1.signed-opaque-code-0123456789abcdef"
    )
    assert (
        next(b for b in boxes if b.kind == "barcode").payload == "PC-20261015-F4BC86-02"
    )
    assert render_thermal_labels([_page()]).startswith(b"%PDF")


def test_delivery_line_printed_under_address_and_wrapped():
    page = _page(delivery_line="Leave at door · Unit 4 · Buzz 1234 · Call on arrival")
    texts = [b.text for b in layout_page(page) if b.kind == "text"]
    joined = " ".join(texts)
    assert "Leave at door" in joined and "Buzz 1234" in joined
    pdf = render_thermal_labels([page])
    assert pdf.startswith(b"%PDF")
