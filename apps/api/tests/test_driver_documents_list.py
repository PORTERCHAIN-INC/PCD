"""Driver documents list maps seed files[] + verified flags into portal rows."""

from __future__ import annotations

from types import SimpleNamespace

from porterchain_driver.documents import DocumentsService
from porterchain_driver.insurance import InsuranceService


def test_list_documents_merges_seed_files_and_verified_flags() -> None:
    driver = SimpleNamespace(
        license_verified=True,
        insurance_verified=True,
        vehicle_verified=True,
        documents={
            "files": [
                {"doc_type": "driver_license", "file_url": "https://example.test/l.pdf"},
                {"doc_type": "insurance", "file_url": "https://example.test/i.pdf"},
                {"doc_type": "vehicle_registration", "file_url": "https://example.test/r.pdf"},
            ],
            "abstract": {"verified": True, "status": "complete"},
        },
    )
    rows = {row["type"]: row for row in DocumentsService().list_documents(driver)}
    assert rows["license"]["url"] == "https://example.test/l.pdf"
    assert rows["license"]["verified"] is True
    assert rows["license"]["status"] != "missing"
    assert rows["insurance"]["verified"] is True
    assert rows["abstract"]["verified"] is True


def test_insurance_status_verified_copy(monkeypatch) -> None:
    from porterchain_driver import vehicle as vehicle_mod

    monkeypatch.setattr(vehicle_mod.VehicleService, "get_active_vehicle", lambda self, db, driver_id: None)
    driver = SimpleNamespace(
        insurance_verified=True,
        vehicle_verified=True,
        license_verified=True,
        background_check_status="cleared",
        documents={},
        id="d1",
    )
    snap = InsuranceService().status(None, driver)
    assert snap["verified"] is True
    assert snap["status"] == "verified"
