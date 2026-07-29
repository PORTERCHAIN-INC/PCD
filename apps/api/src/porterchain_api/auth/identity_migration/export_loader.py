"""Load Clerk export files from a path outside the git repo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from porterchain_api.auth.ensure_user_service import normalize_email
from porterchain_api.auth.identity_migration.types import SourceExportUser, VALID_SOURCE_APPS


def _assert_outside_repo(path: Path, repo_root: Path | None) -> None:
    """Refuse to read exports from inside the git working tree when repo_root is known."""
    if repo_root is None:
        return
    try:
        path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return
    raise ValueError(
        f"Exports must live outside the repository (got {path}). "
        "Place Clerk export JSON under a path like ~/porterchain-migration-exports/."
    )


def _extract_email(user: dict[str, Any]) -> tuple[str | None, bool]:
    emails = user.get("email_addresses") or user.get("emails") or []
    if isinstance(emails, str):
        return normalize_email(emails), False
    primary = None
    verified = False
    for entry in emails:
        if not isinstance(entry, dict):
            continue
        addr = normalize_email(entry.get("email_address") or entry.get("email"))
        if not addr:
            continue
        v = entry.get("verification") or {}
        is_v = False
        if isinstance(v, dict):
            is_v = (v.get("status") or "").lower() == "verified"
        elif entry.get("verified") is True:
            is_v = True
        if entry.get("id") == user.get("primary_email_address_id") or primary is None:
            primary = addr
            verified = is_v
        if is_v and primary is None:
            primary = addr
            verified = True
    if primary is None:
        primary = normalize_email(user.get("email") or user.get("primary_email"))
    return primary, verified


def _metadata_role_hint(user: dict[str, Any]) -> str | None:
    meta = user.get("public_metadata") or user.get("unsafe_metadata") or {}
    if not isinstance(meta, dict):
        return None
    for key in ("role", "porterchain_role", "roles"):
        val = meta.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, list) and val:
            return str(val[0])
    return None


def parse_export_document(doc: Any, *, default_source_app: str | None = None) -> list[SourceExportUser]:
    """
    Accept:
      - { "source_app": "admin", "issuer": "...", "users": [ ... ] }
      - { "source_app": "admin", "users": [ ... ] }
      - [ user, user, ... ] with default_source_app required
    """
    out: list[SourceExportUser] = []
    issuer: str | None = None
    source_app = default_source_app
    users: list[Any]

    if isinstance(doc, dict):
        source_app = (doc.get("source_app") or doc.get("portal") or default_source_app or "").strip().lower()
        issuer = (doc.get("issuer") or doc.get("source_issuer") or None) or None
        if isinstance(issuer, str):
            issuer = issuer.strip() or None
        users = doc.get("users") or doc.get("data") or []
        if not users and "id" in doc:
            users = [doc]
    elif isinstance(doc, list):
        users = doc
    else:
        raise ValueError("export JSON must be an object or array")

    if not source_app or source_app not in VALID_SOURCE_APPS:
        raise ValueError(
            f"source_app must be one of {sorted(VALID_SOURCE_APPS)} (got {source_app!r})"
        )

    for user in users:
        if not isinstance(user, dict):
            continue
        clerk_id = str(user.get("id") or user.get("clerk_user_id") or user.get("user_id") or "").strip()
        if not clerk_id:
            continue
        email, verified = _extract_email(user)
        out.append(
            SourceExportUser(
                source_app=source_app,
                source_clerk_user_id=clerk_id,
                source_issuer=issuer,
                email=email,
                email_verified=verified,
                metadata_role_hint=_metadata_role_hint(user),
            )
        )
    return out


def load_exports_dir(exports_dir: Path, *, repo_root: Path | None = None) -> list[SourceExportUser]:
    """Load all *.json files from an exports directory (outside repo)."""
    root = Path(exports_dir).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"exports directory not found: {root}")
    _assert_outside_repo(root, repo_root)

    users: list[SourceExportUser] = []
    files = sorted(root.glob("*.json"))
    if not files:
        raise ValueError(f"no *.json export files in {root}")

    for path in files:
        # Filename hint: admin.json, porterchain-admin-users.json
        stem = path.stem.lower()
        default_app = None
        for app in VALID_SOURCE_APPS:
            if app in stem:
                default_app = app
                break
        raw = json.loads(path.read_text(encoding="utf-8"))
        try:
            users.extend(parse_export_document(raw, default_source_app=default_app))
        except ValueError as exc:
            raise ValueError(f"{path.name}: {exc}") from exc

    return users


def load_admin_allowlist(path: Path | None) -> "AdminAllowlist":
    from porterchain_api.auth.identity_migration.types import AdminAllowlist

    if path is None:
        return AdminAllowlist()
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    ids = set(data.get("legacy_admin_clerk_user_ids") or data.get("admin_clerk_user_ids") or [])
    roles = data.get("role_by_clerk_user_id") or {}
    return AdminAllowlist(
        legacy_admin_clerk_user_ids={str(x) for x in ids},
        role_by_clerk_user_id={str(k): [str(r) for r in (v or [])] for k, v in roles.items()},
    )


def load_explicit_map(path: Path | None) -> list["ExplicitMapLink"]:
    from porterchain_api.auth.identity_migration.types import ExplicitMapLink

    if path is None:
        return []
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    links = data.get("links") or data.get("mappings") or []
    out: list[ExplicitMapLink] = []
    for item in links:
        if not isinstance(item, dict):
            continue
        out.append(
            ExplicitMapLink(
                source_app=str(item.get("source_app") or "").strip().lower(),
                source_clerk_user_id=str(item.get("source_clerk_user_id") or "").strip(),
                target_clerk_user_id=(str(item["target_clerk_user_id"]).strip() if item.get("target_clerk_user_id") else None),
                internal_user_id=(str(item["internal_user_id"]).strip() if item.get("internal_user_id") else None),
                roles=[str(r) for r in (item.get("roles") or [])],
            )
        )
    return out
