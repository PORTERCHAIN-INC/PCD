"""Commerce SLI counters — Shopify quote + AR pay (scraped via /metrics)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

# kind → result → count
_commerce_events: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
# quote_latency histogram buckets (ms) → count
_QUOTE_LATENCY_BOUNDS_MS = (25, 50, 100, 250, 500, 1000, 2500, 5000)
_quote_latency_bucket_counts: dict[str, int] = defaultdict(int)
_quote_latency_sum_ms: float = 0.0
_quote_latency_count: int = 0


def note_commerce_event(kind: str, result: str) -> None:
    k = (kind or "unknown").strip() or "unknown"
    r = (result or "unknown").strip() or "unknown"
    _commerce_events[k][r] += 1


def note_quote_latency(duration_ms: float) -> None:
    """Record CarrierService quote latency (ops-1 quote_latency)."""
    global _quote_latency_sum_ms, _quote_latency_count
    ms = max(0.0, float(duration_ms))
    _quote_latency_sum_ms += ms
    _quote_latency_count += 1
    label = "+Inf"
    for bound in _QUOTE_LATENCY_BOUNDS_MS:
        if ms <= bound:
            label = str(bound)
            break
    _quote_latency_bucket_counts[label] += 1
    # Also keep a coarse counter for dashboards that only scrape event totals.
    if ms <= 250:
        note_commerce_event("quote_latency", "fast_ms")
    elif ms <= 1000:
        note_commerce_event("quote_latency", "ok_ms")
    else:
        note_commerce_event("quote_latency", "slow_ms")


def note_ar_mismatch(reason: str) -> None:
    """Ops alert counter when invoice lines / quote / AR disagree."""
    note_commerce_event("ar_mismatch", (reason or "unknown").strip() or "unknown")


def check_invoice_detail_consistency(detail: dict[str, Any]) -> list[str]:
    """Return mismatch reasons (also increments metrics). Empty = OK."""
    reasons: list[str] = []
    amount = int(detail.get("amount_cents") or 0)
    lines = detail.get("lines") or []
    line_sum = sum(int(ln.get("amount_cents") or 0) for ln in lines if isinstance(ln, dict))
    reported = detail.get("lines_total_cents")
    if reported is not None:
        line_sum = int(reported)
    if lines and abs(line_sum - amount) > 0:
        reasons.append("line_vs_invoice")
        note_ar_mismatch("line_vs_invoice")
    for ln in lines:
        if not isinstance(ln, dict):
            continue
        rq = ln.get("rate_quote_cents")
        if rq is None:
            continue
        if int(rq) != int(ln.get("amount_cents") or 0):
            reasons.append("quote_vs_line")
            note_ar_mismatch("quote_vs_line")
            break
    return reasons


def prometheus_commerce_lines() -> list[str]:
    lines = [
        "# HELP porterchain_commerce_events_total Quote/pay/AR outcomes (process-local)",
        "# TYPE porterchain_commerce_events_total counter",
    ]
    for kind in sorted(_commerce_events):
        for result, value in sorted(_commerce_events[kind].items()):
            lines.append(
                f'porterchain_commerce_events_total{{kind="{kind}",result="{result}"}} {int(value)}'
            )
    lines.extend(
        [
            "# HELP porterchain_shopify_quote_latency_ms CarrierService quote latency",
            "# TYPE porterchain_shopify_quote_latency_ms histogram",
        ]
    )
    cumulative = 0
    for bound in _QUOTE_LATENCY_BOUNDS_MS:
        cumulative += int(_quote_latency_bucket_counts.get(str(bound), 0))
        lines.append(
            f'porterchain_shopify_quote_latency_ms_bucket{{le="{bound}"}} {cumulative}'
        )
    cumulative += int(_quote_latency_bucket_counts.get("+Inf", 0))
    lines.append(f'porterchain_shopify_quote_latency_ms_bucket{{le="+Inf"}} {cumulative}')
    lines.append(f"porterchain_shopify_quote_latency_ms_sum {_quote_latency_sum_ms:.3f}")
    lines.append(f"porterchain_shopify_quote_latency_ms_count {_quote_latency_count}")
    return lines


def reset_commerce_events_for_tests() -> None:
    global _quote_latency_sum_ms, _quote_latency_count
    _commerce_events.clear()
    _quote_latency_bucket_counts.clear()
    _quote_latency_sum_ms = 0.0
    _quote_latency_count = 0
