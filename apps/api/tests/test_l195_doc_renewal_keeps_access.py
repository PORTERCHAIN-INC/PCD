"""L195: re-uploading a still-valid verified document must not drop the verified flag."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from porterchain_driver.documents import DocumentsService as Svc

PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def _driver(**doc):
    return SimpleNamespace(id="d1", license_verified=True, documents={"license": doc})


def test_renewal_keeps_verified():
    d = _driver(status="verified", verified=True, expires_at="2099-01-01")
    Svc().upload_document(MagicMock(), d, doc_type="license", file_url=PNG)
    assert d.license_verified is True
    assert d.documents["license"]["status"] == "pending_review"


def test_expired_upload_clears_verified():
    d = _driver(status="verified", verified=True, expires_at="2000-01-01")
    Svc().upload_document(MagicMock(), d, doc_type="license", file_url=PNG)
    assert d.license_verified is False
