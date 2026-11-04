"""Admin media viewer + merchant EDI download (own batches only)."""
import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, AdminRole
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.batch_engine import service as B
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_api.media_store import s3
from porterchain_api.media_store import service as M


def _admin(role):
    return lambda: AdminContext(user=SimpleNamespace(id="a1", email="a@x"), role=role)


def test_admin_media_view(monkeypatch):
    key = M._key("photo", "drv-1", "jpg")
    monkeypatch.setattr(s3, "config_from_env", lambda: s3.S3Config("http://g", "b", "k", "s"))
    monkeypatch.setattr(s3, "get_object", lambda cfg, k, http=None: (b"\xff\xd8\xffJ", "image/jpeg"))
    try:
        app.dependency_overrides[get_admin_context] = _admin(AdminRole.DISPATCHER)
        c = TestClient(app)
        r = c.get("/v1/admin/ops-rules/media/" + key)
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
        assert c.get("/v1/admin/ops-rules/media/pod/photo/../../x").status_code == 404
        app.dependency_overrides[get_admin_context] = _admin(AdminRole.FINANCE) if hasattr(AdminRole, "FINANCE") \
            else _admin(AdminRole.SALES)
        assert c.get("/v1/admin/ops-rules/media/" + key).status_code == 403
    finally:
        app.dependency_overrides.pop(get_admin_context, None)


def test_merchant_edi_own_batch_only(db):
    mid, other = str(uuid.uuid4()), str(uuid.uuid4())
    b = B.create_batch(db, mid, "address,client_label\n10 King St W Toronto,#5001\n")
    app.dependency_overrides[get_db] = lambda: db
    try:
        c = TestClient(app)
        app.dependency_overrides[get_merchant_context] = lambda: SimpleNamespace(merchant=SimpleNamespace(id=mid))
        r = c.get(f"/v1/merchant/batches/{b.id}/edi/856")
        assert r.status_code == 200 and r.text.startswith("ISA") and "attachment" in r.headers["content-disposition"]
        assert c.get(f"/v1/merchant/batches/{b.id}/edi/999").status_code == 404
        app.dependency_overrides[get_merchant_context] = lambda: SimpleNamespace(merchant=SimpleNamespace(id=other))
        assert c.get(f"/v1/merchant/batches/{b.id}/edi/856").status_code == 404
    finally:
        app.dependency_overrides.pop(get_merchant_context, None)
        app.dependency_overrides.pop(get_db, None)
