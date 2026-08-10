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


def test_phase10_identity_migrate_cli_deleted() -> None:
    """4→1 Clerk migration CLI retired after platform_driver cutover."""
    migrate = REPO / "apps" / "api" / "scripts" / "identity_migrate.py"
    assert not migrate.is_file()
    pkg = REPO / "apps" / "api" / "src" / "porterchain_api" / "auth" / "identity_migration"
    assert not pkg.is_dir()
    backfill = (
        REPO / "apps" / "api" / "src" / "porterchain_api" / "auth" / "identity_fk_backfill.py"
    ).read_text(encoding="utf-8")
    assert "dry_run" in backfill
