from porterchain_pricing.tax.provinces import PROVINCES, province_from_address, province_from_postal


def test_rates_follow_destination_province():
    assert PROVINCES["ON"].freight_percent() == 13.0
    assert PROVINCES["NS"].freight_percent() == 14.0
    assert PROVINCES["NB"].freight_percent() == 15.0
    assert PROVINCES["AB"].freight_percent() == 5.0
    # PST never applies to freight; QST only when registered.
    assert PROVINCES["BC"].freight_percent() == 5.0
    assert PROVINCES["QC"].freight_percent() == 5.0
    assert PROVINCES["QC"].freight_percent(collect_qst=True) == 14.975
    assert PROVINCES["QC"].label(collect_qst=True) == "GST 5% + QST 9.975%"


def test_province_detection():
    assert province_from_postal("M5V 2T6") == "ON"
    assert province_from_postal("h2x1y4") == "QC"
    assert province_from_address({"postal_code": "V6B 1A1"}) == "BC"
    assert province_from_address({"province": "Quebec"}) == "QC"
    assert province_from_address({"formatted": "100 King St W, Toronto, ON M5H 1A1, Canada"}) == "ON"
    assert province_from_address({"formatted": "1 Main St, Halifax, NS"}) == "NS"
    assert province_from_address({"formatted": "somewhere"}) is None
