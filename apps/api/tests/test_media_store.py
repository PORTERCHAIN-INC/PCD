"""Doc 61/62: proof photos + signatures in Garage (self-hosted S3). Garage test opt-in via scripts/test-media.sh."""
import base64
import os
from pathlib import Path

import httpx
import pytest

from porterchain_api.media_store import s3
from porterchain_api.media_store import service as M

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
JPG = b"\xff\xd8\xff" + b"0" * 32
ENV = Path("/tmp/pcd-test-garage/env")


def test_sniff():
    assert M.sniff(PNG) == ("image/png", "png")
    assert M.sniff(JPG)[1] == "jpg"
    with pytest.raises(ValueError):
        M.sniff(b"GIF89a....")


def test_unconfigured_raises(monkeypatch):
    monkeypatch.delenv("POD_S3_ENDPOINT", raising=False)
    with pytest.raises(RuntimeError):
        M.store_photo("d1", JPG)


def test_key_shape_rejects_traversal():
    assert not M.is_media_key("../etc/passwd")
    assert not M.is_media_key("pod/photo/x/../../a.jpg")
    assert M.is_media_key(M._key("photo", "drv-1", "jpg"))


def test_signature_validation():
    cfg = s3.S3Config("http://x", "b", "k", "s", "garage")
    with pytest.raises(ValueError):
        M.store_signature("d", "data:image/jpeg;base64,AAAA", signer_name="Al", cfg=cfg)
    url = "data:image/png;base64," + base64.b64encode(PNG).decode()
    with pytest.raises(ValueError):
        M.store_signature("d", url, signer_name=" ", cfg=cfg)


def test_put_signs_request():
    seen = {}

    def handler(req: httpx.Request):
        seen["auth"] = req.headers.get("authorization", "")
        seen["path"] = req.url.path
        return httpx.Response(200)
    cfg = s3.S3Config("http://garage.test", "pod", "AK", "SK", "garage")
    out = M.store_photo("drv-1", JPG, cfg=cfg, http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert seen["auth"].startswith("AWS4-HMAC-SHA256 Credential=AK/")
    assert seen["path"] == "/pod/" + out["key"]


def _garage_env():
    if not ENV.exists():
        pytest.skip("test garage not running (scripts/test-media.sh up)")
    return dict(line.split("=", 1) for line in ENV.read_text().split())


def test_garage_roundtrip(monkeypatch):
    for k, v in _garage_env().items():
        monkeypatch.setenv(k, v)
    out = M.store_photo("drv-1", JPG)
    data, ctype = s3.get_object(s3.config_from_env(), out["key"])
    assert data == JPG and ctype == "image/jpeg"
    sig = M.store_signature("drv-1", "data:image/png;base64," + base64.b64encode(PNG).decode(), signer_name="Ann")
    assert s3.get_object(s3.config_from_env(), sig["key"])[0] == PNG
    with pytest.raises(LookupError):
        s3.get_object(s3.config_from_env(), "pod/photo/x/2026/01/" + "0" * 36 + ".jpg")


def test_require_own_keys():
    k = M._key("photo", "drv-1", "jpg")
    M.require_own_keys({"photo_keys": [k], "media_key": None}, "drv-1")
    with pytest.raises(ValueError):
        M.require_own_keys({"photo_key": "photo/1"}, "drv-1")
    with pytest.raises(PermissionError):
        M.require_own_keys({"signature_key": k}, "drv-2")


def test_driver_upload_and_pod_routes(monkeypatch):
    from types import SimpleNamespace

    from fastapi.testclient import TestClient

    from porterchain_api.driver_engine.rbac import DriverContext
    from porterchain_api.main import app
    from porterchain_api.routers.driver._deps import get_driver_context
    stored = {}
    monkeypatch.setattr(s3, "config_from_env", lambda: s3.S3Config("http://g", "b", "k", "s"))
    monkeypatch.setattr(s3, "put_object", lambda cfg, key, data, ct, http=None: stored.__setitem__(key, data))
    app.dependency_overrides[get_driver_context] = lambda: DriverContext(
        driver=SimpleNamespace(id="drv-1", status="APPROVED"))
    try:
        c = TestClient(app)
        r = c.post("/driver-api/v1/media/photo", files={"file": ("a.jpg", JPG, "image/jpeg")})
        assert r.status_code == 200 and r.json()["key"] in stored
        assert c.post("/driver-api/v1/media/photo", files={"file": ("a.gif", b"GIF89a", "image/gif")}).status_code == 422
        url = "data:image/png;base64," + base64.b64encode(PNG).decode()
        r = c.post("/driver-api/v1/media/signature", json={"data_url": url, "signer_name": "Ann Lee"})
        assert r.status_code == 200 and r.json()["key"].startswith("pod/signature/drv-1/")
        bad = c.post("/driver-api/v1/routes/r/stops/s/pod-signature", json={"signature_key": "pod/x"})
        assert bad.status_code == 422
        other = M._key("signature", "drv-2", "png")
        assert c.post("/driver-api/v1/routes/r/stops/s/pod-signature", json={"signature_key": other}).status_code == 403
        jurl = "data:image/jpeg;base64," + base64.b64encode(JPG).decode()
        r = c.post("/driver-api/v1/media/photo-data", json={"data_url": jurl})
        assert r.status_code == 200 and r.json()["key"].startswith("pod/photo/drv-1/")
        assert c.post("/driver-api/v1/media/photo-data", json={"data_url": "data:text/plain;base64,aGVsbG8gd29ybGQgaGVsbG8="}).status_code == 422
    finally:
        app.dependency_overrides.pop(get_driver_context, None)
