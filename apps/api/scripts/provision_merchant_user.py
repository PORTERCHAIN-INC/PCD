"""Provision a merchant Clerk user + organization and Porterchain DB records.

Usage:
    cd apps/api && PYTHONPATH=src python scripts/provision_merchant_user.py \\
        --email ravichauhan7434@gmail.com \\
        --password 'YourPassword' \\
        --company "Ravi Chauhan Trading"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from porterchain_api.db import SessionLocal, init_db
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant, MerchantUser

CLERK_API = "https://api.clerk.com/v1"


def _clerk_secret() -> str:
    secret = os.environ.get("CLERK_MERCHANT_SECRET_KEY", "").strip()
    if not secret:
        secret = os.environ.get("CLERK_SECRET_KEY", "").strip()
    if not secret:
        from porterchain_api.config import get_settings

        settings = get_settings()
        secret = settings.clerk_merchant_secret_key or settings.clerk_secret_key or ""
    if not secret:
        raise SystemExit("CLERK_MERCHANT_SECRET_KEY or CLERK_SECRET_KEY is required")
    return secret


def _clerk_headers(secret: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}


def find_user_by_email(client: httpx.Client, email: str) -> dict | None:
    res = client.get(f"{CLERK_API}/users", params=[("email_address", email)])
    res.raise_for_status()
    users = res.json()
    if isinstance(users, list) and users:
        return users[0]
    if isinstance(users, dict) and users.get("data"):
        return users["data"][0] if users["data"] else None
    return None


def create_or_update_user(client: httpx.Client, email: str, password: str) -> dict:
    existing = find_user_by_email(client, email)
    if existing:
        user_id = existing["id"]
        res = client.patch(
            f"{CLERK_API}/users/{user_id}",
            json={"password": password},
        )
        if res.status_code >= 400:
            # User exists — password update may fail if same; continue
            print(f"Note: could not reset password for existing user ({res.status_code})")
        else:
            print(f"Updated password for existing Clerk user {user_id}")
        return existing

    res = client.post(
        f"{CLERK_API}/users",
        json={
            "email_address": [email],
            "password": password,
            "skip_password_checks": False,
            "skip_password_requirement": False,
        },
    )
    if res.status_code >= 400:
        raise SystemExit(f"Clerk user create failed: {res.status_code} {res.text}")
    user = res.json()
    print(f"Created Clerk user {user['id']}")
    return user


def find_org_by_name(client: httpx.Client, name: str) -> dict | None:
    res = client.get(f"{CLERK_API}/organizations", params={"query": name, "limit": 10})
    res.raise_for_status()
    data = res.json()
    rows = data if isinstance(data, list) else data.get("data", [])
    for org in rows:
        if org.get("name") == name:
            return org
    return None


def ensure_organization(client: httpx.Client, *, name: str, user_id: str) -> dict:
    existing = find_org_by_name(client, name)
    if existing:
        org_id = existing["id"]
        print(f"Using existing Clerk org {org_id}")
    else:
        res = client.post(
            f"{CLERK_API}/organizations",
            json={"name": name, "created_by": user_id},
        )
        if res.status_code >= 400:
            raise SystemExit(f"Clerk org create failed: {res.status_code} {res.text}")
        existing = res.json()
        org_id = existing["id"]
        print(f"Created Clerk org {org_id}")

    mem_res = client.get(f"{CLERK_API}/organizations/{org_id}/memberships", params={"limit": 100})
    mem_res.raise_for_status()
    mem_data = mem_res.json()
    memberships = mem_data if isinstance(mem_data, list) else mem_data.get("data", [])
    member_user_ids = {
        m.get("public_user_data", {}).get("user_id") or m.get("user_id") for m in memberships
    }
    if user_id not in member_user_ids:
        add = client.post(
            f"{CLERK_API}/organizations/{org_id}/memberships",
            json={"user_id": user_id, "role": "org:admin"},
        )
        if add.status_code >= 400:
            raise SystemExit(f"Clerk membership failed: {add.status_code} {add.text}")
        print(f"Added user to org as admin")
    return existing


def ensure_db_merchant(
    db: Session,
    *,
    email: str,
    company_name: str,
    clerk_org_id: str,
    clerk_user_id: str,
) -> tuple[Merchant, MerchantUser]:
    merchant = db.query(Merchant).filter(Merchant.clerk_org_id == clerk_org_id).first()
    if not merchant:
        by_email = db.query(Merchant).filter(Merchant.email == email).first()
        merchant = by_email

    if not merchant:
        merchant = Merchant(
            clerk_org_id=clerk_org_id,
            status=MerchantStatus.ACTIVE.value,
            company_name=company_name,
            legal_name=company_name,
            email=email,
            payment_terms="NET_30",
            activated_at=datetime.now(UTC),
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
        print(f"Created merchant {merchant.id}")
    else:
        merchant.clerk_org_id = clerk_org_id
        merchant.status = MerchantStatus.ACTIVE.value
        merchant.company_name = company_name
        merchant.email = email
        if not merchant.activated_at:
            merchant.activated_at = datetime.now(UTC)
        db.commit()
        db.refresh(merchant)
        print(f"Updated merchant {merchant.id}")

    user = db.query(MerchantUser).filter(MerchantUser.clerk_user_id == clerk_user_id).first()
    if not user:
        user = MerchantUser(
            merchant_id=merchant.id,
            clerk_user_id=clerk_user_id,
            email=email,
            role="merchant_owner",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created merchant_user {user.id}")
    else:
        user.merchant_id = merchant.id
        user.email = email
        user.role = "merchant_owner"
        user.is_active = True
        db.commit()
        db.refresh(user)
        print(f"Updated merchant_user {user.id}")

    return merchant, user


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision merchant Clerk + DB account")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--company", default="Ravi Chauhan Trading")
    args = parser.parse_args()

    secret = _clerk_secret()
    init_db()
    db = SessionLocal()

    try:
        with httpx.Client(headers=_clerk_headers(secret), timeout=30.0) as client:
            clerk_user = create_or_update_user(client, args.email, args.password)
            clerk_user_id = clerk_user["id"]
            org = ensure_organization(
                client, name=args.company, user_id=clerk_user_id
            )
            clerk_org_id = org["id"]

        merchant, muser = ensure_db_merchant(
            db,
            email=args.email,
            company_name=args.company,
            clerk_org_id=clerk_org_id,
            clerk_user_id=clerk_user_id,
        )

        print()
        print("=== Merchant account ready ===")
        print(f"Email:           {args.email}")
        print(f"Clerk user ID:   {clerk_user_id}")
        print(f"Clerk org ID:    {clerk_org_id}")
        print(f"Merchant ID:     {merchant.id}")
        print(f"Merchant user:   {muser.id}")
        print()
        print("Sign in at http://localhost:3001/sign-in with your email and password.")
        print("Select organization:", args.company)
    finally:
        db.close()


if __name__ == "__main__":
    main()
