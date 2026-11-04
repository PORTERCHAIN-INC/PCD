from types import SimpleNamespace
from porterchain_api.merchant_engine import profile_service as ps


class _DB:
    def commit(self):
        pass


def test_set_and_read_display_name(monkeypatch):
    monkeypatch.setattr("sqlalchemy.orm.attributes.flag_modified", lambda *a: None)
    m = SimpleNamespace(profile={"settings": {"billing_contacts": []}})
    assert ps.set_user_display_name(_DB(), m, "u1", "  Jane   Doe ") == "Jane Doe"
    assert ps.user_display_name(m, "u1") == "Jane Doe"
    assert ps.user_display_name(m, "u2") is None
    assert m.profile["settings"]["billing_contacts"] == []
    assert ps.set_user_display_name(_DB(), m, "u1", "") is None
    assert ps.user_display_name(m, "u1") is None
