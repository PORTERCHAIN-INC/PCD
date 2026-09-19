"""HS-16 — FCM token register: store device tokens; Firebase is push-only (not Auth)."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.device_service import (
    DeviceService,
    InvalidFcmToken,
    is_fcm_registration_token,
)
from porterchain_api.notification_engine.models import NotificationDevice


def _token(suffix: str) -> str:
    # Matches DeviceService FCM shape: prefix:APA91…
    return f"430248198034:APA91{suffix}{('x' * 120)}"


def test_hs16_fcm_service_is_push_only_not_auth() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "src/porterchain_api/notification_engine/fcm_service.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    joined = " ".join(imports).lower()
    assert "firebase_admin" in joined or "firebase" in path.read_text(encoding="utf-8").lower()
    for banned in ("clerk", "auth.clerk", "verify_id_token", "sign_in", "password"):
        assert banned not in joined
    text = path.read_text(encoding="utf-8").lower()
    assert "auth" not in text or "firebase_admin.auth" not in text
    assert "verify_id_token" not in text


def test_hs16_register_stores_token_for_admin_driver_customer_merchant(db: Session) -> None:
    svc = DeviceService()
    roles = ("admin", "driver", "customer", "merchant")
    for role in roles:
        uid = f"hs16-{role}-{uuid4().hex[:10]}"
        token = _token(role[:4])
        assert is_fcm_registration_token(token)
        device = svc.register(
            db,
            user_role=role,
            user_id=uid,
            fcm_token=token,
            platform="web" if role != "driver" else "android",
            device_name=f"hs16-{role}",
        )
        db.commit()
        row = db.query(NotificationDevice).filter(NotificationDevice.id == device.id).one()
        assert row.fcm_token == token
        assert row.user_role == role
        assert row.user_id == uid
        assert row.is_active is True


def test_hs16_rejects_expo_and_fake_web_tokens(db: Session) -> None:
    svc = DeviceService()
    for bad in (
        "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
        "web-deadbeef-dead-beef-dead-beefdeadbeef",
        "short",
    ):
        assert is_fcm_registration_token(bad) is False
        with __import__("pytest").raises(InvalidFcmToken):
            svc.register(
                db,
                user_role="admin",
                user_id="hs16-bad",
                fcm_token=bad,
                platform="web",
            )
