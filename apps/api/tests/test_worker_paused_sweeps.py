"""WORKER_PAUSED_SWEEPS lets a local copy of live data run the worker without outbound backlog sweeps."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_RUN = Path(__file__).resolve().parents[2] / "worker" / "run.py"
_spec = importlib.util.spec_from_file_location("porterchain_worker_run", _RUN)
worker_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(worker_run)


def test_named_sweeps_are_skipped():
    active = {n for n, _ in worker_run.active_sweep_table("merchant_ops, lead_nurture,BLOG_SCHEDULED_PUBLISH")}
    assert {"merchant_ops", "lead_nurture", "blog_scheduled_publish"}.isdisjoint(active)
    assert "notification_retries" in active


def test_all_pauses_everything_and_empty_pauses_nothing():
    assert worker_run.active_sweep_table("all") == []
    assert len(worker_run.active_sweep_table("")) == len(worker_run.sweep_table())


def test_unknown_names_are_ignored(caplog):
    active = worker_run.active_sweep_table("no_such_sweep")
    assert len(active) == len(worker_run.sweep_table())
    assert "no_such_sweep" in caplog.text
