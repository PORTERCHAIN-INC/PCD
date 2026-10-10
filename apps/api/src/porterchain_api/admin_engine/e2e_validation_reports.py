"""E2E validation — phase 10 report generation."""

from __future__ import annotations

from typing import Any

from porterchain_api.admin_engine.e2e_validation_helpers import _now_iso
from porterchain_api.config import Settings


class E2EValidationReportsMixin:
    def generate_reports(
        self,
        phases: dict[str, Any],
        settings: Settings,
        auto_fixes: list[dict[str, str]],
    ) -> dict[str, str]:
        summary = self._summarize(phases)
        day_plan = phases.get("phase_1_system_layer", {}).get("day_plan_probe", {}) or {}

        return {
            "SYSTEM_VALIDATION_REPORT.md": self._md_system(phases.get("phase_1_system_layer", {}), summary, auto_fixes),
            "FORWARD_LOGISTICS_REPORT.md": self._md_steps("Forward Logistics", phases.get("phase_2_forward_logistics", {})),
            "REVERSE_LOGISTICS_REPORT.md": self._md_reverse(phases.get("phase_4_reverse_logistics", {})),
            "FAILURE_SCENARIOS_REPORT.md": self._md_failures(phases.get("phase_5_failures", {})),
            "EVENT_BUS_REPORT.md": self._md_events(phases.get("phase_6_event_bus", {})),
            "NOTIFICATION_REPORT.md": self._md_notifications(phases.get("phase_7_notifications", {})),
            "DAY_PLAN_REPORT.md": self._md_day_plan(day_plan),
            "DATA_CONSISTENCY_REPORT.md": self._md_consistency(phases.get("phase_8_consistency", {})),
            "API_TRACE_REPORT.md": self._md_trace(phases.get("phase_9_observability", {})),
            "PRODUCTION_READINESS_REPORT.md": self._md_readiness(summary, phases, settings, auto_fixes),
        }

    def _md_header(self, title: str) -> list[str]:
        return [f"# {title}", "", f"Generated: {_now_iso()}", ""]

    def _md_step_table(self, steps: list[dict[str, Any]]) -> list[str]:
        lines = [
            "| Step | Status | Layer | Root Cause | Fix | Priority |",
            "|------|--------|-------|------------|-----|----------|",
        ]
        for s in steps:
            icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "BLOCKER": "🛑"}.get(s.get("status", ""), "○")
            lines.append(
                f"| {s.get('step', s.get('scenario', s.get('event', '—')))} | {icon} {s.get('status')} | "
                f"{s.get('layer', '—')} | {s.get('root_cause', '—') or '—'} | "
                f"{s.get('recommended_fix', '—') or '—'} | {s.get('priority', '—') or '—'} |"
            )
        return lines

    def _md_system(self, phase: dict, summary: dict, auto_fixes: list) -> str:
        lines = self._md_header("System Validation Report")
        lines.append(f"**Overall:** {phase.get('overall', '—')}")
        lines.append("")
        lines.append("## Connection chain (masterrule §1)")
        for c in phase.get("connections", []):
            lines.append(f"- {c.get('label')}: **{c.get('status')}**")
        lines.append("")
        lines.append("## Auto-fixes applied")
        for f in auto_fixes:
            lines.append(f"- {f.get('fix')}: {f.get('action')} ({f.get('applied')})")
        lines.append("")
        lines.append(f"## Summary: pass={summary.get('pass')} warning={summary.get('warning')} fail={summary.get('fails')} blocker={summary.get('blockers')}")
        return "\n".join(lines)

    def _md_steps(self, title: str, phase: dict) -> str:
        lines = self._md_header(f"{title} Report")
        lines.append(f"**Overall:** {phase.get('overall', '—')}")
        lines.append("")
        lines.extend(self._md_step_table(phase.get("steps", [])))
        return "\n".join(lines)

    def _md_reverse(self, phase: dict) -> str:
        lines = self._md_header("Reverse Logistics Report")
        lines.append(f"**Overall:** {phase.get('overall', '—')}")
        lines.append("")
        lines.extend(self._md_step_table(phase.get("steps", [])))
        if phase.get("exception_scenarios"):
            lines.append("")
            lines.append("## Exception scenarios")
            for ex in phase["exception_scenarios"]:
                lines.append(f"- {ex['scenario']}: **{ex['status']}**")
        return "\n".join(lines)

    def _md_failures(self, phase: dict) -> str:
        lines = self._md_header("Failure Scenarios Report")
        lines.append(f"**Overall:** {phase.get('overall', '—')}")
        lines.append("")
        lines.extend(self._md_step_table(phase.get("scenarios", [])))
        return "\n".join(lines)

    def _md_events(self, phase: dict) -> str:
        lines = self._md_header("Event Bus Report")
        lines.append(f"**Overall:** {phase.get('overall', '—')}")
        lines.append("")
        lines.extend(self._md_step_table(phase.get("events", [])))
        return "\n".join(lines)

    def _md_notifications(self, phase: dict) -> str:
        lines = self._md_header("Notification Report")
        lines.append(f"**Overall:** {phase.get('overall', '—')}")
        lines.append("")
        for a in phase.get("audiences", []):
            lines.append(f"- **{a['audience']}**: {a['status']} (total={a['total']}, failed={a['failed']})")
        return "\n".join(lines)

    def _md_day_plan(self, plan: dict) -> str:
        lines = self._md_header("Day Plan Report")
        lines.append(f"- Engine: {plan.get('engine', 'porterchain')}")
        lines.append(f"- Solver: {plan.get('solver', 'ortools')}")
        lines.append(f"- Road cost: {plan.get('road_cost', 'valhalla')}")
        lines.append(f"- Pending runs: {plan.get('pending_runs', 0)}")
        lines.append(f"- Ready runs: {plan.get('ready_runs', 0)}")
        lines.append(f"- Failed runs: {plan.get('failed_runs', 0)}")
        return "\n".join(lines)

    def _md_consistency(self, phase: dict) -> str:
        lines = self._md_header("Data Consistency Report")
        lines.append(f"**Overall:** {phase.get('overall', '—')}")
        lines.append(f"**Synchronized:** {phase.get('synchronized', False)}")
        lines.append("")
        for s in phase.get("surfaces", []):
            lines.append(f"- {s['surface']}: **{s['status']}** — {s.get('note') or 'OK'}")
        return "\n".join(lines)

    def _md_trace(self, phase: dict) -> str:
        lines = self._md_header("API Trace Report")
        corr = phase.get("correlation", {})
        lines.append(f"Order ID: `{corr.get('order_id')}`")
        lines.append(f"Tracking: `{corr.get('tracking_number')}`")
        lines.append(f"Reference: `{corr.get('reference_number')}`")
        lines.append("")
        lines.append("## Execution timeline")
        for item in phase.get("timeline", [])[:80]:
            lines.append(f"- [{item.get('at', '—')}] {item.get('kind', item.get('type'))}: {item.get('name', item.get('name', ''))} — {item.get('status', item.get('to', ''))}")
        return "\n".join(lines)

    def _md_readiness(self, summary: dict, phases: dict, settings: Settings, auto_fixes: list) -> str:
        score = 100
        score -= summary.get("blockers", 0) * 15
        score -= summary.get("fails", 0) * 8
        score -= summary.get("warning", 0) * 2
        score = max(0, min(100, score))
        grade = "Production Ready" if score >= 90 and summary.get("blockers", 0) == 0 else (
            "Needs Attention" if score >= 70 else "Not Ready"
        )
        critical_forward = phases.get("phase_2_forward_logistics", {})
        critical_status = critical_forward.get("overall", "FAIL")
        critical_pass = critical_status in ("PASS", "WARNING")
        lines = self._md_header("Production Readiness Report")
        lines.append(f"**Score: {score}/100** — {grade}")
        lines.append(
            f"**Critical forward logistics:** {'COMPLETE' if critical_pass else 'INCOMPLETE'} ({critical_status})"
        )
        lines.append("")
        lines.append("## Phase results")
        for key, phase in phases.items():
            lines.append(f"- {phase.get('name', key)}: **{phase.get('overall', '—')}**")
        lines.append("")
        lines.append("## Masterrule compliance")
        lines.append("- Architecture topology: locked (§1)")
        lines.append(f"- Dispatch engine: {settings.dispatch_engine or 'porterchain'} (OR-Tools day plan)")
        lines.append(f"- Stripe webhook signal: {'mock' if settings.stripe_mock else 'live'}")
        lines.append("")
        lines.append(
            f"Platform passes only when all critical workflows complete: "
            f"**{'YES' if grade == 'Production Ready' and critical_pass and summary.get('blockers', 0) == 0 else 'NO'}**"
        )
        return "\n".join(lines)
