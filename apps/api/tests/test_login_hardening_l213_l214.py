"""L213/L214: staff enroll response + invite emails use a redirect Keycloak accepts."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from porterchain_api.admin_engine import staff_accounts
from porterchain_api.auth import invitation_service, keycloak_admin
from porterchain_api.config import Settings
from porterchain_api.schemas_admin import StaffEnrollResponse

KC = Path(__file__).resolve().parents[3] / "infrastructure" / "keycloak"


def test_staff_payload_validates_as_enroll_response():
    user = SimpleNamespace(id="u1", email="a@b.test", role="read_only")
    payload = staff_accounts._payload(user, provisioned=True, email_sent=True, created=True)
    resp = StaffEnrollResponse(**payload)  # used to raise: expires_at missing -> 500
    assert resp.expires_at > 0


def test_admin_base_prefers_portal_url_unless_app_url_set():
    s = Settings(admin_portal_url="http://localhost:53002")
    assert keycloak_admin._admin_base(s) == "http://localhost:53002"
    s2 = Settings(admin_portal_url="http://localhost:53002", admin_app_url="https://admin.example/")
    assert keycloak_admin._admin_base(s2) == "https://admin.example"


def test_invite_driver_uses_driver_client(monkeypatch):
    kc = MagicMock()
    kc.invite_user.return_value = SimpleNamespace(subject="kc1", action="invited", invitation_id="kc1")
    monkeypatch.setattr(invitation_service, "directory_for_kind", lambda settings, kind: kc)
    svc = invitation_service.InvitationService() if hasattr(invitation_service, "InvitationService") else None
    if svc is None:
        cls = next(v for v in vars(invitation_service).values()
                   if isinstance(v, type) and hasattr(v, "invite_driver"))
        svc = cls()
    monkeypatch.setattr(svc, "_record_invitation", lambda *a, **k: SimpleNamespace(id="inv"))
    driver = SimpleNamespace(id="d1", email="X@Y.test", full_name="X", auth_subject=None)
    settings = SimpleNamespace(driver_portal_url="http://localhost:53003")
    try:
        svc.invite_driver(MagicMock(), None, settings, driver)
    except Exception:
        pass  # downstream bookkeeping is not under test; the Keycloak call is
    kwargs = kc.invite_user.call_args.kwargs
    assert kwargs["kind"] == "driver"
    assert kwargs["redirect_url"] == "http://localhost:53003/login"


def _realm():
    spec = importlib.util.spec_from_file_location("build_realm", KC / "build_realm.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.realm()


def test_portal_clients_allow_invite_landing_paths_without_wildcards():
    clients = {c["clientId"]: c for c in _realm()["clients"]}
    drv = clients["pc-driver-portal"]["redirectUris"]
    adm = clients["pc-admin"]["redirectUris"]
    assert "https://driver.porterchain.com/login" in drv
    assert "https://admin.porterchain.com/auth/login" in adm
    for c in clients.values():
        assert not any(u.endswith("*") for u in c.get("redirectUris", [])), c["clientId"]


def test_realm_brute_force_and_reset_policy():
    r = _realm()
    assert r["bruteForceProtected"] is True and r["failureFactor"] <= 10
    assert r["permanentLockout"] is False and r["resetPasswordAllowed"] is True
