"""Staff security 10/10 — recovery, new-device, event feed."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from porterchain_api.auth.staff_security_events import (
    device_fingerprint,
    is_new_device,
    list_security_events,
    record_security_event,
)


def test_device_fingerprint() -> None:
    assert device_fingerprint({"client_ip": "1.2.3.4", "device_label": "Chrome"}) == "1.2.3.4|Chrome"
    assert device_fingerprint({}) == ""


def test_is_new_device_false_when_no_sessions() -> None:
    with patch(
        "porterchain_api.auth.staff_session.list_sessions_for_user",
        return_value=[],
    ):
        assert (
            is_new_device("admin-1", {"client_ip": "1.1.1.1", "device_label": "Chrome"})
            is False
        )


def test_is_new_device_true_when_fingerprint_unseen() -> None:
    with patch(
        "porterchain_api.auth.staff_session.list_sessions_for_user",
        return_value=[
            {"client_ip": "9.9.9.9", "device_label": "Safari"},
        ],
    ):
        assert (
            is_new_device("admin-1", {"client_ip": "1.1.1.1", "device_label": "Chrome"})
            is True
        )


def test_is_new_device_false_when_known() -> None:
    with patch(
        "porterchain_api.auth.staff_session.list_sessions_for_user",
        return_value=[
            {"client_ip": "1.1.1.1", "device_label": "Chrome"},
        ],
    ):
        assert (
            is_new_device("admin-1", {"client_ip": "1.1.1.1", "device_label": "Chrome"})
            is False
        )


def test_security_event_ring_buffer() -> None:
    store: dict[str, list[str]] = {}

    class FakeRedis:
        def lpush(self, key, value):
            store.setdefault(key, []).insert(0, value)

        def ltrim(self, key, start, end):
            store[key] = store.get(key, [])[start : end + 1]

        def expire(self, key, ttl):
            return True

        def lrange(self, key, start, end):
            return store.get(key, [])[start : end + 1]

        def ping(self):
            return True

    with patch("porterchain_api.auth.staff_security_events._client", return_value=FakeRedis()):
        record_security_event("u1", kind="login", detail={"client_ip": "1.1.1.1"})
        record_security_event("u1", kind="new_device", detail={"device_label": "Chrome"})
        events = list_security_events("u1", limit=10)
        assert len(events) == 2
        assert events[0]["kind"] == "new_device"
        assert events[1]["kind"] == "login"


def test_recover_device_wipes_passkeys_and_reissues(db, settings) -> None:
    import uuid

    from porterchain_api.admin_engine.rbac import AdminContext
    from porterchain_api.admin_engine.staff_idp_service import StaffIdpService
    from porterchain_api.admin_models import AdminUser, StaffWebAuthnCredential
    from porterchain_api.auth.staff_session import create_session

    suffix = uuid.uuid4().hex[:8]
    user = AdminUser(
        clerk_user_id=f"staff:recover-{suffix}",
        email=f"recover-{suffix}@porterchain.com",
        name="Recover",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(
        StaffWebAuthnCredential(
            admin_user_id=user.id,
            credential_id=f"cred-{suffix}",
            public_key="pk",
            sign_count=0,
            device_label="Lost laptop",
        )
    )
    db.commit()
    db.refresh(user)

    store: dict[str, str] = {}
    sets: dict[str, set[str]] = {}

    class FakeRedis:
        def setex(self, key, ttl, value):
            store[key] = value

        def get(self, key):
            return store.get(key)

        def delete(self, key):
            return 1 if store.pop(key, None) is not None else 0

        def sadd(self, key, member):
            sets.setdefault(key, set()).add(member)

        def expire(self, key, ttl):
            return True

        def srem(self, key, member):
            if key in sets:
                sets[key].discard(member)

        def smembers(self, key):
            return set(sets.get(key, set()))

        def ping(self):
            return True

        def lpush(self, *a, **k):
            return 1

        def ltrim(self, *a, **k):
            return True

    fake = FakeRedis()
    with (
        patch("porterchain_api.auth.staff_session._client", return_value=fake),
        patch("porterchain_api.auth.staff_security_events._client", return_value=fake),
        patch(
            "porterchain_api.admin_engine.staff_idp_service.send_staff_activate_email",
            return_value=True,
        ),
        patch(
            "porterchain_api.admin_engine.staff_idp_service.ensure_staff_identity",
            return_value="pc-user",
        ),
    ):
        create_session(admin_user_id=user.id, email=user.email, role=user.role)
        actor = AdminUser(
            clerk_user_id=f"staff:actor-{suffix}",
            email=f"super-{suffix}@porterchain.com",
            name="Super",
            role="super_admin",
            is_active=True,
        )
        db.add(actor)
        db.commit()
        db.refresh(actor)
        ctx = MagicMock(spec=AdminContext)
        ctx.user = actor
        out = StaffIdpService().recover_device(
            db, ctx, settings, user.id, reason="lost_laptop"
        )
    assert out["email"] == user.email
    assert out["passkeys_removed"] == 1
    assert out["sessions_revoked"] == 1
    assert out.get("enrollment_token") or out.get("email_sent")
    left = (
        db.query(StaffWebAuthnCredential)
        .filter(StaffWebAuthnCredential.admin_user_id == user.id)
        .count()
    )
    assert left == 0
