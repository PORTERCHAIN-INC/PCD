"""Email identity match — Keycloak verified email must equal system profile email."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.email_identity import (
    IDP_EMAIL_REQUIRED,
    IDP_EMAIL_UNVERIFIED,
    EMAIL_IDENTITY_MISMATCH,
    delete_email_mismatched_bindings,
    email_from_jwt_payload,
    emails_match,
    enrich_claims_with_verified_email,
    normalize_email,
    require_system_email_matches_idp,
    resolve_verified_idp_email,
    verified_primary_email_from_idp_user,
)
from porterchain_api.auth.persona_principal import resolve_persona_principal


def test_normalize_and_match() -> None:
    assert normalize_email("  Admin@PorterChain.com ") == "admin@porterchain.com"
    assert emails_match("Admin@PorterChain.com", "admin@porterchain.com")
    assert not emails_match("admin@porterchain.com", "ravichauhan7434@gmail.com")


def test_require_system_email_matches_idp() -> None:
    require_system_email_matches_idp("a@x.com", "A@x.com")
    with pytest.raises(PermissionError, match=EMAIL_IDENTITY_MISMATCH):
        require_system_email_matches_idp("admin@porterchain.com", "ravichauhan7434@gmail.com")
    with pytest.raises(PermissionError, match=IDP_EMAIL_REQUIRED):
        require_system_email_matches_idp("admin@porterchain.com", None)


def test_email_from_jwt_payload_variants() -> None:
    assert email_from_jwt_payload({"email": "A@X.com"}) == "a@x.com"
    assert email_from_jwt_payload({"primary_email_address": "b@x.com"}) == "b@x.com"
    assert email_from_jwt_payload({"sub": "user_1"}) is None


def test_verified_primary_email_from_idp_user() -> None:
    verified = {
        "primary_email_address_id": "em_1",
        "email_addresses": [
            {
                "id": "em_1",
                "email_address": "owner@pareva.com",
                "verification": {"status": "verified"},
            }
        ],
    }
    assert verified_primary_email_from_idp_user(verified) == ("owner@pareva.com", None)

    unverified = {
        "primary_email_address_id": "em_1",
        "email_addresses": [
            {
                "id": "em_1",
                "email_address": "owner@pareva.com",
                "verification": {"status": "unverified"},
            }
        ],
    }
    assert verified_primary_email_from_idp_user(unverified) == (None, IDP_EMAIL_UNVERIFIED)


def test_resolve_verified_idp_email_jwt_wins() -> None:
    settings = MagicMock()
    assert (
        resolve_verified_idp_email(
            jwt_email="Pareva@Gmail.com",
            auth_subject="user_x",
            settings=settings,
        )
        == "pareva@gmail.com"
    )


def test_enrich_claims_fetches_backend_when_jwt_omits_email() -> None:
    settings = MagicMock()
    claims = IdentityClaims(auth_subject="user_x", email=None)
    with patch(
        "porterchain_api.auth.email_identity.resolve_verified_idp_email",
        return_value="parevalogistics@gmail.com",
    ):
        enriched = enrich_claims_with_verified_email(claims, settings)
    assert enriched.email == "parevalogistics@gmail.com"


def test_delete_mismatched_admin_binding() -> None:
    from porterchain_api.auth.persona_bundle import PersonaBundle

    db = MagicMock()
    admin = AdminUser(
        id="a1",
        auth_subject="user_gmail",
        email="admin@porterchain.com",
        name="Mismatch",
        role="super_admin",
    )
    deleted: list[object] = []
    db.delete.side_effect = deleted.append
    bundle = PersonaBundle(
        auth_subject="user_gmail",
        admin=admin,
        merchant_users=[],
        driver=None,
        customer=None,
    )
    with patch(
        "porterchain_api.auth.persona_bundle.load_persona_bundle",
        return_value=bundle,
    ), patch(
        "porterchain_api.auth.persona_bundle.invalidate_persona_bundle",
    ), patch(
        "porterchain_api.auth.email_identity._strip_registry_if_no_matching_persona",
    ):
        n = delete_email_mismatched_bindings(
            db, auth_subject="user_gmail", identity_email="ravichauhan7434@gmail.com"
        )
    assert n == 1
    assert admin in deleted


def test_persona_principal_skips_email_mismatched_admin() -> None:
    db = MagicMock()
    admin = AdminUser(
        id="a1",
        auth_subject="user_gmail",
        email="admin@porterchain.com",
        name="Mismatch",
        role="super_admin",
        is_active=True,
    )

    def query(model):
        q = MagicMock()
        if model is AdminUser:
            q.filter.return_value.first.return_value = admin
        else:
            q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = query
    claims = IdentityClaims(auth_subject="user_gmail", email="ravichauhan7434@gmail.com")
    assert resolve_persona_principal(db, claims) is None


def test_persona_principal_skips_missing_idp_email() -> None:
    from porterchain_api.auth.persona_bundle import PersonaBundle

    db = MagicMock()
    admin = AdminUser(
        id="a1",
        auth_subject="user_gmail",
        email="admin@porterchain.com",
        name="Staff",
        role="super_admin",
        is_active=True,
    )
    bundle = PersonaBundle(
        auth_subject="user_gmail",
        admin=admin,
        merchant_users=[],
        driver=None,
        customer=None,
    )
    with patch("porterchain_api.auth.persona_principal.load_persona_bundle", return_value=bundle):
        claims = IdentityClaims(auth_subject="user_gmail", email=None)
        assert resolve_persona_principal(db, claims) is None
