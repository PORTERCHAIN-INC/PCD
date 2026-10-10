"""Intelligence engine boundary — Phase 2 scaffold only."""

from __future__ import annotations

from unittest.mock import MagicMock

from porterchain_api.intelligence_engine import (
    PHASE2_BOUNDARY,
    phase2_intelligence_enabled,
)
from porterchain_api.intelligence_engine.enrichers import (
    explain_dispatch_rationale,
    paraphrase_merchant_actions,
    polish_message_draft,
)


def test_phase2_boundary_default_off() -> None:
    assert PHASE2_BOUNDARY == "intelligence_engine"
    assert phase2_intelligence_enabled({}) is False
    assert phase2_intelligence_enabled({"crm": True}) is False


def test_phase2_boundary_flags() -> None:
    assert phase2_intelligence_enabled({"intelligence": True}) is True
    assert phase2_intelligence_enabled({"ai_dispatch": True}) is True


def test_enrichers_fail_soft_when_phase2_off() -> None:
    insights = {
        "risk_score": "low",
        "payment_risk": "low",
        "renewal_risk": "low",
        "revenue_trend": "up",
        "suggested_actions": ["Follow up on overdue invoices to reduce payment risk."],
    }
    out = paraphrase_merchant_actions(insights, flags={}, db=None)
    assert out["actions_source"] == "heuristic"
    assert out["suggested_actions"] == insights["suggested_actions"]

    draft = polish_message_draft(
        sms="PorterChain update: TRK is Booked.",
        email_body="Hello,\n\nYour shipment TRK is currently Booked.\n",
        tracking_number="TRK",
        state="BOOKED",
        flags={"intelligence": False},
        db=None,
    )
    assert draft["draft_source"] == "heuristic"
    assert draft["sms"].startswith("PorterChain update")

    assert explain_dispatch_rationale(["closest ETA"], flags={}, db=None) is None


def test_readonly_tools_reject_unknown_and_extract_merchant_id() -> None:
    from porterchain_api.intelligence_engine.tools import (
        READONLY_TOOL_NAMES,
        extract_merchant_id,
        get_manifest_summary,
        get_optimize_run,
        run_readonly_tool,
    )

    assert "get_sla_queue" in READONLY_TOOL_NAMES
    assert "get_optimize_run" in READONLY_TOOL_NAMES
    assert "get_manifest_summary" in READONLY_TOOL_NAMES
    assert "get_fsa_coverage" in READONLY_TOOL_NAMES
    assert "get_fuel_delta" in READONLY_TOOL_NAMES
    mid = "11111111-1111-1111-1111-111111111111"
    assert extract_merchant_id(f"Look at merchant_id: {mid} please") == mid
    unknown = run_readonly_tool("delete_order", db=None)  # type: ignore[arg-type]
    assert unknown["error"] == "unknown_or_forbidden_tool"
    assert get_optimize_run(None, "")["error"] == "run_id_required"  # type: ignore[arg-type]
    assert get_manifest_summary(None, "")["error"] == "driver_id_required"  # type: ignore[arg-type]
    from porterchain_api.intelligence_engine.tools import get_fsa_coverage

    cov = get_fsa_coverage(MagicMock(), "M5V")
    assert cov["in_gta150_tile"] is True
    assert cov["fsa"] == "M5V"
    out = get_fsa_coverage(MagicMock(), "K1A")
    assert out["ontario_district"] is True
    assert out["in_gta150_tile"] is False


def test_readonly_tools_and_usage_summary(db) -> None:
    from porterchain_api.intelligence_engine.tools import (
        gather_ops_tool_context,
        get_merchant_snapshot,
        get_sla_queue,
    )
    from porterchain_api.intelligence_engine.usage import (
        ai_usage_summary,
        record_ai_usage,
    )
    from porterchain_api.merchant_models import Merchant

    merchant = Merchant(company_name="Tool Co", email="tools@example.com", status="ACTIVE")
    db.add(merchant)
    db.flush()

    snap = get_merchant_snapshot(db, merchant.id)
    assert snap["tool"] == "get_merchant_snapshot"
    assert snap["company_name"] == "Tool Co"
    assert "outstanding_balance_cents" in snap

    missing = get_merchant_snapshot(db, "00000000-0000-0000-0000-000000000000")
    assert missing["error"] == "merchant_not_found"

    queue = get_sla_queue(db, limit=5)
    assert queue["tool"] == "get_sla_queue"
    assert "breached_count" in queue

    bundle = gather_ops_tool_context(db, merchant_id=merchant.id, include_sla_queue=True)
    assert len(bundle["results"]) == 2

    record_ai_usage(
        db,
        provider="nvidia_nim",
        model="meta/llama-3.2-11b-vision-instruct",
        feature="ops_copilot",
        prompt_tokens=10,
        completion_tokens=5,
        status="ok",
    )
    db.commit()
    summary = ai_usage_summary(db, limit=10)
    assert summary["nim"]["provider"] == "nvidia_nim"
    assert "phase2" in summary
    assert any(r["feature"] == "ops_copilot" for r in summary["recent"])

