"""SpiceDB client + in-memory store for tests / SPICEDB_ENABLED=false local soft mode."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("porterchain.authz")

_SCHEMA_PATH = Path(__file__).with_name("schema.zed")


@dataclass
class Relationship:
    resource_type: str
    resource_id: str
    relation: str
    subject_type: str
    subject_id: str


@dataclass
class _MemoryStore:
    """Process-local relationship store used when SpiceDB is disabled or unreachable in tests."""

    relationships: set[tuple[str, str, str, str, str]] = field(default_factory=set)
    schema_loaded: bool = False
    zed_token: str = "memory-token-1"
    lock: threading.Lock = field(default_factory=threading.Lock)

    def write(self, rels: list[Relationship], *, touch: bool = True) -> str:
        with self.lock:
            for r in rels:
                self.relationships.add(
                    (r.resource_type, r.resource_id, r.relation, r.subject_type, r.subject_id)
                )
            if touch:
                n = int(self.zed_token.rsplit("-", 1)[-1]) + 1
                self.zed_token = f"memory-token-{n}"
            return self.zed_token

    def delete(self, rels: list[Relationship]) -> str:
        with self.lock:
            for r in rels:
                self.relationships.discard(
                    (r.resource_type, r.resource_id, r.relation, r.subject_type, r.subject_id)
                )
            n = int(self.zed_token.rsplit("-", 1)[-1]) + 1
            self.zed_token = f"memory-token-{n}"
            return self.zed_token

    def check(
        self,
        *,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        """Minimal Check implementing our schema.zed permission expansions."""
        with self.lock:
            return self._check_unlocked(
                resource_type, resource_id, permission, subject_type, subject_id, set()
            )

    def _has(self, rt: str, rid: str, rel: str, st: str, sid: str) -> bool:
        return (rt, rid, rel, st, sid) in self.relationships

    def _subjects(self, rt: str, rid: str, rel: str) -> set[str]:
        return {t[4] for t in self.relationships if t[0] == rt and t[1] == rid and t[2] == rel}

    def _check_unlocked(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
        seen: set[tuple],
    ) -> bool:
        key = (resource_type, resource_id, permission, subject_type, subject_id)
        if key in seen:
            return False
        seen.add(key)

        if resource_type == "platform":
            from porterchain_api.authz.platform_roles import (
                PLATFORM_ROLE_RELATIONS,
                roles_for_platform_permission,
            )

            rid = resource_id or "porterchain"
            allowed = roles_for_platform_permission(permission)
            if not allowed:
                return False
            return any(
                self._has("platform", rid, rel, subject_type, subject_id)
                for rel in allowed
                if rel in PLATFORM_ROLE_RELATIONS
            )

        if resource_type == "organization":
            # Keep in sync with authz/schema.zed organization permissions.
            roles = {
                rel
                for rel in ("owner", "admin", "ops", "finance", "readonly", "member")
                if self._has("organization", resource_id, rel, subject_type, subject_id)
            }
            org_perms: dict[str, set[str]] = {
                "portal": {"owner", "admin", "ops", "finance", "readonly", "member"},
                "manage": {"owner", "admin"},
                "dashboard": {"owner", "admin", "ops", "finance", "readonly", "member"},
                "book": {"owner", "admin", "ops"},
                "bulk": {"owner", "admin", "ops"},
                "api_keys": {"owner", "admin"},
                "orders": {"owner", "admin", "ops", "finance", "readonly", "member"},
                "orders_write": {"owner", "admin", "ops"},
                "tracking": {"owner", "admin", "ops", "finance", "readonly", "member"},
                "invoices": {"owner", "admin", "ops", "finance", "readonly", "member"},
                "invoices_pay": {"owner", "admin", "finance"},
                "statements": {"owner", "admin", "finance", "readonly"},
                "reports": {"owner", "admin", "ops", "finance", "readonly", "member"},
                "billing": {"owner", "admin", "finance"},
                "users": {"owner", "admin"},
                "settings": {"owner", "admin", "finance", "ops"},
                "support": {"owner", "admin", "ops", "finance", "readonly", "member"},
                "claims": {"owner", "admin", "ops", "finance"},
            }
            allowed = org_perms.get(permission)
            if allowed is not None:
                return bool(roles & allowed)

        if resource_type in ("driver_profile", "customer_profile"):
            if permission == "access":
                return self._has(resource_type, resource_id, "owner", subject_type, subject_id)

        if resource_type == "order":
            if permission == "view":
                if self._has("order", resource_id, "viewer", subject_type, subject_id):
                    return True
                for org_id in self._subjects("order", resource_id, "parent"):
                    if self._check_unlocked(
                        "organization", org_id, "orders", subject_type, subject_id, seen
                    ):
                        return True
            if permission == "manage":
                for org_id in self._subjects("order", resource_id, "parent"):
                    if self._check_unlocked(
                        "organization", org_id, "orders_write", subject_type, subject_id, seen
                    ):
                        return True

        return False

    def lookup_resources(
        self,
        *,
        resource_type: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> list[str]:
        with self.lock:
            ids: set[str] = set()
            candidates = {t[1] for t in self.relationships if t[0] == resource_type}
            # Also check known platform singleton
            if resource_type == "platform":
                candidates.add("porterchain")
            for rid in candidates:
                if self._check_unlocked(
                    resource_type, rid, permission, subject_type, subject_id, set()
                ):
                    ids.add(rid)
            return sorted(ids)


class AuthzClient:
    """Check / WriteRelationships facade. Uses SpiceDB gRPC when enabled, else memory."""

    def __init__(
        self,
        *,
        enabled: bool,
        required: bool,
        endpoint: str,
        preshared_key: str,
        use_memory: bool = False,
    ) -> None:
        self.enabled = enabled
        self.required = required
        self.endpoint = endpoint
        self.preshared_key = preshared_key
        self._memory = _MemoryStore()
        self._grpc = None
        # Explicit memory (tests / SPICEDB_ENABLED=false) vs soft fallback when gRPC is down.
        self._force_memory = use_memory or not enabled
        self._use_memory = self._force_memory
        self._last_zed_token: str | None = None
        if not self._use_memory:
            self._try_connect()

    def _try_connect(self) -> None:
        try:
            # Must use a sync client. authzed's ``Client`` auto-picks ``grpc.aio`` when an
            # asyncio loop is running (uvicorn), which returns UnaryUnaryCall objects and
            # breaks Check/Write — empty session permissions → false customer redirects.
            from authzed.api.v1 import InsecureClient

            self._grpc = InsecureClient(self.endpoint, self.preshared_key)
            self._ensure_schema()
            self._use_memory = False
            logger.info("spicedb_connected endpoint=%s", self.endpoint)
        except Exception:  # noqa: BLE001
            logger.exception("spicedb_connect_failed endpoint=%s", self.endpoint)
            self._grpc = None
            if self.required:
                raise
            self._use_memory = True
            logger.warning("spicedb_falling_back_to_memory_store")

    def _ensure_backend(self) -> None:
        """Retry SpiceDB when API booted before the container was ready."""
        if self._force_memory:
            return
        if self._grpc is not None and not self._use_memory:
            return
        self._try_connect()

    def _ensure_schema(self) -> None:
        if self._grpc is None:
            return
        from authzed.api.v1 import WriteSchemaRequest

        schema = _SCHEMA_PATH.read_text(encoding="utf-8")
        self._grpc.WriteSchema(WriteSchemaRequest(schema=schema))

    @property
    def last_zed_token(self) -> str | None:
        return self._last_zed_token

    def write_relationships(self, rels: list[Relationship]) -> str:
        if not rels:
            return self._last_zed_token or ""
        self._ensure_backend()
        if self._use_memory or self._grpc is None:
            token = self._memory.write(rels)
            self._last_zed_token = token
            return token
        from authzed.api.v1 import (
            ObjectReference,
            RelationshipUpdate,
            SubjectReference,
            WriteRelationshipsRequest,
        )
        from authzed.api.v1 import Relationship as SpiceRel

        updates = []
        for r in rels:
            updates.append(
                RelationshipUpdate(
                    operation=RelationshipUpdate.Operation.OPERATION_TOUCH,
                    relationship=SpiceRel(
                        resource=ObjectReference(object_type=r.resource_type, object_id=r.resource_id),
                        relation=r.relation,
                        subject=SubjectReference(
                            object=ObjectReference(object_type=r.subject_type, object_id=r.subject_id)
                        ),
                    ),
                )
            )
        resp = self._grpc.WriteRelationships(WriteRelationshipsRequest(updates=updates))
        token = resp.written_at.token if resp.written_at else ""
        self._last_zed_token = token
        return token

    def delete_relationships(self, rels: list[Relationship]) -> str:
        if not rels:
            return self._last_zed_token or ""
        self._ensure_backend()
        if self._use_memory or self._grpc is None:
            token = self._memory.delete(rels)
            self._last_zed_token = token
            return token
        from authzed.api.v1 import (
            ObjectReference,
            RelationshipUpdate,
            SubjectReference,
            WriteRelationshipsRequest,
        )
        from authzed.api.v1 import Relationship as SpiceRel

        updates = []
        for r in rels:
            updates.append(
                RelationshipUpdate(
                    operation=RelationshipUpdate.Operation.OPERATION_DELETE,
                    relationship=SpiceRel(
                        resource=ObjectReference(object_type=r.resource_type, object_id=r.resource_id),
                        relation=r.relation,
                        subject=SubjectReference(
                            object=ObjectReference(object_type=r.subject_type, object_id=r.subject_id)
                        ),
                    ),
                )
            )
        resp = self._grpc.WriteRelationships(WriteRelationshipsRequest(updates=updates))
        token = resp.written_at.token if resp.written_at else ""
        self._last_zed_token = token
        return token

    def check(
        self,
        *,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str = "user",
        subject_id: str,
        zed_token: str | None = None,
    ) -> bool:
        self._ensure_backend()
        if resource_type == "platform":
            from porterchain_api.authz.platform_roles import to_schema_permission

            permission = to_schema_permission(permission)
        if self._use_memory or self._grpc is None:
            return self._memory.check(
                resource_type=resource_type,
                resource_id=resource_id,
                permission=permission,
                subject_type=subject_type,
                subject_id=subject_id,
            )
        from authzed.api.v1 import (
            CheckPermissionRequest,
            Consistency,
            ObjectReference,
            SubjectReference,
            ZedToken,
        )

        consistency = Consistency(minimize_latency=True)
        token = zed_token or self._last_zed_token
        if token:
            consistency = Consistency(at_least_as_fresh=ZedToken(token=token))
        resp = self._grpc.CheckPermission(
            CheckPermissionRequest(
                consistency=consistency,
                resource=ObjectReference(object_type=resource_type, object_id=resource_id),
                permission=permission,
                subject=SubjectReference(
                    object=ObjectReference(object_type=subject_type, object_id=subject_id)
                ),
            )
        )
        from authzed.api.v1 import CheckPermissionResponse

        return resp.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION

    def lookup_resources(
        self,
        *,
        resource_type: str,
        permission: str,
        subject_id: str,
        subject_type: str = "user",
    ) -> list[str]:
        self._ensure_backend()
        if resource_type == "platform":
            from porterchain_api.authz.platform_roles import to_schema_permission

            permission = to_schema_permission(permission)
        if self._use_memory or self._grpc is None:
            return self._memory.lookup_resources(
                resource_type=resource_type,
                permission=permission,
                subject_type=subject_type,
                subject_id=subject_id,
            )
        from authzed.api.v1 import (
            Consistency,
            LookupResourcesRequest,
            ObjectReference,
            SubjectReference,
            ZedToken,
        )

        req = LookupResourcesRequest(
            consistency=(
                Consistency(at_least_as_fresh=ZedToken(token=self._last_zed_token))
                if self._last_zed_token
                else Consistency(minimize_latency=True)
            ),
            resource_object_type=resource_type,
            permission=permission,
            subject=SubjectReference(
                object=ObjectReference(object_type=subject_type, object_id=subject_id)
            ),
        )
        return [r.resource_object_id for r in self._grpc.LookupResources(req)]


_client: AuthzClient | None = None
_client_lock = threading.Lock()


def get_authz_client(settings: object | None = None) -> AuthzClient:
    global _client
    with _client_lock:
        if _client is not None:
            return _client
        if settings is None:
            from porterchain_api.config import get_settings

            settings = get_settings()
        enabled = bool(getattr(settings, "spicedb_enabled", False))
        required = bool(getattr(settings, "spicedb_required", False))
        endpoint = str(getattr(settings, "spicedb_endpoint", "localhost:50051"))
        key = str(getattr(settings, "spicedb_preshared_key", "porterchain-spicedb-dev-key"))
        use_memory = bool(getattr(settings, "spicedb_use_memory", False)) or not enabled
        _client = AuthzClient(
            enabled=enabled,
            required=required,
            endpoint=endpoint,
            preshared_key=key,
            use_memory=use_memory,
        )
        return _client


def reset_authz_client() -> None:
    global _client
    with _client_lock:
        _client = None
