from porterchain_api.admin_models import AdminAuditLog
from porterchain_api.forensics_models import ForensicAuditEntry
from porterchain_api.platform import forensics
from porterchain_api.platform.forensic_middleware import category_for


def test_mask_drops_secrets_and_masks_pii():
    out = forensics.mask({"password": "x", "Authorization": "Bearer y", "email": "ravi@example.com",
                          "note": "call 416-555-0199", "nested": {"api_key": "k"}})
    assert out["password"] == out["Authorization"] == out["nested"]["api_key"] == "[redacted]"
    assert out["email"] == "r***@example.com" and "0199" not in out["note"] and out["note"].endswith("199")


def test_chain_mirrors_audit_rows_and_detects_tamper(db):

    db.add(AdminAuditLog(actor_user_id="u1", action="settings.config.update", resource_type="settings",
                         resource_id="pricing", payload={"token": "s3cret", "v": 1}))
    db.commit()
    forensics.record(db, "auth", "staff.login.passkey", ip="8.8.8.8")
    forensics.record(db, "auth", "staff.login.passkey", ip="8.8.4.4", outcome="denied")
    db.flush()
    rows = db.query(ForensicAuditEntry).order_by(ForensicAuditEntry.seq).all()
    assert [r.seq for r in rows][-3:] == [rows[-3].seq, rows[-3].seq + 1, rows[-3].seq + 2]
    mirrored = [r for r in rows if r.source.startswith("admin_audit_logs:")][-1]
    assert mirrored.category == "settings" and mirrored.detail["token"] == "[redacted]"
    assert forensics.verify(db)["ok"]
    r = rows[-2]
    row = {c: getattr(r, c) for c in ("seq", "at", "category", "action", "actor", "target_type", "target_id",
                                      "ip", "outcome", "source", "detail")}
    assert forensics.entry_hash(r.prev_hash, row) == r.hash
    assert forensics.entry_hash(r.prev_hash, {**row, "detail": {"forged": True}}) != r.hash
    import pytest
    from sqlalchemy.exc import DBAPIError

    r.detail = {"forged": True}
    with pytest.raises(DBAPIError, match="append-only"):  # Postgres trigger
        db.flush()


def test_checkpoint_signature(db, monkeypatch):
    import base64
    import contextlib
    import io

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    from porterchain_api import forensics_cli
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        forensics_cli.main(["keygen"])
    monkeypatch.setenv("AUDIT_SIGNING_KEY", buf.getvalue().strip())
    forensics.record(db, "deploy", "deploy", detail={"sha": "abc"})
    cp = forensics.checkpoint(db)
    Ed25519PublicKey.from_public_bytes(base64.b64decode(cp["public_key"])).verify(
        base64.b64decode(cp["signature"]), cp["message"].encode())


def test_middleware_categories():
    assert category_for("POST", "/v1/admin/settings/config") == "admin_action"
    assert category_for("GET", "/v1/admin/privacy/access-export") == "data_export"
    assert category_for("POST", "/v1/admin/privacy/erase") == "erasure"
    assert category_for("POST", "/v1/merchant/webhooks") == "webhooks"
    assert category_for("GET", "/v1/admin/orders") is None
