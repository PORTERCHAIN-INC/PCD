"""L36: realm-as-code invariants, reviewer seed plan, Keycloak→Keycloak dry-run migration."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest

KC = Path(__file__).resolve().parents[3] / "infrastructure" / "keycloak"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, KC / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_committed_realm_matches_generator():
    built = _load("build_realm").realm()
    assert json.loads((KC / "realm-porterchain.json").read_text()) == built


def test_realm_policy():
    r = json.loads((KC / "realm-porterchain.json").read_text())
    assert r["realm"] == "porterchain" and r["bruteForceProtected"] is True
    # L82: the API only trusts verified emails, so self sign-up must verify once (not a per-login code).
    assert r["verifyEmail"] is True
    assert r["attributes"]["actionTokenGeneratedByUserLifespan.verify-email"] == "43200"
    clients = {c["clientId"]: c for c in r["clients"]}
    for cid in ("pc-website", "pc-merchant-portal", "pc-admin", "pc-customer-app", "pc-driver-app"):
        c = clients[cid]
        assert c["publicClient"] and c["attributes"]["pkce.code.challenge.method"] == "S256"
        assert not c["directAccessGrantsEnabled"] and not c["implicitFlowEnabled"]
    assert clients["pc-api"]["bearerOnly"] is True
    assert clients["pc-customer-app"]["redirectUris"] == ["porterchain-customer://auth"]
    assert clients["pc-driver-app"]["redirectUris"] == ["porterchain-driver://auth"]
    roles = {x["name"]: x for x in r["roles"]["realm"]}
    for staff in ("super_admin", "admin"):
        assert roles[staff]["composites"]["realm"] == ["mfa_required"]
    assert "composites" not in roles["reviewer"] and "composites" not in roles["dispatcher"]
    flows = {f["alias"]: f for f in r["authenticationFlows"]}
    otp = flows["pc-staff-otp"]["authenticationExecutions"]
    assert otp[0]["authenticator"] == "conditional-user-role" and otp[1]["authenticator"] == "auth-otp-form"
    assert not any(e.get("authenticator") == "auth-email-otp-form" for f in flows.values() for e in f["authenticationExecutions"])


def test_realm_has_no_secrets():
    text = (KC / "realm-porterchain.json").read_text()
    idp = {i["alias"]: i for i in json.loads(text)["identityProviders"]}
    assert idp["google"]["config"]["clientSecret"] == "${GOOGLE_CLIENT_SECRET}"
    assert idp["apple"]["config"]["p8Content"] == "${APPLE_P8_KEY}"
    assert "BEGIN PRIVATE KEY" not in text and "GOCSPX" not in text


def test_reviewer_seed_plan_requires_env_passwords():
    seed = _load("seed_reviewers")
    with pytest.raises(SystemExit):
        seed.plan({"REVIEWER_CUSTOMER_EMAIL": "r@x.test"})
    items = seed.plan({"REVIEWER_CUSTOMER_EMAIL": "R@X.test", "REVIEWER_CUSTOMER_PASSWORD": "p" * 12,
                       "REVIEWER_DRIVER_EMAIL": "d@x.test", "REVIEWER_DRIVER_PASSWORD": "q" * 12})
    assert [i["email"] for i in items] == ["r@x.test", "d@x.test"]
    assert all("password" not in i for i in items)
    assert items[1]["roles"] == ["driver", "reviewer"]


def test_migration_dry_run(tmp_path):
    mig = _load("migrate_clerk_users")
    export = tmp_path / "users.csv"
    with open(export, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "first_name", "primary_email_address", "verified_email_addresses",
                                           "password_digest", "public_metadata_role"])
        w.writeheader()
        w.writerow({"id": "user_a", "first_name": "A", "primary_email_address": "A@x.test",
                    "verified_email_addresses": "a@x.test", "password_digest": "$2a$10$secret", "public_metadata_role": "driver"})
        w.writerow({"id": "user_b", "primary_email_address": "a@x.test"})
        w.writerow({"id": "", "primary_email_address": "c@x.test"})
    assert mig.main(["--export", str(export), "--out-dir", str(tmp_path / "out")]) == 0
    data = json.loads((tmp_path / "out" / "keycloak-users.json").read_text())
    assert len(data["users"]) == 1
    u = data["users"][0]
    assert u["id"] == mig.keycloak_id("user_a") and u["realmRoles"] == ["driver"]
    assert "$2a$" not in (tmp_path / "out" / "keycloak-users.json").read_text()
    assert mig.main(["--export", str(export), "--out-dir", str(tmp_path / "o2"), "--apply"]) == 2
