#!/usr/bin/env python3
"""Create/update App Store / Play reviewer accounts in the Keycloak `porterchain` realm.

Password-only, no required actions, no OTP (reviewers are never in mfa_required roles).
Passwords come ONLY from env (load via scripts/secrets/sops-load.sh); never printed.

Env: KEYCLOAK_URL, KEYCLOAK_REALM (default porterchain), KEYCLOAK_ADMIN_USER, KEYCLOAK_ADMIN_PASSWORD,
     REVIEWER_CUSTOMER_EMAIL, REVIEWER_CUSTOMER_PASSWORD, REVIEWER_DRIVER_EMAIL, REVIEWER_DRIVER_PASSWORD
     --dry-run prints the plan without calling Keycloak.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ACCOUNTS = [
    ("REVIEWER_CUSTOMER_EMAIL", "REVIEWER_CUSTOMER_PASSWORD", "reviewers", ["customer", "reviewer"]),
    ("REVIEWER_DRIVER_EMAIL", "REVIEWER_DRIVER_PASSWORD", "reviewers", ["driver", "reviewer"]),
]


def _req(method: str, url: str, token: str | None = None, body: dict | None = None, form: dict | None = None):
    data = None
    headers = {}
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def plan(env: dict) -> list[dict]:
    out = []
    for email_key, pw_key, group, roles in ACCOUNTS:
        email = (env.get(email_key) or "").strip().lower()
        if not email:
            continue
        if not env.get(pw_key):
            raise SystemExit(f"{pw_key} not set (load it from SOPS)")
        out.append({"email": email, "password_env": pw_key, "group": group, "roles": roles})
    if not out:
        raise SystemExit("no reviewer emails set")
    return out


def apply(env: dict, items: list[dict]) -> None:
    base = env["KEYCLOAK_URL"].rstrip("/")
    realm = env.get("KEYCLOAK_REALM", "porterchain")
    tok = _req("POST", f"{base}/realms/master/protocol/openid-connect/token", form={
        "grant_type": "password", "client_id": "admin-cli",
        "username": env["KEYCLOAK_ADMIN_USER"], "password": env["KEYCLOAK_ADMIN_PASSWORD"],
    })["access_token"]
    admin = f"{base}/admin/realms/{realm}"
    groups = {g["name"]: g["id"] for g in _req("GET", f"{admin}/groups?briefRepresentation=true", tok)}
    for it in items:
        q = urllib.parse.quote(it["email"])
        found = _req("GET", f"{admin}/users?email={q}&exact=true", tok)
        user = {"username": it["email"], "email": it["email"], "enabled": True, "emailVerified": True,
                "requiredActions": [], "attributes": {"pc_reviewer": ["true"]}}
        if found:
            uid = found[0]["id"]
            _req("PUT", f"{admin}/users/{uid}", tok, body=user)
        else:
            _req("POST", f"{admin}/users", tok, body=user)
            uid = _req("GET", f"{admin}/users?email={q}&exact=true", tok)[0]["id"]
        try:
            _req("PUT", f"{admin}/users/{uid}/reset-password", tok,
                 body={"type": "password", "value": env[it["password_env"]], "temporary": False})
        except urllib.error.HTTPError as exc:
            # Re-run with the same password: realm passwordHistory refuses it — already set.
            if exc.code != 400 or b"History" not in exc.read():
                raise
        if it["group"] in groups:
            _req("PUT", f"{admin}/users/{uid}/groups/{groups[it['group']]}", tok)
        roles = [_req("GET", f"{admin}/roles/{r}", tok) for r in it["roles"]]
        _req("POST", f"{admin}/users/{uid}/role-mappings/realm", tok, body=roles)
        print(f"reviewer ready: {it['email']} roles={','.join(it['roles'])}")


def main() -> int:
    items = plan(dict(os.environ))
    if "--dry-run" in sys.argv:
        for it in items:
            print(f"[dry-run] would upsert {it['email']} roles={','.join(it['roles'])} (password from {it['password_env']})")
        return 0
    apply(dict(os.environ), items)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
