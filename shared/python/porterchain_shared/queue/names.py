"""Async job queue names — Redis-backed workers consume these queues."""

from enum import StrEnum


class QueueName(StrEnum):
    EMAILS = "emails"
    SMS = "sms"
    PUSH = "push"
    DISPATCH = "dispatch"
    ROUTING = "routing"
    BILLING = "billing"
    REPORTS = "reports"
    WEBHOOKS = "webhooks"

    @property
    def redis_key(self) -> str:
        return f"porterchain:queue:{self.value}"
