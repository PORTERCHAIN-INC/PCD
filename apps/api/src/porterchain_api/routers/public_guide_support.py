"""Helpers for public capacity-guide ingest (keeps router under LOC gate)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from porterchain_api.schemas_public import PublicGuideSlot

GUIDE_SOURCE = "website_capacity_guide"
GUIDE_TZ = ZoneInfo("America/Toronto")
TRANSCRIPT_MAX_CHARS = 16_000
TRANSCRIPT_MAX_TURNS = 40
SLOT_HOURS = range(9, 17)  # 09:00–16:00 starts → end by 17:00
SLOT_COUNT = 10


def phone_trim(raw: str | None) -> str | None:
    phone_raw = (raw or "").strip() or None
    return phone_raw[:32] if phone_raw else None


def merge_custom(existing: dict | None, patch: dict) -> dict:
    base = dict(existing or {})
    for key, value in patch.items():
        if value is not None and value != "":
            base[key] = value
    return base


def append_transcript(existing: dict | None, turns: list[dict], summary: str | None) -> dict:
    fields = dict(existing or {})
    history = fields.get("transcript")
    if not isinstance(history, list):
        history = []
    for turn in turns:
        history.append(
            {
                "role": turn.get("role", "user"),
                "content": str(turn.get("content", ""))[:4000],
                "at": datetime.now(UTC).isoformat(),
            }
        )
    history = history[-TRANSCRIPT_MAX_TURNS:]
    while history and len(str(history)) > TRANSCRIPT_MAX_CHARS:
        history = history[1:]
    fields["transcript"] = history
    if summary:
        fields["transcript_summary"] = summary[:4000]
    return fields


def next_slots(*, meeting_type: str, count: int = SLOT_COUNT) -> list[PublicGuideSlot]:
    now = datetime.now(GUIDE_TZ)
    cursor = now + timedelta(hours=1)
    if cursor.minute < 30:
        cursor = cursor.replace(minute=30, second=0, microsecond=0)
    else:
        cursor = (cursor + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    slots: list[PublicGuideSlot] = []
    guard = 0
    while len(slots) < count and guard < 400:
        guard += 1
        if cursor.weekday() < 5 and cursor.hour in SLOT_HOURS:
            if cursor > now:
                end = cursor + timedelta(minutes=30)
                try:
                    label = cursor.strftime("%a %b %-d · %-I:%M %p")
                except ValueError:
                    label = cursor.strftime("%a %b %d · %I:%M %p")
                slots.append(
                    PublicGuideSlot(
                        start=cursor.astimezone(UTC),
                        end=end.astimezone(UTC),
                        label=label,
                        meeting_type=meeting_type,
                    )
                )
        cursor += timedelta(minutes=30)
    return slots
