from types import SimpleNamespace

from porterchain_api.platform import gps_policy, monitoring_policy as mp


def test_ack_is_versioned_and_timestamped():
    d = SimpleNamespace(documents={})
    assert mp.driver_view(d)["acknowledged"] is False
    rec = mp.acknowledge(d, source="portal")
    assert rec["version"] == mp.POLICY_VERSION and rec["at"]
    view = mp.driver_view(d)
    assert view["acknowledged"] and view["sections"]
    d.documents["monitoring_policy_ack"]["version"] = "old"
    assert mp.driver_view(d)["acknowledged"] is False  # new version -> ask again


def test_consent_required_by_default_and_links_policy():
    gps_policy.set_policy_cache(None)
    assert gps_policy.default_driver_gps()["require_consent"] is True
    assert gps_policy.normalize_driver_gps({})["require_consent"] is True
    gps_policy.set_policy_cache(gps_policy.default_driver_gps())
    st = gps_policy.driver_gps_status("d1", None, SimpleNamespace(documents={}))
    assert st["consent_required"] and not st["enabled"] and st["policy_url"] == "/monitoring-policy"
    gps_policy.set_policy_cache(None)
