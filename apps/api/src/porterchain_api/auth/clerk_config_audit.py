"""Clerk / Doppler config audit — names + validity only (never secret values).

Phase 6: startup fail-fast helpers + CLI-friendly report shape.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal
from urllib.parse import urlparse

from porterchain_shared.redis_health import is_local_env

from porterchain_api.auth.clerk_registry import (
    ALL_CLERK_APP_KINDS,
    clerk_app_configs,
    clerk_configuration_mode,
    is_divergent_enterprise_clerk,
)
from porterchain_api.config import Settings

AuditStatus = Literal[
    "ok",
    "missing",
    "empty",
    "malformed_prefix",
    "test_key",
    "live_key",
    "env_mismatch",
    "warn",
    "info",
]


@dataclass(frozen=True)
class ConfigAuditFinding:
    """One config check result. ``detail`` must never include secret material."""

    name: str
    status: AuditStatus
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _classify_key_prefix(value: str, *, expect: Literal["pk", "sk"]) -> AuditStatus:
    v = (value or "").strip()
    if not v:
        return "empty"
    if expect == "pk":
        if v.startswith("pk_test_"):
            return "test_key"
        if v.startswith("pk_live_"):
            return "live_key"
        if v.startswith("pk_"):
            return "ok"
        return "malformed_prefix"
    if v.startswith("sk_test_"):
        return "test_key"
    if v.startswith("sk_live_"):
        return "live_key"
    if v.startswith("sk_"):
        return "ok"
    return "malformed_prefix"


def issuer_from_jwks_url(jwks_url: str) -> str:
    """Derive Clerk issuer base from a JWKS URL (no secrets)."""
    raw = (jwks_url or "").strip().rstrip("/")
    suffix = "/.well-known/jwks.json"
    if raw.lower().endswith(suffix):
        return raw[: -len(suffix)]
    return raw


def _looks_like_jwks_url(url: str) -> bool:
    u = (url or "").strip()
    if not u:
        return False
    parsed = urlparse(u)
    if parsed.scheme not in ("https", "http"):
        return False
    return "/.well-known/jwks.json" in parsed.path.lower()


def resolve_clerk_runtime_mode(settings: Settings) -> str:
    """
    platform_driver | enterprise | legacy | incomplete

    Delegates to ``clerk_configuration_mode``. ``unified`` is retired and never
    reported as a healthy mode.
    """
    return clerk_configuration_mode(settings)


def audit_clerk_settings(settings: Settings) -> list[ConfigAuditFinding]:
    """Return findings for Clerk-related settings. Never includes key values."""
    findings: list[ConfigAuditFinding] = []
    mode = resolve_clerk_runtime_mode(settings)
    findings.append(
        ConfigAuditFinding(
            name="CLERK_CONFIGURATION_MODE",
            status="ok" if mode != "incomplete" else "missing",
            detail=mode,
        )
    )
    findings.append(
        ConfigAuditFinding(
            name="CLERK_UNIFIED_MODE",
            status="info",
            detail="true" if settings.clerk_unified_mode else "false",
        )
    )
    findings.append(
        ConfigAuditFinding(
            name="APP_ENV",
            status="info",
            detail=(settings.app_env or "").strip() or "unset",
        )
    )

    # Platform triad (unified / legacy names)
    for name, value, expect in (
        ("CLERK_PUBLISHABLE_KEY", settings.clerk_publishable_key, "pk"),
        ("CLERK_SECRET_KEY", settings.clerk_secret_key, "sk"),
    ):
        status = _classify_key_prefix(value, expect=expect)  # type: ignore[arg-type]
        if status == "empty":
            findings.append(ConfigAuditFinding(name=name, status="empty", detail="not set"))
        elif status == "malformed_prefix":
            findings.append(
                ConfigAuditFinding(name=name, status="malformed_prefix", detail=f"expected {expect}_*")
            )
        else:
            findings.append(ConfigAuditFinding(name=name, status=status, detail="prefix ok"))

    jwks = settings.clerk_jwks_url.strip()
    if not jwks:
        findings.append(ConfigAuditFinding(name="CLERK_JWKS_URL", status="empty", detail="not set"))
    elif not _looks_like_jwks_url(jwks):
        findings.append(
            ConfigAuditFinding(name="CLERK_JWKS_URL", status="malformed_prefix", detail="not a JWKS URL")
        )
    else:
        findings.append(ConfigAuditFinding(name="CLERK_JWKS_URL", status="ok", detail="shape ok"))

    # Per-portal enterprise slots
    portal_attrs = {
        "customer": (
            "CLERK_CUSTOMER_PUBLISHABLE_KEY",
            settings.clerk_customer_publishable_key,
            "CLERK_CUSTOMER_SECRET_KEY",
            settings.clerk_customer_secret_key,
            "CLERK_CUSTOMER_JWKS_URL",
            settings.clerk_customer_jwks_url,
        ),
        "merchant": (
            "CLERK_MERCHANT_PUBLISHABLE_KEY",
            settings.clerk_merchant_publishable_key,
            "CLERK_MERCHANT_SECRET_KEY",
            settings.clerk_merchant_secret_key,
            "CLERK_MERCHANT_JWKS_URL",
            settings.clerk_merchant_jwks_url,
        ),
        "admin": (
            "CLERK_ADMIN_PUBLISHABLE_KEY",
            settings.clerk_admin_publishable_key,
            "CLERK_ADMIN_SECRET_KEY",
            settings.clerk_admin_secret_key,
            "CLERK_ADMIN_JWKS_URL",
            settings.clerk_admin_jwks_url,
        ),
        "driver": (
            "CLERK_DRIVER_PUBLISHABLE_KEY",
            settings.clerk_driver_publishable_key,
            "CLERK_DRIVER_SECRET_KEY",
            settings.clerk_driver_secret_key,
            "CLERK_DRIVER_JWKS_URL",
            settings.clerk_driver_jwks_url,
        ),
    }

    for _portal, (
        pk_name,
        pk_val,
        sk_name,
        sk_val,
        jwks_name,
        jwks_val,
    ) in portal_attrs.items():
        pk_status = _classify_key_prefix(pk_val, expect="pk")
        sk_status = _classify_key_prefix(sk_val, expect="sk")
        findings.append(
            ConfigAuditFinding(
                name=pk_name,
                status=pk_status if pk_status != "empty" else "empty",
                detail="prefix ok" if pk_status in ("ok", "test_key", "live_key") else "not set or bad prefix",
            )
        )
        findings.append(
            ConfigAuditFinding(
                name=sk_name,
                status=sk_status if sk_status != "empty" else "empty",
                detail="prefix ok" if sk_status in ("ok", "test_key", "live_key") else "not set or bad prefix",
            )
        )
        if not (jwks_val or "").strip():
            findings.append(ConfigAuditFinding(name=jwks_name, status="empty", detail="not set"))
        elif not _looks_like_jwks_url(jwks_val):
            findings.append(
                ConfigAuditFinding(name=jwks_name, status="malformed_prefix", detail="not a JWKS URL")
            )
        else:
            findings.append(ConfigAuditFinding(name=jwks_name, status="ok", detail="shape ok"))

        # pk/sk environment mismatch within a portal slot
        if pk_status == "test_key" and sk_status == "live_key":
            findings.append(
                ConfigAuditFinding(
                    name=f"{pk_name}+{sk_name}",
                    status="env_mismatch",
                    detail="publishable is test but secret is live",
                )
            )
        if pk_status == "live_key" and sk_status == "test_key":
            findings.append(
                ConfigAuditFinding(
                    name=f"{pk_name}+{sk_name}",
                    status="env_mismatch",
                    detail="publishable is live but secret is test",
                )
            )

    # Policy / webhook names (presence only)
    for name, value in (
        ("CLERK_AUDIENCE", settings.clerk_audience),
        ("CLERK_AUTHORIZED_PARTIES", settings.clerk_authorized_parties),
        ("CLERK_AUTHORIZED_ISSUERS", settings.clerk_authorized_issuers),
        ("CLERK_WEBHOOK_SIGNING_SECRET", settings.clerk_webhook_signing_secret),
    ):
        findings.append(
            ConfigAuditFinding(
                name=name,
                status="ok" if (value or "").strip() else "empty",
                detail="set" if (value or "").strip() else "optional / not set",
            )
        )

    # Issuer allowlist vs JWKS bases
    allowed = [
        x.strip().rstrip("/")
        for x in (settings.clerk_authorized_issuers or "").split(",")
        if x.strip()
    ]
    if allowed:
        derived = {
            issuer_from_jwks_url(app.jwks_url)
            for app in clerk_app_configs(settings)
            if app.jwks_url
        }
        if settings.clerk_jwks_url.strip():
            derived.add(issuer_from_jwks_url(settings.clerk_jwks_url))
        derived.discard("")
        if derived and not derived.intersection(set(allowed)):
            findings.append(
                ConfigAuditFinding(
                    name="CLERK_AUTHORIZED_ISSUERS",
                    status="env_mismatch",
                    detail="no JWKS-derived issuer overlaps allowlist",
                )
            )
        else:
            findings.append(
                ConfigAuditFinding(
                    name="CLERK_AUTHORIZED_ISSUERS",
                    status="ok",
                    detail="allowlist overlaps JWKS issuers",
                )
            )

    if mode == "platform_driver":
        findings.append(
            ConfigAuditFinding(
                name="SECRET_ACCESS_MATRIX",
                status="info",
                detail="Platform triad for customer/merchant/website; Driver triad for drivers; admin uses staff IdP (no Clerk pk)",
            )
        )
    elif mode in ("unified", "enterprise"):
        findings.append(
            ConfigAuditFinding(
                name="CLERK_MODE_RETIRED",
                status="warn",
                detail=f"CLERK_MODE={mode} is retired — use platform_driver (Platform + Driver)",
            )
        )
    elif is_divergent_enterprise_clerk(settings) and settings.clerk_unified_mode:
        findings.append(
            ConfigAuditFinding(
                name="CLERK_UNIFIED_MODE_RETIRED",
                status="warn",
                detail="CLERK_UNIFIED_MODE=true is retired — set false and use platform_driver",
            )
        )

    findings.append(
        ConfigAuditFinding(
            name="CLERK_DEV_BYPASS",
            status="warn" if settings.clerk_dev_bypass and not is_local_env(settings.app_env) else "info",
            detail="true" if settings.clerk_dev_bypass else "false",
        )
    )

    return findings


def production_clerk_errors(settings: Settings) -> list[str]:
    """
    Hard errors for non-local production boot (name-only messages).

    Used by Settings validators and config-audit --strict.
    """
    if is_local_env(settings.app_env):
        return []

    errors: list[str] = []
    if settings.clerk_dev_bypass:
        errors.append("CLERK_DEV_BYPASS must be false outside local/development")

    mode = resolve_clerk_runtime_mode(settings)
    if mode == "incomplete":
        missing = ", ".join(f"CLERK_{k.upper()}_*" for k in ALL_CLERK_APP_KINDS)
        errors.append(
            "Clerk incomplete: set enterprise CLERK_{CUSTOMER,MERCHANT,ADMIN,DRIVER}_* "
            f"or unified CLERK_SECRET_KEY + CLERK_JWKS_URL (+ CLERK_UNIFIED_MODE) (need: {missing})"
        )
        return errors

    # Collect key environment statuses without values
    findings = audit_clerk_settings(settings)
    for f in findings:
        if f.status == "env_mismatch":
            errors.append(f"{f.name}: {f.detail}")
        if f.status == "test_key":
            errors.append(f"{f.name}: test keys are not allowed when APP_ENV is not local")
        if f.status == "malformed_prefix" and f.name.endswith(("_KEY", "_URL")):
            # Only fail hard on portal/platform keys that are set but malformed
            if "not set" not in f.detail:
                errors.append(f"{f.name}: {f.detail}")

    # In production, enterprise/unified must have usable JWKS somewhere
    if not clerk_app_configs(settings) and not settings.clerk_jwks_url.strip():
        errors.append("CLERK_JWKS_URL (or per-portal JWKS) required in production")

    # Prefer registry mode for dual-compat
    registry_mode = clerk_configuration_mode(settings)
    if registry_mode == "incomplete" and mode == "incomplete":
        errors.append("clerk_configuration_mode=incomplete")

    return errors


def audit_report_dict(settings: Settings) -> dict:
    """JSON-serializable audit report (safe to log / print)."""
    findings = audit_clerk_settings(settings)
    errors = production_clerk_errors(settings)
    return {
        "mode": resolve_clerk_runtime_mode(settings),
        "registry_mode": clerk_configuration_mode(settings),
        "app_env": settings.app_env,
        "ok": len(errors) == 0 or is_local_env(settings.app_env),
        "production_errors": errors,
        "findings": [f.to_dict() for f in findings],
    }
