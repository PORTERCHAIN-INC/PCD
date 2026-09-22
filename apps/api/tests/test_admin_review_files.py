"""Admin document review includes mobile keyed uploads, not only files[]."""

from porterchain_api.admin_engine.driver_documents import admin_review_files


def test_admin_review_files_includes_mobile_uploads_and_photos() -> None:
    files = admin_review_files(
        {
            "license": {
                "status": "pending_review",
                "verified": False,
                "url": "data:image/jpeg;base64,abc",
                "uploaded_at": "2026-09-22T12:00:00+00:00",
            },
            "insurance": {"status": "pending_review", "url": "https://files.test/ins.pdf"},
            "vehicle_photos": [
                {
                    "id": "p1",
                    "url": "data:image/jpeg;base64,photo",
                    "status": "pending_review",
                    "label": "Van",
                }
            ],
        }
    )
    by_type = {row["doc_type"]: row for row in files}
    assert by_type["license"]["file_url"] == "data:image/jpeg;base64,abc"
    assert by_type["license"]["status"] == "pending_review"
    assert by_type["insurance"]["file_url"] == "https://files.test/ins.pdf"
    assert by_type["vehicle_photo"]["label"] == "Van"
    assert by_type["vehicle_photo"]["file_url"].startswith("data:image")


def test_assign_blockers_are_sentences() -> None:
    from types import SimpleNamespace

    from porterchain_api.admin_engine.driver_documents import assign_blockers

    driver = SimpleNamespace(
        status="PENDING",
        license_verified=False,
        insurance_verified=False,
        vehicle_verified=False,
        background_check_status="pending",
        documents={},
    )
    blockers = assign_blockers(driver, active_vehicle_count=0)
    assert "Driver is not approved." in blockers
    assert "License is not verified." in blockers
    assert "No active vehicle." in blockers
    assert all("driver_" not in item for item in blockers)


def test_decide_document_rejects_without_reason() -> None:
    from types import SimpleNamespace

    from porterchain_api.admin_engine.driver_documents import decide_document

    driver = SimpleNamespace(
        id="d1",
        documents={"license": {"url": "data:image/jpeg;base64,abc", "status": "pending_review"}},
        license_verified=False,
        insurance_verified=False,
        vehicle_verified=False,
        background_check_status="pending",
    )
    try:
        decide_document(
            None,
            SimpleNamespace(user=SimpleNamespace(id="a")),
            driver,
            doc_type="license",
            decision="rejected",
            reason="  ",
            audit=lambda *args, **kwargs: None,
        )
    except ValueError as exc:
        assert str(exc) == "reason_required"
    else:
        raise AssertionError("expected reason_required")


def test_review_files_keep_rejection_reason() -> None:
    files = admin_review_files(
        {
            "insurance": {
                "url": "data:image/jpeg;base64,abc",
                "status": "rejected",
                "rejection_reason": "Photo is blurry",
            }
        }
    )
    assert files[0]["rejection_reason"] == "Photo is blurry"


def test_decide_document_clear_keeps_the_photo_pending() -> None:
    from types import SimpleNamespace

    from porterchain_api.admin_engine.driver_documents import decide_document

    driver = SimpleNamespace(
        id="d1",
        documents={
            "license": {
                "url": "data:image/jpeg;base64,abc",
                "status": "verified",
                "verified": True,
                "rejection_reason": "old",
            }
        },
        license_verified=True,
        insurance_verified=False,
        vehicle_verified=False,
        background_check_status="pending",
    )
    decide_document(
        None,
        SimpleNamespace(user=SimpleNamespace(id="a")),
        driver,
        doc_type="license",
        decision="cleared",
        audit=lambda *args, **kwargs: None,
    )
    entry = driver.documents["license"]
    assert entry["status"] == "pending_review"
    assert entry["verified"] is False
    assert "rejection_reason" not in entry
    assert entry["url"].startswith("data:image")
    assert driver.license_verified is False


def test_decide_document_rejects_vehicle_photo() -> None:
    from types import SimpleNamespace

    from porterchain_api.admin_engine.driver_documents import decide_document

    driver = SimpleNamespace(id="d1", documents={}, license_verified=False)
    try:
        decide_document(
            None,
            SimpleNamespace(user=SimpleNamespace(id="a")),
            driver,
            doc_type="vehicle_photo",
            decision="verified",
            audit=lambda *args, **kwargs: None,
        )
    except ValueError as exc:
        assert str(exc) == "invalid_doc_type"
    else:
        raise AssertionError("expected invalid_doc_type")


def test_upload_rejects_oversized_data_url() -> None:
    from types import SimpleNamespace

    from porterchain_driver.documents import DocumentsService

    driver = SimpleNamespace(documents={}, license_verified=True)
    try:
        DocumentsService().upload_document(
            None,
            driver,
            doc_type="license",
            file_url="data:image/jpeg;base64," + ("a" * 400_000),
        )
    except ValueError as exc:
        assert str(exc) == "file_too_large"
    else:
        raise AssertionError("expected file_too_large")
    assert driver.license_verified is True


def test_admin_review_files_does_not_duplicate_files_array() -> None:
    files = admin_review_files(
        {
            "files": [
                {
                    "id": "f1",
                    "doc_type": "driver_license",
                    "file_url": "https://files.test/license.pdf",
                }
            ],
            "license": {"url": "data:image/jpeg;base64,newer", "status": "pending_review"},
        }
    )
    assert len(files) == 1
    assert files[0]["file_url"] == "https://files.test/license.pdf"
