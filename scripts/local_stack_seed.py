#!/usr/bin/env python3
"""Helpers for scripts/local-stack.sh (isolated local stack only). Never prints passwords.

  db        -> ensure the staff admin row (admin@porterchain.com, super_admin) exists in the LOCAL stack DB
  keycloak  -> upsert admin/merchant/driver/customer test users in the LOCAL Keycloak (passwords from env)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def _guard_local(url: str, allowed: set[int]) -> None:
    u = urlsplit(url)
    if u.hostname not in {"127.0.0.1", "localhost"} or u.port not in allowed:
        raise SystemExit(f"refusing: {u.hostname}:{u.port} is not the local stack")


def db() -> None:
    _guard_local(os.environ["DATABASE_URL"].replace("postgresql+psycopg", "postgresql"), {56432})
    import porterchain_api.main  # noqa: F401  (registers every mapper)
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.db import SessionLocal, init_db

    init_db()
    s = SessionLocal()
    try:
        email = os.environ["ADMIN_EMAIL"].lower()
        u = s.query(AdminUser).filter(AdminUser.email == email).first()
        if not u:
            s.add(AdminUser(auth_subject="local_stack_admin", email=email, name="Local Admin", role="super_admin", is_active=True))
            s.commit()
        print("db: staff admin ready")
        from porterchain_api.platform.tax_registration import collects_tax, record_registration

        if not collects_tax(s):  # Porterchain Inc. is a GST/HST registrant (effective 2026-09-28)
            record_registration(s, gst_hst_number="743402620RT0001", legal_name="Porterchain Inc.",
                                effective_from="2026-09-28", actor_id=None, note="local stack seed")
            s.commit()
        print("db: GST/HST registration on (Porterchain Inc. 743402620 RT0001)")
    finally:
        s.close()


def keycloak() -> None:
    _guard_local(os.environ["KEYCLOAK_URL"], {18280})
    sys.path.insert(0, str(ROOT / "infrastructure" / "keycloak"))
    import seed_reviewers as sr

    items = [
        {"email": os.environ["ADMIN_EMAIL"], "password_env": "ADMIN_PASSWORD", "group": "staff", "roles": ["super_admin"]},
        {"email": os.environ["MERCHANT_EMAIL"], "password_env": "MERCHANT_PASSWORD", "group": "merchants", "roles": ["merchant_owner"]},
        {"email": os.environ["DRIVER_EMAIL"], "password_env": "DRIVER_PASSWORD", "group": "drivers", "roles": ["driver"]},
        {"email": os.environ["CUSTOMER_EMAIL"], "password_env": "CUSTOMER_PASSWORD", "group": "customers", "roles": ["customer"]},
    ]
    sr.apply(dict(os.environ), items)


if __name__ == "__main__":
    {"db": db, "keycloak": keycloak}[sys.argv[1]]()
