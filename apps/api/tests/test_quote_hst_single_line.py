"""Doc 72 HST line must appear once: merchant pictures carry it in tax_cents, not again in line_items."""

from porterchain_api.merchant_engine.quote_snapshot import merchant_line_items, merchant_quote_picture

BD = {
    "items": [
        {"code": "base", "label": "Base", "amount_cents": 6500},
        {"code": "hst", "label": "HST (13%)", "amount_cents": 845},
    ],
    "summary": {"subtotal_cents": 6500, "tax_cents": 845, "final_cents": 7345},
}


def test_merchant_line_items_drop_hst_line():
    assert [i["code"] for i in merchant_line_items(BD)] == ["base"]


def test_merchant_picture_shows_hst_once_and_adds_up():
    pic = merchant_quote_picture(BD)
    assert pic["tax_cents"] == 845
    assert sum(i["amount_cents"] for i in pic["line_items"]) + pic["tax_cents"] == pic["amount_cents"]
