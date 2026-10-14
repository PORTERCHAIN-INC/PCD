"""The test-driver seed must import cleanly and refuse non-local databases."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "seed_online_drivers.py"


def _load():
    spec = importlib.util.spec_from_file_location("seed_online_drivers", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # import-time FK registration must not raise
    return mod


def _db(host: str):
    return SimpleNamespace(get_bind=lambda: SimpleNamespace(url=SimpleNamespace(host=host)))


def test_seed_imports_and_allows_local(monkeypatch) -> None:
    mod = _load()
    monkeypatch.delenv("SEED_ALLOW_REMOTE", raising=False)
    for host in ("localhost", "127.0.0.1", "postgres"):
        mod._require_local_db(_db(host))


def test_seed_refuses_remote(monkeypatch) -> None:
    mod = _load()
    monkeypatch.delenv("SEED_ALLOW_REMOTE", raising=False)
    with pytest.raises(SystemExit, match="refusing"):
        mod._require_local_db(_db("10.0.0.5"))
