"""Delivery lanes: time-critical messages never wait behind digests or marketing.

fast   job offers, out for delivery, ETA / next stop, failed attempt, security codes.
       Own Redis queue, drained first and between every normal message.
normal everything else (booking, invoices, support...), per-channel queues as before.
slow   digests, marketing, nurture. Own queue, small budget per worker loop.

Lane only changes *which queue* a message waits in. The processor, payload and FCM
format are identical (driver job-offer push keeps its category and content).
"""

from __future__ import annotations

import random

FAST = "fast"
NORMAL = "normal"
SLOW = "slow"

FAST_TEMPLATES = frozenset(
    {
        "job_assigned",  # driver job offer (push, FCM category job_offer)
        "cx_out_for_delivery",
        "cx_eta",
        "cx_eta_20",
        "cx_next_stop",
        "cx_attempted",
        "cx_delivered",
        "delivery_failed",
        "near_delivery",
        "password_reset",
        "otp",
        "staff_activate",
        "staff_new_login",
        "notification_health_alert",
    }
)
SLOW_TEMPLATES = frozenset({"ops_daily_digest", "weekly_summary", "checkout_recovery", "lead_nurture"})
SLOW_CATEGORIES = frozenset({"marketing", "crm"})

#: p95 targets, event -> provider accepted (seconds). Alert when breached.
P95_TARGET_SEC = {FAST: 30, NORMAL: 120, SLOW: 900}
#: Max slow-lane messages per worker loop so a 10k digest burst can't hog a worker.
SLOW_BUDGET_PER_LOOP = 25


def lane_for(template: str | None, *, category: str | None = None, priority: str | None = None) -> str:
    if template in FAST_TEMPLATES or priority == "critical":
        return FAST
    if template in SLOW_TEMPLATES or (category in SLOW_CATEGORIES):
        return SLOW
    return NORMAL


def jittered(delay_sec: float, *, spread: float = 0.2, rng: random.Random | None = None) -> float:
    """Retry delay +/- spread (default 20%) so a provider outage doesn't retry in lockstep."""
    r = rng or random
    return max(1.0, delay_sec * (1 + r.uniform(-spread, spread)))
