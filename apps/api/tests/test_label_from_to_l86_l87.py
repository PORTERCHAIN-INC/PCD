"""L86: FROM line carries pickup address + phone. L87: TO keeps the city after a named place."""
from porterchain_api.reporting.label_service import _from_line
from porterchain_api.reporting.thermal_pdf import _address_text


def test_to_keeps_city_after_named_place():
    raw = "Toronto City Hall, 100 Queen Street West, Toronto, ON, M5H 2N2, Toronto, M5H 2N2"
    assert _address_text(raw) == "Toronto City Hall, 100 Queen Street West, Toronto, ON, M5H 2N2"


def test_to_keeps_province_after_word_containing_on():
    assert _address_text("Continental Building, 18 King Street East, Toronto, ON, M5E 1K0") == (
        "Continental Building, 18 King Street East, Toronto, ON, M5E 1K0"
    )


def test_from_line_has_address_and_phone():
    pickup = {"formatted": "1 Yonge Street, Toronto, ON, M5E 1E5", "postal": "M5E 1E5"}
    line = _from_line("Acme", pickup, "+1 416 555 0100")
    assert line.startswith("Acme, 1 Yonge Street")
    assert "M5E 1E5" in line and line.endswith("Tel +1 416 555 0100")


def test_from_line_pickup_phone_wins_and_name_only_fallback():
    assert _from_line("Acme", {"formatted": "1 A St", "phone": "111"}, "222").endswith("Tel 111")
    assert _from_line("Acme", {}, None) == "Acme"
