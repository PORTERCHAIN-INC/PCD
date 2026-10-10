import pytest

from porterchain_api.platform.tax_registration import (
    normalize_finance,
    normalize_gst_hst,
    registration_status,
    safe_gst_hst,
)


@pytest.mark.parametrize("raw", ["123456789RT0001", "123456789 RT0001", "123-456-789 rt 0001", " 123456789rt0001 "])
def test_accepts_cra_formats(raw):
    assert normalize_gst_hst(raw) == "123456789 RT0001"


@pytest.mark.parametrize("raw", ["12345678RT0001", "123456789", "123456789 RP0001", "PENDING-GST-HST-NUMBER"])
def test_rejects_bad(raw):
    with pytest.raises(ValueError):
        normalize_gst_hst(raw)
    assert safe_gst_hst(raw) == ""


def test_blank_and_finance_and_status():
    assert normalize_gst_hst("") == ""
    assert normalize_finance({"gst_hst_number": "123456789rt0001", "tax_name": "HST"}) == {
        "gst_hst_number": "123456789 RT0001", "tax_name": "HST"}
    assert registration_status("")["warning"] and not registration_status("")["set"]
    assert registration_status("123456789 RT0001")["warning"] is None
