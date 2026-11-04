"""Keycloak cutover (Clerk retirement) is a manual runbook; agents must not mutate prod."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
_RUNBOOK = REPO / "docs" / "runbooks" / "KEYCLOAK_CUTOVER.md"
_PHASE10 = REPO / "docs" / "archive" / "redundant-2026-08" / "clerk-cutover-phase10.md"


def test_phase10_cutover_runbook_exists() -> None:
    assert _RUNBOOK.is_file(), "Keycloak cutover runbook missing"


def test_phase10_runbook_forbids_agent_prod_mutation() -> None:
    lower = _RUNBOOK.read_text(encoding="utf-8").lower()
    assert "do **not** execute from cursor agents" in lower
    assert "migrate_clerk_users.py" in lower
    assert "pcd_subject_remap_csv" in lower
    assert "rollback" in lower
    assert "no production secrets were changed or deleted" in lower


def test_phase10_main_runbook_still_manual() -> None:
    text = _PHASE10.read_text(encoding="utf-8")
    assert "superseded" in text.lower() and "KEYCLOAK_CUTOVER.md" in text
