"""Read Interac notifications from the Zoho billing inbox over IMAP (read-only).

* Off unless ``INTERAC_IMAP_ENABLED=true``; credentials come from env only.
* Mailbox is opened ``readonly`` and fetched with ``BODY.PEEK[]`` — nothing is marked
  read, moved or deleted, and nothing is ever sent.
* Dedupe is by Message-ID in ``interac_transfers``.
"""

from __future__ import annotations

import email
import imaplib
import logging
from datetime import UTC, datetime, timedelta
from email import policy
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def imap_configured(settings) -> bool:
    return bool(
        settings.interac_imap_enabled
        and settings.interac_imap_host
        and settings.interac_imap_user
        and settings.interac_imap_password
    )


def fetch_and_ingest(db: Session, settings, *, client_factory=None) -> dict[str, Any]:
    from porterchain_api.billing_engine.interac.service import ingest_message

    if not imap_configured(settings):
        return {"enabled": False, "fetched": 0, "queued": 0}
    factory = client_factory or (lambda: imaplib.IMAP4_SSL(settings.interac_imap_host, settings.interac_imap_port))
    since = (datetime.now(UTC) - timedelta(days=max(1, int(settings.interac_imap_lookback_days)))).strftime(
        "%d-%b-%Y"
    )
    fetched = queued = 0
    client = factory()
    try:
        client.login(settings.interac_imap_user, settings.interac_imap_password)
        client.select(settings.interac_imap_folder or "INBOX", readonly=True)
        typ, data = client.search(None, "SINCE", since, "FROM", '"interac.ca"')
        if typ != "OK":
            return {"enabled": True, "fetched": 0, "queued": 0, "error": "search_failed"}
        for num in (data[0] or b"").split():
            typ, parts = client.fetch(num, "(BODY.PEEK[])")
            if typ != "OK" or not parts or not isinstance(parts[0], tuple):
                continue
            fetched += 1
            msg = email.message_from_bytes(parts[0][1], policy=policy.compat32)
            row = ingest_message(db, msg, authserv_id=settings.interac_authserv_id)
            if row is not None:
                queued += 1
        db.commit()
    finally:
        try:
            client.logout()
        except Exception:  # noqa: BLE001
            pass
    if queued:
        logger.info("interac inbox: fetched=%s queued=%s", fetched, queued)
    return {"enabled": True, "fetched": fetched, "queued": queued}
