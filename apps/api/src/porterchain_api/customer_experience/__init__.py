"""Recipient ("customer") experience: branded tracking, proactive notifications,
self-scheduling / reschedule / instructions and the failed-delivery policy.

Lives outside the ``*_engine`` packages on purpose: it composes booking,
merchant, notification and pricing pieces without adding engine-to-engine coupling.
Every customer-facing behaviour is off by default (per-merchant settings).
"""
