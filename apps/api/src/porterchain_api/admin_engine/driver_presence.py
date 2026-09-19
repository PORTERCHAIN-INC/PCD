"""Keep Driver.is_online warm from Fleetbase list snapshots (worker path)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver

logger = logging.getLogger(__name__)


def patch_online_from_fleetbase(db: Session, fleetbase_drivers: list[dict[str, Any]]) -> None:
    online_by_fb: dict[str, bool] = {}
    for fd in fleetbase_drivers:
        fid = str(fd.get("id") or fd.get("uuid") or "")
        if not fid:
            continue
        online = fd.get("online")
        if not isinstance(online, bool):
            online = str(fd.get("status") or "").lower() in {"online", "active"}
        online_by_fb[fid] = bool(online)

    if not online_by_fb:
        return

    try:
        rows = (
            db.query(Driver)
            .filter(Driver.fleetbase_driver_id.in_(list(online_by_fb.keys())))
            .all()
        )
        dirty = False
        for d in rows:
            want = online_by_fb.get(d.fleetbase_driver_id or "")
            if want is None:
                continue
            if bool(d.is_online) != want:
                d.is_online = want
                dirty = True
        if dirty:
            db.commit()
    except Exception:
        logger.debug("ops_mirror patch is_online failed", exc_info=True)
        db.rollback()
