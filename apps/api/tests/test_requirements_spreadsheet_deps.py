"""Spreadsheet deps must ship in the Docker/CI install (requirements.txt).

Bug: openpyxl/xlrd were only in pyproject.toml, so containers built from
requirements.txt raised ``excel_support_unavailable`` on .xlsx/.xls bulk
uploads and Excel report exports.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from porterchain_api.merchant_engine.import_ingest import parse_xlsx_bytes
from porterchain_api.merchant_engine.reporting_metrics import rows_to_excel

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"


def _requirement_names() -> set[str]:
    names: set[str] = set()
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = re.match(r"[A-Za-z0-9_.\-]+", line)
        if match:
            names.add(match.group(0).lower().replace("_", "-"))
    return names


def test_requirements_txt_ships_spreadsheet_libraries() -> None:
    names = _requirement_names()
    assert "openpyxl" in names, "bulk_service/import_ingest/reporting_metrics import openpyxl"
    assert "xlrd" in names, "import_ingest.parse_xls_bytes imports xlrd"


def test_excel_export_round_trips_through_import() -> None:
    data = rows_to_excel(
        [{"reference": "PO-1", "postal_code": "M5V 2T6"}],
        ["reference", "postal_code"],
        sheet_name="Orders",
    )
    sheet = parse_xlsx_bytes(data)
    assert sheet.sheet_name == "Orders"
    assert sheet.rows == [{"reference": "PO-1", "postal_code": "M5V 2T6"}]


def test_legacy_xls_reader_is_installed() -> None:
    assert importlib.util.find_spec("xlrd") is not None, "legacy .xls uploads need xlrd"
