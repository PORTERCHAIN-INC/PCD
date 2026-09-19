"""Driver ratings & feedback."""

from __future__ import annotations

from typing import Any


class RatingsService:
    def summary(self, driver: Any) -> dict:
        perf = driver.performance or {}
        return {
            "rating": driver.rating or 5.0,
            "total_reviews": perf.get("total_reviews", 0),
            "five_star_percent": perf.get("five_star_percent", 100.0),
            "recent_feedback": perf.get("recent_feedback", []),
        }
