"""Phase 10 — cutover is manual docs only; agents must not mutate prod."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def test_phase10_cutover_runbook_exists() -> None:
    path = REPO / "docs" / "runbooks" / "clerk-cutover-phase10.md"
    assert path.is_file(), "Phase 10 cutover runbook missing"


def test_phase10_runbook_forbids_agent_prod_mutation() -> None:
    text = (REPO / "docs" / "runbooks" / "clerk-cutover-phase10.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "do not execute from cursor agents" in lower or "do **not** execute from cursor agents" in lower
    assert "upload-clerk-to-doppler" in lower
    assert "retirement" in lower
    assert "rollback" in lower
    assert "no production" in lower or "were changed or deleted" in lower


def test_phase10_main_runbook_still_manual() -> None:
    text = (REPO / "docs" / "runbooks" / "clerk-consolidation.md").read_text(encoding="utf-8")
    assert "do **not** execute production cutover from agents" in text.lower() or "do not execute production cutover from agents" in text.lower()
    assert "clerk-cutover-phase10.md" in text or "Phase 10" in text


def test_phase10_does_not_ship_prod_mutation_scripts_as_default() -> None:
    """Identity tooling defaults remain dry-run; apply requires explicit confirm token."""
    migrate = (REPO / "apps" / "api" / "scripts" / "identity_migrate.py").read_text(encoding="utf-8")
    assert "--confirm" in migrate
    assert "APPLY" in migrate
    backfill = (REPO / "apps" / "api" / "src" / "porterchain_api" / "auth" / "identity_fk_backfill.py").read_text(
        encoding="utf-8"
    )
    assert "dry_run" in backfill
