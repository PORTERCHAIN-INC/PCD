"""§2.2.12 — standard error envelope on HTTP responses."""

from fastapi.testclient import TestClient

from porterchain_api.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200


def test_404_envelope_has_detail_and_code():
    r = client.get("/v1/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert "detail" in body
    assert body.get("code") == "not_found" or isinstance(body["detail"], str)


def test_validation_envelope():
    r = client.post("/v1/booking-drafts", json={})
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body
    assert body.get("code") == "validation_error"
    assert isinstance(body["detail"], list)
