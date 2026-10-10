"""CSV/XLSX ingest + column mapping for route import."""

from porterchain_api.merchant_engine.import_column_mapper import (
    apply_mapping,
    suggest_mapping,
)
from porterchain_api.merchant_engine.import_ingest import parse_csv_bytes, parse_upload


def test_parse_csv_normalizes_headers():
    data = b"Ship To,Name,Phone\n100 King St W,Ada,4165551212\n"
    sheet = parse_csv_bytes(data)
    assert "ship_to" in sheet.headers
    assert sheet.rows[0]["ship_to"] == "100 King St W"


def test_parse_upload_routes_csv():
    sheet = parse_upload("stops.csv", b"address,stop_type\n1 Main St,pickup\n2 Main St,drop\n")
    assert len(sheet.rows) == 2


def test_mapper_builds_stops_ready_rows():
    sheet = parse_csv_bytes(
        b"sequence,type,delivery_address\n1,pickup,100 King St W Toronto\n2,drop,200 Bay St Toronto\n"
    )
    mapping = suggest_mapping(sheet.headers)
    rows = apply_mapping(sheet.rows, mapping)
    assert rows[0].get("address")
    assert rows[0].get("sequence") == "1" or rows[0].get("stop_type")
