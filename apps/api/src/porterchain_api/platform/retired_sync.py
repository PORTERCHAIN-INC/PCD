"""Placeholders for the Fleetbase sync that was removed. Callers get an empty result."""

from __future__ import annotations

from typing import Any


class _Quiet:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def __getattr__(self, _name: str) -> Any:
        def _no(*_args: Any, **_kwargs: Any) -> None:
            return None

        return _no


class BookingSyncService(_Quiet):
    def process_retry_queue(self, *_args: Any, **_kwargs: Any) -> dict[str, int]:
        return {"processed": 0, "failed": 0, "skipped": 0}

    def push_order(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class RetryQueue(_Quiet):
    @staticmethod
    def enqueue(*_args: Any, **_kwargs: Any) -> None:
        return None

    @staticmethod
    def stats(_db: Any = None) -> dict[str, int]:
        return {"pending": 0, "retrying": 0, "dead": 0, "done": 0}

    @staticmethod
    def claim_due(*_args: Any, **_kwargs: Any) -> list[Any]:
        return []

    @staticmethod
    def mark_done(*_args: Any, **_kwargs: Any) -> None:
        return None

    @staticmethod
    def mark_failed(*_args: Any, **_kwargs: Any) -> None:
        return None


class ErrorQueue(RetryQueue):
    @staticmethod
    def list_dead(*_args: Any, **_kwargs: Any) -> list[Any]:
        return []

    @staticmethod
    def requeue(*_args: Any, **_kwargs: Any) -> None:
        return None


class WebhookIngressService(_Quiet):
    pass


class WebhookProcessor(_Quiet):
    pass


SLO_TARGET_PCT = 0


def _find_inflight(*_args: Any, **_kwargs: Any) -> None:
    return None


def assess_fleetbase_sync(_db: Any, _settings: Any) -> dict[str, Any]:
    return {
        "status": "removed",
        "ok": True,
        "bridge_enabled": False,
        "meets_slo": True,
        "eligible_orders": 0,
        "linked_orders": 0,
        "link_pct": 100.0,
        "dead_letters": 0,
        "pending": 0,
        "pending_jobs": 0,
        "target_pct": 0,
        "slo_target_pct": 0,
        "alerts": [],
    }


def build_fleetbase_sync_alerts(_slo: dict[str, Any]) -> list[dict[str, str]]:
    return []
