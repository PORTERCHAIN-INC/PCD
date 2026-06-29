"""Driver performance metrics."""

from __future__ import annotations

from typing import Any


class PerformanceService:
    def score(self, driver: Any) -> float:
        perf = driver.performance or {}
        if "score" in perf:
            return float(perf["score"])
        on_time = float(perf.get("on_time_percent", 95.0))
        completion = float(perf.get("completion_percent", 98.0))
        rating_factor = (driver.rating or 4.8) / 5.0 * 100
        return round((on_time * 0.4 + completion * 0.4 + rating_factor * 0.2), 1)

    def summary(self, driver: Any) -> dict:
        perf = driver.performance or {}
        return {
            "score": self.score(driver),
            "on_time_percent": perf.get("on_time_percent", 95.0),
            "completion_percent": perf.get("completion_percent", 98.0),
            "deliveries_total": perf.get("deliveries_total", 0),
            "deliveries_today": perf.get("deliveries_today", 0),
            "acceptance_rate": perf.get("acceptance_rate", 100.0),
            "rating": driver.rating,
        }
