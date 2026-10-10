#!/usr/bin/env python3
"""§3.2.2–3.2.5 — bounded-context ORM write ownership guards."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src/porterchain_api"

_DB_MUTATION = re.compile(
    r"\bdb\.(add|delete|merge|flush|commit)\s*\(|"
    r"\bsession\.(add|delete|merge|flush|commit)\s*\(",
    re.IGNORECASE,
)

# Structural writes only — avoids false positives when a module reads one context
# but commits mutations on another (e.g. control_tower + fleetbase audit reads).
_DB_STRUCTURAL_MUTATION = re.compile(
    r"\bdb\.(add|delete|merge|flush)\s*\(|"
    r"\bsession\.(add|delete|merge|flush)\s*\(",
    re.IGNORECASE,
)

# §3.2.2 — legacy writers outside merchant_engine (shrink over time).
_LEGACY_MERCHANT_MODEL_WRITERS: frozenset[str] = frozenset(
    {
        "admin_engine/merchant_org.py",  # Wave compose — shrink via merchant_engine APIs
        "admin_engine/shopify_control_service.py",  # Shopify control plane (shop policy / hold / repush)
        "admin_engine/control_tower/exceptions.py",  # exception board Shopify hold/release
        "admin_engine/control_tower/service.py",  # control tower Shopify ops side-effects
        "integrations/shopify_carrier_rates.py",  # carrier quote persistence
        "notification_engine/preference_service.py",  # merchant notif prefs
    }
)

# §3.2.3 — legacy writers outside admin_engine (shrink over time).
_LEGACY_ADMIN_MODEL_WRITERS: frozenset[str] = frozenset(
    {
        "customer_fast/admin360.py",  # integration: branch debt
        "finance_ops/payout_runs.py",  # integration: branch debt
        "auth/staff_session.py",  # StaffWebAuthnCredential — Staff IdP owns
        "merchant_engine/billing_service.py",  # MerchantContract read+flush path
        "notification_engine/delivery_service.py",  # AdminUser resolve on deliver
        "booking_engine/order_sla.py",  # SLA timestamps on admin-adjacent order rows
    }
)

# §3.2.4 — legacy writers outside driver_engine (shrink over time).
_LEGACY_DRIVER_MODEL_WRITERS: frozenset[str] = frozenset({"finance_ops/payout_runs.py"})  # integration: branch debt

# §3.2.6 — legacy writers outside collaboration_engine (shrink over time).
_LEGACY_CRM_MODEL_WRITERS: frozenset[str] = frozenset(
    {
        "customer_fast/privacy.py",  # integration: branch debt
        "admin_engine/merchant_org.py",
        "routers/admin/leads.py",  # thin later — move commits to collaboration_engine
    }
)

_LEGACY_IDENTITY_MODEL_WRITERS: frozenset[str] = frozenset()

_USER_SYNC_WRITER = frozenset({"auth/user_sync_service.py"})

_IDENTITY_AUTH_WRITERS = frozenset(
    {
        "auth/user_sync_service.py",
        "auth/email_identity.py",
        "auth/ensure_user_service.py",
        "auth/identity_fk_backfill.py",
        "auth/identity_links.py",
        "auth/staff_identity.py",
        "auth/staff_session.py",
        "auth/principal_resolution_service.py",
        "auth/admin.py",
        "authz/tuples.py",
        "admin_engine/platform_user_authorize.py",
    }
)
_OWNERSHIP_CHECKS: tuple[dict[str, object], ...] = (
    {
        "model_module": "merchant_models",
        "owner_prefix": "merchant_engine",
        "legacy_writers": _LEGACY_MERCHANT_MODEL_WRITERS,
        "section": "§3.2.2",
        "mutation_re": _DB_MUTATION,
    },
    {
        "model_module": "admin_models",
        "owner_prefix": "admin_engine",
        "legacy_writers": _LEGACY_ADMIN_MODEL_WRITERS,
        "section": "§3.2.3",
        "mutation_re": _DB_MUTATION,
        "extra_owner_prefixes": ("support_engine", "driver_engine"),
    },
    {
        "model_module": "driver_models",
        "owner_prefix": "driver_engine",
        "legacy_writers": _LEGACY_DRIVER_MODEL_WRITERS,
        "section": "§3.2.4",
        "mutation_re": _DB_STRUCTURAL_MUTATION,
    },
    {
        "model_module": "crm_models",
        "owner_prefix": "collaboration_engine",
        "legacy_writers": _LEGACY_CRM_MODEL_WRITERS,
        "section": "§3.2.6",
        "mutation_re": _DB_STRUCTURAL_MUTATION,
    },
    {
        "model_module": "identity_models",
        "owner_prefix": "auth",
        "owner_files": _IDENTITY_AUTH_WRITERS,
        "legacy_writers": _LEGACY_IDENTITY_MODEL_WRITERS,
        "section": "§3.2.7",
        "mutation_re": _DB_MUTATION,
    },
    {
        "model_module": "user_models",
        "owner_prefix": "auth",
        "owner_files": _IDENTITY_AUTH_WRITERS,
        "legacy_writers": frozenset({"admin_engine/operations_service.py", "notification_engine/delivery_service.py"}),
        "section": "§3.2.7",
        "mutation_re": _DB_MUTATION,
    },
    {
        "model_module": "website_content_models",
        "owner_prefix": "content_engine",
        "legacy_writers": frozenset(),
        "section": "§3.2.8",
        "mutation_re": _DB_MUTATION,
    },
)


def _rel(path: Path) -> str:
    return str(path.relative_to(API_SRC))


def _check_model_writes(
    *,
    model_module: str,
    owner_prefix: str,
    legacy_writers: frozenset[str],
    section: str,
    mutation_re: re.Pattern[str],
    owner_files: frozenset[str] | None = None,
    extra_owner_prefixes: tuple[str, ...] = (),
) -> list[str]:
    failures: list[str] = []
    import_re = re.compile(
        rf"from porterchain_api\.{re.escape(model_module)} import|"
        rf"import porterchain_api\.{re.escape(model_module)}"
    )
    for path in sorted(API_SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not import_re.search(text):
            continue
        if not mutation_re.search(text):
            continue
        rel = _rel(path)
        if owner_files is not None:
            if rel in owner_files:
                continue
        elif rel.startswith(f"{owner_prefix}/"):
            continue
        elif any(rel.startswith(f"{prefix}/") for prefix in extra_owner_prefixes):
            continue
        if rel in legacy_writers:
            continue
        target = owner_files or owner_prefix
        failures.append(f"{section} new {model_module} writer outside {target}: {rel}")
    return failures


def _check_no_models_strangler() -> list[str]:
    failures: list[str] = []
    strangler = API_SRC / "models.py"
    if strangler.exists():
        failures.append("§3.2.1 porterchain_api.models.py strangler must not exist — import booking_models")
    import_re = re.compile(r"from porterchain_api\.models import|import porterchain_api\.models")
    for path in sorted(API_SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if import_re.search(text):
            failures.append(f"§3.2.1 import of deleted models.py strangler: {_rel(path)}")
    return failures


def main() -> int:
    failures: list[str] = _check_no_models_strangler()
    for spec in _OWNERSHIP_CHECKS:
        failures.extend(_check_model_writes(**spec))  # type: ignore[arg-type]

    if failures:
        print("Model ownership guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print(
        "Model ownership guard passed "
        f"(§3.2.2 merchant: {len(_LEGACY_MERCHANT_MODEL_WRITERS)} legacy; "
        f"§3.2.3 admin: {len(_LEGACY_ADMIN_MODEL_WRITERS)} legacy; "
        f"§3.2.4 driver: {len(_LEGACY_DRIVER_MODEL_WRITERS)} legacy; "
        f"§3.2.6 crm: {len(_LEGACY_CRM_MODEL_WRITERS)} legacy; "
        f"§3.2.7 identity/user via user_sync_service ({len(_LEGACY_IDENTITY_MODEL_WRITERS)} legacy); "
        "§3.2.8 website content: 0 legacy."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
