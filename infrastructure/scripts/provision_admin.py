#!/usr/bin/env python3
"""Provision a Porterchain admin user (Clerk invite + local admin_users row).

Usage:
  cd apps/api && source .venv/bin/activate
  python ../../infrastructure/scripts/provision_admin.py cadaravichauhan@gmail.com --role super_admin
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

API_ROOT = Path(__file__).resolve().parents[2] / "apps" / "api"
sys.path.insert(0, str(API_ROOT / "src"))

from porterchain_api.admin_models import AdminUser  # noqa: E402


def load_env() -> None:
    env_path = API_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def clerk_headers() -> dict[str, str]:
    secret = os.environ.get("CLERK_SECRET_KEY", "").strip()
    if not secret:
        raise SystemExit("CLERK_SECRET_KEY missing in apps/api/.env")
    return {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}


def find_or_invite_clerk_user(client: httpx.Client, email: str, role: str) -> tuple[str | None, str]:
    headers = clerk_headers()
    lookup = client.get(
        "https://api.clerk.com/v1/users",
        headers=headers,
        params=[("email_address", email), ("limit", "5")],
    )
    lookup.raise_for_status()
    users = lookup.json()
    if users:
        clerk_user_id = users[0]["id"]
        client.patch(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers=headers,
            json={"public_metadata": {"role": role}},
        ).raise_for_status()
        return clerk_user_id, "found"

    invite = client.post(
        "https://api.clerk.com/v1/invitations",
        headers=headers,
        json={
            "email_address": email,
            "public_metadata": {"role": role},
            "redirect_url": os.environ.get("ADMIN_PORTAL_URL", "http://localhost:3002/sign-in"),
        },
    )
    if invite.status_code == 400 and "already" in invite.text.lower():
        return None, "invite_pending"
    invite.raise_for_status()
    return None, "invited"


def upsert_admin(db: Session, *, email: str, role: str, name: str, clerk_user_id: str | None) -> AdminUser:
    clerk_ref = clerk_user_id or f"pending:{email}"
    user = db.query(AdminUser).filter((AdminUser.email == email) | (AdminUser.clerk_user_id == clerk_ref)).first()
    if user:
        user.email = email
        user.name = name
        user.role = role
        user.is_active = True
        if clerk_user_id:
            user.clerk_user_id = clerk_user_id
        elif user.clerk_user_id.startswith("user_"):
            pass
        else:
            user.clerk_user_id = clerk_ref
    else:
        user = AdminUser(
            id=str(uuid.uuid4()),
            clerk_user_id=clerk_ref,
            email=email,
            name=name,
            role=role,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db.add(user)
    db.commit()
    db.refresh(user)
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision Porterchain admin user")
    parser.add_argument("email", type=str)
    parser.add_argument("--role", default="super_admin")
    parser.add_argument("--name", default="Admin User")
    args = parser.parse_args()

    load_env()
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain",
    )
    if database_url.startswith("sqlite"):
        raise SystemExit(
            "SQLite is not supported. Set DATABASE_URL=postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain"
        )

    with httpx.Client(timeout=20) as client:
        clerk_user_id, clerk_action = find_or_invite_clerk_user(client, args.email, args.role)

    engine = create_engine(database_url, pool_pre_ping=True)
    with Session(engine) as db:
        admin = upsert_admin(
            db,
            email=args.email.lower().strip(),
            role=args.role,
            name=args.name,
            clerk_user_id=clerk_user_id,
        )

    print(
        json.dumps(
            {
                "email": admin.email,
                "role": admin.role,
                "admin_id": admin.id,
                "clerk_user_id": admin.clerk_user_id,
                "clerk": clerk_action,
                "next_step": "Check email for Clerk invite, then sign in at http://localhost:3002/sign-in",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
