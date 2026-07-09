# Investor metrics cadence (§10.1 · INV-G2)

**Type:** CANONICAL  
**Checklist:** INV-G2  
**Last verified:** 2026-07-09

## Monthly rhythm

| When             | Action                                  | Owner         |
| ---------------- | --------------------------------------- | ------------- |
| 1st business day | Export snapshot JSON                    | CTO / finance |
| Same week        | Review vs Series A targets in deck      | CEO           |
| Quarterly        | Update `DECK_OUTLINE.md` traction slide | CEO + CTO     |

## Export command

```bash
cd apps/api && source .venv/bin/activate && PYTHONPATH=src python scripts/export_investor_snapshot.py
```

Writes `docs/investor/snapshots/YYYY-MM.json` (commit redacted summary to data room).

## Live API (ops dashboard)

```http
GET /v1/admin/investor-metrics
Authorization: Bearer <admin-token>
```

Returns the same structure as the monthly snapshot (`arr_cents`, `yoy_growth_multiplier`, `software_gross_margin_pct`, `icp_logos`, `acv_cents`, placeholders for NRR/CAC/burn).

## Targets (Series A)

| Metric                | Target | Source                              |
| --------------------- | ------ | ----------------------------------- |
| ARR                   | $1M+   | Trailing 30d order revenue × 12     |
| YoY growth            | 3×     | Year-over-year ARR proxy            |
| Software gross margin | ≥75%   | `margin_intelligence()`             |
| ICP logos             | ≥15    | `website/src/content/partners.json` |
| ACV                   | ≥$24k  | ARR / active merchants              |

## Review checklist

- [ ] Snapshot file committed for current month
- [ ] `GET /v1/admin/investor-metrics` matches snapshot `as_of`
- [ ] Gaps (NRR, CAC, burn) documented in investor deck footnotes
- [ ] Monopoly metrics (`/v1/admin/monopoly-metrics`) reviewed same session
