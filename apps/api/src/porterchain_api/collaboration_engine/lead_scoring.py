"""Predictive lead score blend — empirical channel/intent priors + heuristic fallback.

Trains (online, no sklearn) from won/lost outcomes:
  positive = status=converted OR decision_status=converted
  negative = status=unqualified OR decision_status=lost

When fewer than MIN_SAMPLES labeled leads exist, callers get pure heuristic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmLead

logger = logging.getLogger(__name__)

MIN_SAMPLES = 20
HEURISTIC_WEIGHT = 0.65
PREDICTIVE_WEIGHT = 0.35
_PRIOR_TTL_SEC = 300.0

_cache_at: float = 0.0
_cache_priors: "ScorePriors | None" = None


@dataclass(frozen=True)
class ScorePriors:
    by_channel: dict[str, float] = field(default_factory=dict)
    by_intent: dict[str, float] = field(default_factory=dict)
    by_source: dict[str, float] = field(default_factory=dict)
    global_rate: float = 0.5
    sample_n: int = 0

    @property
    def ready(self) -> bool:
        return self.sample_n >= MIN_SAMPLES


def _laplace(wins: int, total: int) -> float:
    return (wins + 1.0) / (total + 2.0)


def _rate_map(rows: list[tuple[str | None, int, int]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, wins, total in rows:
        k = (key or "").strip() or "unknown"
        if total <= 0:
            continue
        out[k] = _laplace(wins, total)
    return out


def compute_score_priors(db: Session) -> ScorePriors:
    """Aggregate labeled CrmLead rows into conversion-rate priors."""
    leads = (
        db.query(
            CrmLead.channel,
            CrmLead.intent_type,
            CrmLead.source,
            CrmLead.status,
            CrmLead.decision_status,
        )
        .filter(
            (CrmLead.status.in_(("converted", "unqualified")))
            | (CrmLead.decision_status.in_(("converted", "lost")))
        )
        .all()
    )

    ch_w: dict[str, int] = {}
    ch_t: dict[str, int] = {}
    in_w: dict[str, int] = {}
    in_t: dict[str, int] = {}
    src_w: dict[str, int] = {}
    src_t: dict[str, int] = {}
    wins = 0
    total = 0

    for channel, intent_type, source, status, decision_status in leads:
        pos = status == "converted" or decision_status == "converted"
        neg = status == "unqualified" or decision_status == "lost"
        if not pos and not neg:
            continue
        total += 1
        if pos:
            wins += 1
        ck = (channel or "unknown").strip() or "unknown"
        ik = (intent_type or "unknown").strip() or "unknown"
        sk = (source or "unknown").strip() or "unknown"
        ch_t[ck] = ch_t.get(ck, 0) + 1
        in_t[ik] = in_t.get(ik, 0) + 1
        src_t[sk] = src_t.get(sk, 0) + 1
        if pos:
            ch_w[ck] = ch_w.get(ck, 0) + 1
            in_w[ik] = in_w.get(ik, 0) + 1
            src_w[sk] = src_w.get(sk, 0) + 1

    return ScorePriors(
        by_channel=_rate_map([(k, ch_w.get(k, 0), ch_t[k]) for k in ch_t]),
        by_intent=_rate_map([(k, in_w.get(k, 0), in_t[k]) for k in in_t]),
        by_source=_rate_map([(k, src_w.get(k, 0), src_t[k]) for k in src_t]),
        global_rate=_laplace(wins, total) if total else 0.5,
        sample_n=total,
    )


def get_score_priors(db: Session | None, *, force: bool = False) -> ScorePriors | None:
    global _cache_at, _cache_priors
    if db is None:
        return _cache_priors if _cache_priors and _cache_priors.ready else None
    now = time.monotonic()
    if not force and _cache_priors is not None and (now - _cache_at) < _PRIOR_TTL_SEC:
        return _cache_priors if _cache_priors.ready else None
    try:
        priors = compute_score_priors(db)
    except Exception:
        logger.exception("lead_score_priors_failed")
        return _cache_priors if _cache_priors and _cache_priors.ready else None
    _cache_priors = priors
    _cache_at = now
    return priors if priors.ready else None


def clear_score_priors_cache() -> None:
    global _cache_at, _cache_priors
    _cache_at = 0.0
    _cache_priors = None


def _contact_completeness(lead: CrmLead) -> float:
    bits = 0
    if lead.email:
        bits += 1
    if lead.phone:
        bits += 1
    if lead.company_name:
        bits += 1
    if lead.primary_contact_name:
        bits += 1
    return bits / 4.0


def predictive_score(lead: CrmLead, priors: ScorePriors) -> float:
    """0–100 predictive component from empirical priors + contact completeness."""
    ch = (getattr(lead, "channel", None) or "unknown").strip() or "unknown"
    intent = (lead.intent_type or "unknown").strip() or "unknown"
    source = (lead.source or "unknown").strip() or "unknown"
    ch_r = priors.by_channel.get(ch, priors.global_rate)
    in_r = priors.by_intent.get(intent, priors.global_rate)
    src_r = priors.by_source.get(source, priors.global_rate)
    contact = _contact_completeness(lead)
    rate = 0.4 * ch_r + 0.3 * in_r + 0.2 * src_r + 0.1 * contact
    return max(0.0, min(100.0, 100.0 * rate))


def blend_scores(heuristic: int, predictive: float | None) -> int:
    """Blend heuristic with predictive; fall back to heuristic when no model."""
    h = max(0, min(100, int(heuristic)))
    if predictive is None:
        return h
    blended = HEURISTIC_WEIGHT * h + PREDICTIVE_WEIGHT * float(predictive)
    return max(0, min(100, int(round(blended))))


def score_breakdown(
    lead: CrmLead,
    heuristic: int,
    *,
    db: Session | None = None,
    priors: ScorePriors | None = None,
) -> dict[str, Any]:
    p = priors if priors is not None else get_score_priors(db)
    pred = predictive_score(lead, p) if p and p.ready else None
    final = blend_scores(heuristic, pred)
    return {
        "heuristic": max(0, min(100, int(heuristic))),
        "predictive": None if pred is None else round(pred, 2),
        "final": final,
        "method": "blend" if pred is not None else "heuristic",
        "priors_n": p.sample_n if p else 0,
    }


__all__ = [
    "MIN_SAMPLES",
    "ScorePriors",
    "blend_scores",
    "clear_score_priors_cache",
    "compute_score_priors",
    "get_score_priors",
    "predictive_score",
    "score_breakdown",
]
