#!/usr/bin/env python3
"""Allow the mobile clients to exchange native Apple/Google id_tokens for Keycloak tokens (L36).

Keycloak legacy (v1) external→internal token exchange: the server must run with
``--features=token-exchange,admin-fine-grained-authz:v1``. For each identity provider this
enables its management permissions and grants the ``token-exchange`` permission to a client
policy covering the mobile clients. Idempotent. Admin credentials come from the environment
(KEYCLOAK_ADMIN_USER / KEYCLOAK_ADMIN_PASSWORD); nothing is printed except names.

  KEYCLOAK_URL=https://auth.porterchain.com python3 enable_token_exchange.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_CLIENTS = ("pc-customer-app", "pc-driver-app")
DEFAULT_IDPS = ("apple", "google")
POLICY_NAME = "pc-mobile-token-exchange"


class Admin:
    def __init__(self, base: str, realm: str, user: str, password: str) -> None:
        self.base = base.rstrip("/")
        self.realm = realm
        body = urllib.parse.urlencode(
            {"grant_type": "password", "client_id": "admin-cli", "username": user, "password": password}
        ).encode()
        req = urllib.request.Request(f"{self.base}/realms/master/protocol/openid-connect/token", data=body)
        with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310 - admin URL from operator
            self.token = json.load(r)["access_token"]

    def call(self, method: str, path: str, payload: object | None = None) -> object:
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.base}/admin/realms/{self.realm}{path}",
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310
            raw = r.read()
        return json.loads(raw) if raw else None

    def client_id(self, client_id: str) -> str:
        found = self.call("GET", f"/clients?clientId={urllib.parse.quote(client_id)}")
        if not found:
            raise SystemExit(f"client not found: {client_id}")
        return found[0]["id"]  # type: ignore[index]


def enable(admin: Admin, idps: list[str], clients: list[str], dry_run: bool = False) -> list[str]:
    done: list[str] = []
    rm = admin.client_id("realm-management")
    client_ids = [admin.client_id(c) for c in clients]
    # 1. Turn on IdP management permissions (this also creates realm-management's authz server).
    perm_ids: dict[str, str] = {}
    for alias in idps:
        try:
            admin.call("GET", f"/identity-provider/instances/{alias}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                done.append(f"skip {alias}: identity provider not configured")
                continue
            raise
        if dry_run:
            done.append(f"would grant token-exchange on {alias} to {', '.join(clients)}")
            continue
        perms = admin.call(
            "PUT", f"/identity-provider/instances/{alias}/management/permissions", {"enabled": True}
        )
        perm_ids[alias] = perms["scopePermissions"]["token-exchange"]  # type: ignore[index]
    if dry_run or not perm_ids:
        return done
    # 2. Client policy covering the mobile apps.
    base = f"/clients/{rm}/authz/resource-server"
    existing = admin.call("GET", f"{base}/policy?name={POLICY_NAME}") or []
    policy = next((p for p in existing if p.get("name") == POLICY_NAME), None)  # type: ignore[union-attr]
    body = {"name": POLICY_NAME, "type": "client", "logic": "POSITIVE", "clients": client_ids}
    if policy:
        admin.call("PUT", f"{base}/policy/client/{policy['id']}", {**body, "id": policy["id"]})
    else:
        policy = admin.call("POST", f"{base}/policy/client", body)
    # 3. Attach the policy to each IdP's token-exchange permission.
    for alias, perm_id in perm_ids.items():
        perm = admin.call("GET", f"{base}/permission/scope/{perm_id}")
        perm.update({"policies": [policy["id"]], "decisionStrategy": "UNANIMOUS"})  # type: ignore[union-attr,index]
        admin.call("PUT", f"{base}/permission/scope/{perm_id}", perm)
        done.append(f"granted token-exchange on {alias} to {', '.join(clients)}")
    return done


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=os.environ.get("KEYCLOAK_URL", "http://127.0.0.1:18180"))
    ap.add_argument("--realm", default=os.environ.get("KEYCLOAK_REALM", "porterchain"))
    ap.add_argument("--idp", action="append", help="identity provider alias (default apple, google)")
    ap.add_argument("--client", action="append", help="client allowed to exchange (default mobile apps)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    user, pw = os.environ.get("KEYCLOAK_ADMIN_USER"), os.environ.get("KEYCLOAK_ADMIN_PASSWORD")
    if not user or not pw:
        print("Set KEYCLOAK_ADMIN_USER and KEYCLOAK_ADMIN_PASSWORD", file=sys.stderr)
        return 2
    admin = Admin(a.url, a.realm, user, pw)
    for line in enable(admin, a.idp or list(DEFAULT_IDPS), a.client or list(DEFAULT_CLIENTS), a.dry_run):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
