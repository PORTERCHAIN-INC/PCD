"""Billing queue jobs — delegates to billing_engine."""

from __future__ import annotations

from typing import Any

from porterchain_api.billing_engine import process_billing_job


def process_billing(payload: dict[str, Any]) -> None:
    process_billing_job(payload)
