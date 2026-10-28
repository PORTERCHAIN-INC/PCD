"""Single writer for ``packages.status`` (chain of custody).

Every status change goes through :func:`set_package_status`: legal moves are applied and
logged to ``order_events`` (``package.status_changed``); illegal ones are rejected with
``ValueError("illegal_package_transition")`` and logged as ``package.transition_rejected``
in an independent transaction, so the audit row survives the caller's rollback.
The DB keeps ``ck_packages_status_known`` so no unknown status can be written either.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.booking_models import OrderEvent, Package
from porterchain_api.domain.states import PackageState, can_transition_package
from porterchain_api.platform.transition_audit import log_rejected_transition

EVENT_CHANGED = "package.status_changed"
EVENT_REJECTED = "package.transition_rejected"


class IllegalPackageTransition(ValueError):
    def __init__(self, from_state: str, to_state: str) -> None:
        super().__init__("illegal_package_transition")
        self.from_state = from_state
        self.to_state = to_state


def set_package_status(
    db: Session,
    pkg: Package,
    to_state: PackageState | str,
    *,
    actor_type: str = "system",
    actor_id: str | None = None,
    source: str = "system",
) -> bool:
    """Move ``pkg`` to ``to_state``. Returns False for a same-state no-op, True on change."""
    target = PackageState(to_state)
    current = PackageState(pkg.status or PackageState.MANIFESTED)
    if current == target:
        return False
    if not can_transition_package(current, target):
        log_rejected_transition(
            db,
            order_id=pkg.order_id,
            event_type=EVENT_REJECTED,
            from_state=current.value,
            to_state=target.value,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"package_id": pkg.id, "source": source},
        )
        raise IllegalPackageTransition(current.value, target.value)
    pkg.status = target.value
    db.add(pkg)
    db.add(
        OrderEvent(
            order_id=pkg.order_id,
            event_type=EVENT_CHANGED,
            from_state=current.value,
            to_state=target.value,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"package_id": pkg.id, "source": source},
        )
    )
    return True
