import pytest

from porterchain_api.platform.future_features import CATALOG, default_future, future_overview, normalize_future


def test_all_off_by_default_with_threshold_and_description():
    assert all(v is False for v in default_future().values())
    assert all(f["threshold"] == 500 and f["description"] and f["group"] for f in CATALOG)


def test_normalize_rejects_unknown():
    assert normalize_future({"ml_eta": 1})["ml_eta"] is True
    with pytest.raises(ValueError):
        normalize_future({"nope": True})


def test_overview(db):
    out = future_overview(db)
    assert out["parcels_per_day"] >= 0 and len(out["features"]) == len(CATALOG)
    assert all(f["ready"] == (out["parcels_per_day"] >= 500) for f in out["features"])
