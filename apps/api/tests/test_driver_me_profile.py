"""Driver personal profile: validation, audit (field names only), identity sync."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from porterchain_api.routers.driver import me_profile
from porterchain_driver import personal_profile as pp


def _driver(**kw):
    base = dict(id="d1", documents={}, full_name="Old Name", email="a@x.com", phone="+14165550000",
                performance={"rating_avg": 4.8, "app_settings": {"voice": True}}, clerk_user_id="user_1")
    return SimpleNamespace(**{**base, **kw})


def _patch(body, driver, db=None):
    db = db or MagicMock()
    with patch.object(me_profile, "db_transaction", lambda _db: nullcontext()):
        return me_profile.patch_my_profile(body, SimpleNamespace(driver=driver), db=db), db


GOOD = {
    "full_name": "  Tracy   Lee ",
    "address": {"line1": "1 Yonge St", "city": "Toronto", "province": "on", "postal_code": "m5e1w7"},
    "emergency_contact": {"name": "Sam Lee", "relationship": "Spouse", "phone": "(416) 555-0199"},
    "photo": "data:image/jpeg;base64,/9j/4AAQ",
}


def test_patch_saves_normalised_values_and_keeps_other_performance_data():
    d = _driver()
    out, db = _patch(GOOD, d)
    p = out["profile"]
    assert p["full_name"] == "Tracy Lee"
    assert p["address"]["postal_code"] == "M5E 1W7" and p["address"]["province"] == "ON"
    assert p["emergency_contact"] == {"name": "Sam Lee", "relationship": "spouse", "phone": "+14165550199"}
    assert p["photo_url"].startswith("data:image/jpeg")
    assert sorted(out["changed"]) == ["address", "emergency_contact", "full_name", "photo"]
    assert d.performance["rating_avg"] == 4.8 and d.performance["app_settings"] == {"voice": True}
    audit = db.add.call_args.args[0]
    assert audit.action == "driver.profile.update" and audit.resource_id == "d1"
    assert "Tracy" not in str(audit.payload) and "Yonge" not in str(audit.payload)


def test_noop_patch_writes_no_audit():
    d = _driver()
    _patch(GOOD, d)
    out, db = _patch(GOOD, d)
    assert out["changed"] == [] and not db.add.called


@pytest.mark.parametrize("body,field,code", [
    ({"email": "b@x.com"}, "email", "verify_via_identity"),
    ({"phone": "+14165551111"}, "phone", "verify_via_identity"),
    ({"status": "active"}, "status", "unknown_field"),
    ({"full_name": "A"}, "full_name", "too_short"),
    ({"full_name": "x" * 200}, "full_name", "too_long"),
    ({"address": {**GOOD["address"], "postal_code": "12345"}}, "address.postal_code", "invalid"),
    ({"address": {**GOOD["address"], "province": "ZZ"}}, "address.province", "invalid"),
    ({"address": {"city": "Toronto"}}, "address.line1", "required"),
    ({"emergency_contact": {"name": "S", "phone": "12"}}, "emergency_contact.phone", "invalid"),
    ({"photo": "data:image/svg+xml;base64,AAAA"}, "photo", "invalid"),
    ({"photo": "data:image/png;base64," + "A" * pp.MAX_PHOTO_CHARS}, "photo", "too_large"),
])
def test_patch_rejects_bad_input(body, field, code):
    with pytest.raises(HTTPException) as e:
        _patch(body, _driver())
    assert e.value.status_code == 422 and e.value.detail == {"field": field, "code": code}


def test_clearing_optional_blocks():
    d = _driver()
    _patch(GOOD, d)
    out, _ = _patch({"photo": None, "address": None}, d)
    assert out["profile"]["photo_url"] is None and out["profile"]["address"] is None


def test_get_profile_shape():
    p = me_profile.get_my_profile(SimpleNamespace(driver=_driver()))
    assert p["email"] == "a@x.com" and p["identity_managed_by"] == "clerk"


def _clerk_user(email_status="verified", phone_status="verified"):
    return {
        "primary_email_address_id": "e2",
        "email_addresses": [
            {"id": "e1", "email_address": "a@x.com", "verification": {"status": "verified"}},
            {"id": "e2", "email_address": "New@X.com", "verification": {"status": email_status}},
        ],
        "primary_phone_number_id": "p1",
        "phone_numbers": [{"id": "p1", "phone_number": "+14165552222", "verification": {"status": phone_status}}],
    }


async def _sync(driver, clerk_user):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = driver
    creds = SimpleNamespace(credentials="jwt")
    with patch("porterchain_api.auth.clerk.verify_clerk_token", return_value=SimpleNamespace(clerk_user_id="user_1")), \
         patch("porterchain_api.auth.clerk_registry.fetch_clerk_user", return_value=(clerk_user, "admin")), \
         patch.object(me_profile, "db_transaction", lambda _db: nullcontext()):
        return await me_profile.sync_my_identity(creds, db=db, settings=MagicMock()), db


@pytest.mark.asyncio
async def test_sync_copies_only_verified_values():
    d = _driver()
    out, db = await _sync(d, _clerk_user())
    assert d.email == "new@x.com" and d.phone == "+14165552222"
    assert sorted(out["changed"]) == ["email", "phone"]
    assert db.add.call_args.args[0].action == "driver.identity.sync"


@pytest.mark.asyncio
async def test_sync_ignores_unverified_values():
    d = _driver()
    out, _ = await _sync(d, _clerk_user(email_status="unverified", phone_status="unverified"))
    assert d.email == "a@x.com" and d.phone == "+14165550000" and out["changed"] == []


@pytest.mark.asyncio
async def test_sync_requires_real_token():
    with pytest.raises(HTTPException) as e:
        await me_profile.sync_my_identity(None, db=MagicMock(), settings=MagicMock())
    assert e.value.status_code == 401


def test_emergency_contact_shares_the_support_hub_store():
    d = _driver(documents={"license": {"status": "verified"}})
    _patch({"emergency_contact": GOOD["emergency_contact"]}, d)
    assert d.documents["emergency_contact"]["phone"] == "+14165550199"
    assert d.documents["license"] == {"status": "verified"}
    assert "emergency_contact" not in d.performance.get("personal", {})
