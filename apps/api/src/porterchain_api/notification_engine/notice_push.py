"""Firebase push (doc 60 R7 / doc 61: web push + FCM/APNs) for driver route notices.
The notice stays in the in-app feed (route.notices) either way; push is best-effort and never blocks the write.
FCMService is log-only/dry-run unless FIREBASE_* + PUSH_SEND are configured (no credentials in tests)."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.models import NotificationDevice

logger = logging.getLogger(__name__)

COPY = {
    "leg_unlocked": ("Route ready", "Your parcels have been handed over. Your route is unlocked."),
    "leg_cancelled": ("Route cancelled", "The upstream pickup failed, so this leg is cancelled."),
    "leg_adjusted": ("Route changed", "Some parcels were removed from your route."),
}
COPY_FR = {
    "leg_unlocked": ("Trajet prêt", "Vos colis ont été remis. Votre trajet est débloqué."),
    "leg_cancelled": ("Trajet annulé", "La collecte en amont a échoué : ce trajet est annulé."),
    "leg_adjusted": ("Trajet modifié", "Des colis ont été retirés de votre trajet."),
}


def push_notice(db: Session, driver_id: str | None, kind: str, route_id: str, *, sender: Any = None) -> int:
    """Send one push per active driver device. Returns how many were accepted. Invalid tokens are deactivated."""
    if not driver_id:
        return 0
    if sender is None:
        from porterchain_api.notification_engine.fcm_service import FCMService
        sender = FCMService()
    devs = db.query(NotificationDevice).filter(NotificationDevice.user_role == "driver",
                                              NotificationDevice.user_id == str(driver_id),
                                              NotificationDevice.is_active.is_(True)).all()
    sent = 0
    for d in devs:
        fr = (d.language or "").lower().startswith("fr")
        title, body = (COPY_FR if fr else COPY).get(kind, ("Route update", "Open the app to see the change."))
        try:
            ok, _err, invalid = sender.send(d.fcm_token, title=title, body=body,
                                            data={"kind": kind, "route_id": route_id},
                                            deep_link=f"porterchain-driver://batches/routes/{route_id}",
                                            priority="high" if kind == "leg_cancelled" else "normal")
        except Exception:  # noqa: BLE001 - push must never break the notice
            logger.exception("notice push failed")
            continue
        if ok:
            sent += 1
        elif invalid:
            d.is_active, d.invalidated_at = False, datetime.now(UTC)
    return sent
