"""Doc 60 R7: route notices also go out as Firebase push (fake sender; no real credentials)."""
from porterchain_api.notification_engine.models import NotificationDevice
from porterchain_api.notification_engine.notice_push import push_notice


class Fake:
    def __init__(self, bad=()):
        self.calls, self.bad = [], set(bad)

    def send(self, token, **kw):
        self.calls.append((token, kw))
        return (False, "token_unregistered", True) if token in self.bad else (True, None, False)


def _dev(db, uid, tok, lang="en-CA", active=True):
    d = NotificationDevice(user_role="driver", user_id=uid, platform="android", fcm_token=tok, language=lang,
                           is_active=active)
    db.add(d)
    db.flush()
    return d


def test_push_to_active_devices_fr_copy_and_invalid_token(db):
    _dev(db, "drv-p1", "tok-en")
    _dev(db, "drv-p1", "tok-fr", lang="fr-CA")
    dead = _dev(db, "drv-p1", "tok-dead")
    _dev(db, "drv-p1", "tok-off", active=False)
    _dev(db, "drv-other", "tok-x")
    f = Fake(bad={"tok-dead"})
    assert push_notice(db, "drv-p1", "leg_cancelled", "route-1", sender=f) == 2
    toks = {t: kw for t, kw in f.calls}
    assert set(toks) == {"tok-en", "tok-fr", "tok-dead"}
    assert toks["tok-fr"]["title"] == "Trajet annulé" and toks["tok-en"]["priority"] == "high"
    assert toks["tok-en"]["data"] == {"kind": "leg_cancelled", "route_id": "route-1"}
    assert dead.is_active is False and dead.invalidated_at is not None


def test_no_driver_and_sender_errors_never_raise(db):
    assert push_notice(db, None, "leg_unlocked", "r") == 0
    _dev(db, "drv-p2", "tok")

    class Boom:
        def send(self, *a, **k):
            raise RuntimeError("fcm down")
    assert push_notice(db, "drv-p2", "leg_unlocked", "r", sender=Boom()) == 0


def test_default_sender_is_safe_without_credentials(db):
    _dev(db, "drv-p3", "tok")
    assert push_notice(db, "drv-p3", "leg_unlocked", "r") == 1  # log-only / dry-run in tests
