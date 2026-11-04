"""Merchant row reads owned by merchant_engine — other engines must not import merchant_models."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant, MerchantUser


def get_merchant(db: Session, merchant_id: str | None) -> Merchant | None:
    if not merchant_id:
        return None
    return db.get(Merchant, merchant_id)


def company_name(db: Session, merchant_id: str | None) -> str | None:
    merchant = get_merchant(db, merchant_id)
    return merchant.company_name if merchant else None


def company_names(db: Session) -> dict[str, str]:
    return {m.id: m.company_name for m in db.query(Merchant).all()}


def credit_limit_cents_sum(db: Session) -> int:
    return int(
        db.query(func.coalesce(func.sum(Merchant.credit_limit_cents), 0))
        .filter(Merchant.credit_limit_cents.isnot(None))
        .scalar()
        or 0
    )


def list_directory_seats(db: Session, *, limit: int = 5000) -> list[tuple[Any, Any]]:
    return (
        db.query(MerchantUser, Merchant)
        .join(Merchant, Merchant.id == MerchantUser.merchant_id)
        .order_by(MerchantUser.created_at.desc())
        .limit(limit)
        .all()
    )


def active_seats_for_idp(
    db: Session, auth_subject: str, *, user_id: str | None = None
) -> list[MerchantUser]:
    rows = db.query(MerchantUser).filter(MerchantUser.auth_subject == auth_subject).all()
    out: list[MerchantUser] = []
    for mu in rows:
        if not mu.is_active:
            continue
        if user_id is not None and mu.porterchain_user_id != user_id:
            mu.porterchain_user_id = user_id
        out.append(mu)
    return out


def seats_for_idp(db: Session, auth_subject: str) -> list[MerchantUser]:
    return db.query(MerchantUser).filter(MerchantUser.auth_subject == auth_subject).order_by(MerchantUser.created_at).all()


def get_merchant_user(db: Session, user_id: str | None) -> MerchantUser | None:
    if not user_id:
        return None
    return db.get(MerchantUser, user_id)


def get_merchant_user_by_email(db: Session, email: str, *, merchant_id: str | None = None) -> MerchantUser | None:
    from porterchain_api.auth.email_identity import normalize_email

    normalized = normalize_email(email) or email
    q = db.query(MerchantUser).filter(MerchantUser.email == normalized)
    if merchant_id:
        q = q.filter(MerchantUser.merchant_id == merchant_id)
    return q.first()


def get_merchant_by_email(db: Session, email: str) -> Merchant | None:
    from porterchain_api.auth.email_identity import normalize_email

    normalized = normalize_email(email) or email
    return (
        db.query(Merchant)
        .filter(Merchant.email == normalized)
        .order_by(Merchant.created_at.desc())
        .first()
    )


def get_merchant_by_idp_org(db: Session, external_org_id: str) -> Merchant | None:
    return db.query(Merchant).filter(Merchant.external_org_id == external_org_id).first()


def rebind_idp_by_email(db: Session, email: str, subject_ref: str) -> bool:
    from porterchain_api.auth.email_identity import emails_match

    row = db.query(MerchantUser).filter(MerchantUser.email == email).first()
    if not row or not emails_match(getattr(row, "email", None), email):
        return False
    if row.auth_subject == subject_ref:
        return False
    taken = db.query(MerchantUser).filter(MerchantUser.auth_subject == subject_ref).first()
    if taken and taken.id != row.id:
        return False
    row.auth_subject = subject_ref
    return True


def list_merchants(db: Session, *, status: str | None = None, limit: int = 50) -> list[Merchant]:
    q = db.query(Merchant)
    if status:
        q = q.filter(Merchant.status == status)
    return q.order_by(Merchant.created_at.desc()).limit(limit).all()


def list_subsidiaries(db: Session, parent_merchant_id: str) -> list[Merchant]:
    return (
        db.query(Merchant)
        .filter(Merchant.parent_merchant_id == parent_merchant_id)
        .order_by(Merchant.company_name.asc())
        .all()
    )


def seats_for_merchant(
    db: Session, merchant_id: str, *, email: str | None = None
) -> list[MerchantUser]:
    q = db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant_id)
    if email:
        q = q.filter(MerchantUser.email == email.lower().strip())
    return q.all()


def get_seat(
    db: Session, user_id: str | None, *, merchant_id: str | None = None
) -> MerchantUser | None:
    user = get_merchant_user(db, user_id)
    if not user:
        return None
    if merchant_id is not None and user.merchant_id != merchant_id:
        return None
    return user


def get_seat_by_idp(db: Session, auth_subject: str | None) -> MerchantUser | None:
    if not auth_subject:
        return None
    return db.query(MerchantUser).filter(MerchantUser.auth_subject == auth_subject).first()


def first_seat(db: Session, merchant_id: str) -> MerchantUser | None:
    return db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant_id).first()


def suspended_merchants(db: Session, statuses: list[str], merchant_id: str | None = None) -> list[Merchant]:
    q = db.query(Merchant).filter(Merchant.status.in_(statuses))
    if merchant_id:
        q = q.filter(Merchant.id == merchant_id)
    return q.all()


def merchants_by_created(db: Session) -> list[Merchant]:
    from sqlalchemy import select

    return list(db.scalars(select(Merchant).order_by(Merchant.created_at)))


def shopify_merchant_ids(db: Session) -> set[str]:
    from sqlalchemy import select

    from porterchain_api.merchant_models import ShopifyShop

    return set(db.scalars(select(ShopifyShop.merchant_id)))
