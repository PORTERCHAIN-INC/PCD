"""Rules-based triage of an inbound message (email / WhatsApp / form text).

Deterministic and local: no data leaves the server. Extracts what pricing needs
(postal codes, parcel count, vehicle) and labels the intent so the inbox can
sort and the draft can answer the right question.
"""

from __future__ import annotations

import re
from typing import Any

_POSTAL = re.compile(r"\b([ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z])\s?(\d[ABCEGHJ-NPRSTV-Z]\d)?\b", re.IGNORECASE)
_PARCELS = re.compile(r"\b(\d{1,4})\s*(?:x\s*)?(parcels?|packages?|boxes|box|pallets?|orders?|deliveries|drops|stops)\b", re.IGNORECASE)
_VEHICLES = (
    ("box_16", ("box truck", "16 ft", "16ft", "cube truck", "pallet")),
    ("cargo_van", ("cargo van", "van", "sprinter")),
    ("sedan_suv", ("car", "sedan", "suv", "small parcel", "envelope")),
)
_INTENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("auto_reply", ("out of office", "out of the office", "auto-reply", "automatic reply", "vacation")),
    ("not_interested", ("not interested", "unsubscribe", "stop messaging", "remove me", "no thanks")),
    ("price_objection", ("too expensive", "cheaper", "lower price", "better rate", "discount")),
    ("ready_to_book", ("book", "schedule a pickup", "today", "asap", "urgent", "right now", "tomorrow")),
    ("quote_request", ("quote", "price", "pricing", "how much", "cost", "rate", "estimate")),
    ("question", ("?", "do you", "can you", "is it possible", "what is", "how do")),
)
URGENT_INTENTS = {"ready_to_book", "quote_request"}


def triage(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    low = t.lower()
    intent = "general"
    for name, words in _INTENTS:
        if any(w in low for w in words):
            intent = name
            break
    fsas = []
    for m in _POSTAL.finditer(t):
        code = m.group(1).upper()
        if code not in fsas:
            fsas.append(code)
    parcels = None
    m = _PARCELS.search(t)
    if m:
        parcels = max(1, min(int(m.group(1)), 500))
    vehicle = None
    for vid, words in _VEHICLES:
        if any(re.search(rf"\b{re.escape(w)}\b", low) for w in words):
            vehicle = vid
            break
    return {
        "intent": intent,
        "pickup_fsa": fsas[0] if fsas else None,
        "dropoff_fsa": fsas[1] if len(fsas) > 1 else None,
        "parcel_count": parcels,
        "vehicle_class": vehicle,
        "urgent": intent in URGENT_INTENTS,
    }
