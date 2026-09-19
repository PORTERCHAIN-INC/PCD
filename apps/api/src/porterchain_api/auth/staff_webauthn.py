"""Shim — staff WebAuthn credential writes live in admin_engine."""

from porterchain_api.admin_engine.staff_webauthn import (  # noqa: F401
    authentication_options,
    confirm_passkey_for_admin,
    registration_options,
    step_up_options,
    verify_authentication,
    verify_registration,
)
