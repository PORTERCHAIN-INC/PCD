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
        "admin_engine/booking_draft_admin_service.py",
        "admin_engine/clerk_directory_service.py",
        "admin_engine/control_tower_service.py",
        "admin_engine/finance_service.py",
        "admin_engine/merchant_ar_service.py",
        "admin_engine/merchant_service.py",
        "admin_engine/platform_user_authorize.py",
        "admin_engine/pricing_service.py",
        "admin_engine/settings_service.py",
        "auth/invitation_service.py",
        "auth/merchant.py",
        "auth/merchant_onboarding.py",
        "auth/user_sync_service.py",
        "collaboration_engine/crm_companies.py",
        "collaboration_engine/crm_contacts.py",
        "collaboration_engine/crm_contracts.py",
        "collaboration_engine/crm_deals.py",
        "collaboration_engine/crm_leads.py",
        "collaboration_engine/crm_quotations.py",
        "collaboration_engine/crm_tasks.py",
        "compliance_engine/privacy_service.py",
        "gateway_engine/merchant_api.py",
        "support_engine/support_context.py",
        "support_engine/support_tickets.py",
    }
)

# §3.2.3 — legacy writers outside admin_engine (shrink over time).
_LEGACY_ADMIN_MODEL_WRITERS: frozenset[str] = frozenset(
    {
        "auth/admin.py",
        "auth/invitation_service.py",
        "auth/merchant_onboarding.py",
        "auth/sso_service.py",
        "auth/user_sync_service.py",
        "booking_engine/customer_service.py",
        "driver_engine/auth_service.py",
        "fleetbase_engine/integration_bridge.py",
        "fleetbase_engine/webhook_processor.py",
        "merchant_engine/support_bridge_service.py",
        "routers/auth.py",
        "support_engine/claims_mutations.py",
        "support_engine/support_context.py",
        "support_engine/support_kb.py",
        "support_engine/support_ticket_actions.py",
        "support_engine/support_tickets.py",
    }
)

# §3.2.6 — legacy writers outside collaboration_engine (shrink over time).
_LEGACY_CRM_MODEL_WRITERS: frozenset[str] = frozenset(
    {
        "merchant_engine/contacts_service.py",
    }
)

_LEGACY_IDENTITY_MODEL_WRITERS: frozenset[str] = frozenset(
    {
        "auth/sso_service.py",
    }
)

_USER_SYNC_WRITER = frozenset({"auth/user_sync_service.py"})

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
    },
    {
        "model_module": "driver_models",
        "owner_prefix": "driver_engine",
        "legacy_writers": frozenset(),
        "section": "§3.2.4",
        "mutation_re": _DB_STRUCTURAL_MUTATION,
    },
    {
        "model_module": "fleetbase_models",
        "owner_prefix": "fleetbase_engine",
        "legacy_writers": frozenset(),
        "section": "§3.2.5",
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
        "owner_files": _USER_SYNC_WRITER,
        "legacy_writers": _LEGACY_IDENTITY_MODEL_WRITERS,
        "section": "§3.2.7",
        "mutation_re": _DB_MUTATION,
    },
    {
        "model_module": "user_models",
        "owner_prefix": "auth",
        "owner_files": _USER_SYNC_WRITER,
        "legacy_writers": frozenset({"auth/merchant_onboarding.py"}),
        "section": "§3.2.7",
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
        if rel in legacy_writers:
            continue
        target = owner_files or owner_prefix
        failures.append(f"{section} new {model_module} writer outside {target}: {rel}")
    return failures


def main() -> int:
    failures: list[str] = []
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
        "§3.2.4 driver + §3.2.5 fleetbase: 0 legacy; "
        f"§3.2.6 crm: {len(_LEGACY_CRM_MODEL_WRITERS)} legacy; "
        f"§3.2.7 identity/user via user_sync_service ({len(_LEGACY_IDENTITY_MODEL_WRITERS)} legacy)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
