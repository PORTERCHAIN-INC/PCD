#!/usr/bin/env python3
"""One-off: Clerk user export (CSV) → Keycloak partial-import JSON + subject remap plan. DRY RUN ONLY.

The only place Clerk is still referenced in code (history/migration). It never calls Clerk,
Keycloak or the database. Outputs (pass --out-dir):
  keycloak-users.json   realm partial import ({"users": [...]}) — ids are uuid5(clerk id), so the
                        remap is deterministic and re-runnable
  subject-remap.csv     legacy_subject,keycloak_sub,email — feed to a reviewed DB migration later
Passwords: Clerk exports bcrypt digests; stock Keycloak cannot verify bcrypt, so imported users get
no password credential and sign in with Google/Apple or "forgot password". Digests are never written.

Usage: python3 migrate_clerk_users.py --export clerk_users.csv --out-dir /tmp/kc-migration [--dry-run]
(--dry-run is the default and the only supported mode.)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from pathlib import Path

NAMESPACE = uuid.UUID("6d1f5f0e-5c1a-4c8e-9a43-7f1a2b0c9e11")  # fixed: PorterChain legacy subjects
ROLE_BY_META = {"driver": ["driver"], "merchant": ["merchant_owner"], "customer": ["customer"]}


def keycloak_id(legacy_subject: str) -> str:
    return str(uuid.uuid5(NAMESPACE, legacy_subject))


def convert(rows: list[dict]) -> tuple[list[dict], list[tuple[str, str, str]], list[str]]:
    users, remap, skipped, seen = [], [], [], set()
    for row in rows:
        sub = (row.get("id") or "").strip()
        email = (row.get("primary_email_address") or row.get("email") or "").strip().lower()
        if not sub or not email:
            skipped.append(f"{sub or '?'}: missing id/email")
            continue
        if email in seen:
            skipped.append(f"{sub}: duplicate email")
            continue
        seen.add(email)
        verified = {e.strip().lower() for e in (row.get("verified_email_addresses") or "").split(",") if e.strip()}
        persona = (row.get("public_metadata_role") or row.get("role") or "customer").strip().lower()
        kid = keycloak_id(sub)
        user = {
            "id": kid, "username": email, "email": email, "enabled": True,
            "emailVerified": email in verified or not verified,
            "firstName": (row.get("first_name") or "").strip() or None,
            "lastName": (row.get("last_name") or "").strip() or None,
            "attributes": {"legacy_subject": [sub]},
            "realmRoles": ROLE_BY_META.get(persona, ["customer"]),
            "requiredActions": [],
        }
        phone = (row.get("primary_phone_number") or "").strip()
        if phone:
            user["attributes"]["phone_number"] = [phone]
        users.append({k: v for k, v in user.items() if v is not None})
        remap.append((sub, kid, email))
    return users, remap, skipped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true", help="not supported: refuses")
    a = ap.parse_args(argv)
    if a.apply:
        print("refusing: this tool is dry-run only; import via a reviewed Keycloak partial import", file=sys.stderr)
        return 2
    with open(a.export, newline="") as fh:
        rows = list(csv.DictReader(fh))
    users, remap, skipped = convert(rows)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "keycloak-users.json").write_text(json.dumps({"ifResourceExists": "SKIP", "users": users}, indent=2))
    with open(out / "subject-remap.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["legacy_subject", "keycloak_sub", "email"])
        w.writerows(remap)
    print(f"[dry-run] rows={len(rows)} users={len(users)} skipped={len(skipped)} out={out}")
    for s in skipped:
        print(f"[dry-run] skip {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
