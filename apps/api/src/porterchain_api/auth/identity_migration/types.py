"""Phase 7 identity migration types — no secrets, no credential material."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SourceApp = Literal["admin", "merchant", "driver", "customer"]

VALID_SOURCE_APPS: frozenset[str] = frozenset({"admin", "merchant", "driver", "customer"})

RecordStatus = Literal[
    "pending",
    "matched_identity",
    "matched_map",
    "email_candidate",
    "unmatched",
    "conflict",
    "skipped",
    "dry_run_ok",
    "applied",
    "failed",
]


@dataclass(frozen=True)
class SourceExportUser:
    source_app: str
    source_clerk_user_id: str
    source_issuer: str | None = None
    email: str | None = None
    email_verified: bool = False
    # Recorded only to prove we ignore it for elevation
    metadata_role_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExplicitMapLink:
    source_app: str
    source_clerk_user_id: str
    target_clerk_user_id: str | None = None
    internal_user_id: str | None = None
    roles: list[str] = field(default_factory=list)


@dataclass
class AdminAllowlist:
    """Invite-only / admin roles may only come from this reviewed list."""

    legacy_admin_clerk_user_ids: set[str] = field(default_factory=set)
    role_by_clerk_user_id: dict[str, list[str]] = field(default_factory=dict)

    def allows_admin_id(self, clerk_user_id: str) -> bool:
        return clerk_user_id in self.legacy_admin_clerk_user_ids

    def roles_for(self, clerk_user_id: str) -> list[str]:
        return list(self.role_by_clerk_user_id.get(clerk_user_id, []))


@dataclass
class PlannedRecord:
    source_app: str
    source_clerk_user_id: str
    source_issuer: str | None
    email: str | None
    email_verified: bool
    status: str
    conflict_reason: str | None = None
    internal_user_id: str | None = None
    target_clerk_user_id: str | None = None
    proposed_roles: list[str] = field(default_factory=list)
    match_method: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MigrationPlan:
    label: str
    records: list[PlannedRecord]
    source_summary: dict[str, Any] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)

    def recompute_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {"total": len(self.records)}
        for r in self.records:
            counts[r.status] = counts.get(r.status, 0) + 1
        self.counts = counts
        return counts
