"""Free text from merchants/customers -> English for admin (self-hosted LibreTranslate, async).

Admin is English only. Whenever a watched free-text field is written (order instructions,
address notes, claim descriptions, support tickets) a ``pending`` row is queued in the same
flush. The worker (``translate_pending``) detects the language and, if it is not English,
stores the English translation. The original text and its language are always kept.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, event, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from porterchain_api.db import Base

log = logging.getLogger(__name__)

LANG_NAMES = {"fr": "French", "en": "English", "es": "Spanish", "pt": "Portuguese", "it": "Italian",
              "de": "German", "zh": "Chinese", "ar": "Arabic", "hi": "Hindi", "pa": "Punjabi"}
MAX_ATTEMPTS = 5
ADDRESS_NOTE_KEYS = (
    "notes", "instructions", "access_notes", "delivery_instructions", "buzzer_notes", "site_access_notes",
)


class FreeTextTranslation(Base):
    __tablename__ = "free_text_translations"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "field", name="uq_free_text_translations_target"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(48))
    entity_id: Mapped[str] = mapped_column(String(64))
    field: Mapped[str] = mapped_column(String(64))
    original: Mapped[str] = mapped_column(Text)
    source_lang: Mapped[str | None] = mapped_column(String(8), nullable=True)
    translated_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pending | translated | same (already English) | failed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    translated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _watched(obj: Any) -> list[tuple[str, str, str | None]]:
    """(entity_type, field, text) pairs for a model instance, or [] if not watched."""
    name = type(obj).__name__
    out: list[tuple[str, str, str | None]] = []
    if name in ("Order", "Booking"):
        et = "order" if name == "Order" else "booking"
        out.append((et, "special_instructions", getattr(obj, "special_instructions", None)))
        for side in ("pickup", "dropoff"):
            addr = getattr(obj, side, None) or {}
            if isinstance(addr, dict):
                for k in ADDRESS_NOTE_KEYS:
                    if isinstance(addr.get(k), str):
                        out.append((et, f"{side}.{k}", addr[k]))
    elif name == "Claim":
        out.append(("claim", "description", getattr(obj, "description", None)))
    elif name == "SupportTicket":
        out.append(("support_ticket", "subject", getattr(obj, "subject", None)))
        out.append(("support_ticket", "description", getattr(obj, "description", None)))
    return out


def queue(db: Session, entity_type: str, entity_id: str, field: str, text: str | None) -> None:
    text = (text or "").strip()
    if not text or not entity_id:
        return
    with db.no_autoflush:
        row = (
            db.query(FreeTextTranslation)
            .filter_by(entity_type=entity_type, entity_id=str(entity_id), field=field)
            .one_or_none()
        )
    if row is None:
        db.add(FreeTextTranslation(entity_type=entity_type, entity_id=str(entity_id), field=field,
                                   original=text, status="pending", attempts=0))
    elif row.original != text:
        row.original, row.status, row.attempts = text, "pending", 0
        row.translated_en = row.source_lang = None


@event.listens_for(Session, "before_flush")
def _queue_before_flush(session: Session, _ctx: Any, _instances: Any) -> None:
    for obj in list(session.new) + list(session.dirty):
        if isinstance(obj, FreeTextTranslation):
            continue
        pairs = _watched(obj)
        if not pairs:
            continue
        oid = getattr(obj, "id", None)
        if oid is None and obj in session.new:
            obj.id = oid = str(uuid.uuid4())
        for et, field, text in pairs:
            try:
                queue(session, et, oid, field, text)
            except Exception:  # never break the user's write
                log.exception("free_text_translation.queue_failed")


def _call(url: str, path: str, data: dict[str, Any]) -> Any:
    r = httpx.post(url.rstrip("/") + path, json=data, timeout=20)
    r.raise_for_status()
    return r.json()


def translate_text(url: str, text: str) -> tuple[str, str | None]:
    """Return (source_lang, english or None if already English)."""
    det = _call(url, "/detect", {"q": text})
    lang = (det[0]["language"] if det else "en") or "en"
    if lang == "en":
        return "en", None
    res = _call(url, "/translate", {"q": text, "source": lang, "target": "en", "format": "text"})
    return lang, res.get("translatedText")


def translate_pending(db: Session, url: str, limit: int = 50) -> dict[str, int]:
    if not url:
        return {"skipped": 1}
    rows = (
        db.query(FreeTextTranslation)
        .filter(FreeTextTranslation.status == "pending", FreeTextTranslation.attempts < MAX_ATTEMPTS)
        .order_by(FreeTextTranslation.created_at)
        .limit(limit)
        .all()
    )
    done = failed = 0
    for row in rows:
        row.attempts = (row.attempts or 0) + 1
        try:
            lang, en = translate_text(url, row.original)
            row.source_lang = lang
            row.translated_en = en
            row.status = "same" if en is None else "translated"
            row.translated_at = datetime.now(UTC)
            done += 1
        except Exception:
            log.warning("free_text_translation.failed id=%s", row.id)
            if row.attempts >= MAX_ATTEMPTS:
                row.status = "failed"
            failed += 1
        db.commit()
    return {"translated": done, "failed": failed}


def for_entity(db: Session, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
    rows = db.query(FreeTextTranslation).filter_by(entity_type=entity_type, entity_id=str(entity_id)).all()
    return [
        {
            "field": r.field, "original": r.original, "source_lang": r.source_lang,
            "source_language": LANG_NAMES.get(r.source_lang or "", r.source_lang),
            "translated_en": r.translated_en, "status": r.status,
            "label": (f"Translated from {LANG_NAMES.get(r.source_lang or '', r.source_lang)}"
                      if r.status == "translated" else None),
        }
        for r in rows
    ]


def english_note_lines(db: Session, order_id: str | None, lines: list[str]) -> list[str]:
    """Driver app is English only: after each note line that contains translated free text,
    add "English: <translation>" (the original stays first). Missing or pending translations
    leave the lines unchanged; translation lookups never break a driver payload."""
    if not order_id or not lines:
        return lines
    try:
        rows = (
            db.query(FreeTextTranslation)
            .filter_by(entity_type="order", entity_id=str(order_id), status="translated")
            .all()
        )
    except Exception:  # noqa: BLE001
        log.debug("english_note_lines lookup failed", exc_info=True)
        return lines
    pairs = [(r.original.strip(), (r.translated_en or "").strip()) for r in rows if r.original and r.translated_en]
    if not pairs:
        return lines
    out: list[str] = []
    for line in lines:
        out.append(line)
        for original, english in pairs:
            if original and original in line and english and english != original:
                out.append(f"English: {english}")
                break
    return out
