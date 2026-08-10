# Order 360 — §5 audit scorecard

**Env:** local / staging / prod  
**Date:** YYYY-MM-DD  
**Auditor:**  
**Seed orders:** mid-flight `order_*` · `INVOICED` · `FAILED`

Mark each **Pass / Fail / Partial** with a one-line note.

## Entry points

| #                         | Result | Note |
| ------------------------- | ------ | ---- |
| E1 Open drawer from board |        |      |
| E2 Open drawer from queue |        |      |
| E3 Open drawer from table |        |      |
| E4 Open full page         |        |      |
| E5 Poll / refresh         |        |      |

## Drawer

| #                          | Result | Note |
| -------------------------- | ------ | ---- |
| D1 Details                 |        |      |
| D2 Timeline                |        |      |
| D3 POD gallery             |        |      |
| D4 Money (no fake hosts)   |        |      |
| D5 Care                    |        |      |
| D6 Assign modal            |        |      |
| D7 Exception + reason      |        |      |
| D8 Copy tracking           |        |      |
| D9 Route map               |        |      |
| D10 Open Fleetbase         |        |      |
| D11 Next-best-action       |        |      |
| D12 PC↔FB status chip      |        |      |
| Assist tab proposals       |        |      |
| Assist playbooks (confirm) |        |      |

## Full page quick actions

| #                        | Result | Note |
| ------------------------ | ------ | ---- |
| A1 Assign / Reassign     |        |      |
| A2 Cancel                |        |      |
| A6 Generate invoice      |        |      |
| A6b Resend receipt       |        |      |
| A9 Share tracking        |        |      |
| A10 Label / manifest PDF |        |      |
| Invoice PDF download     |        |      |

## Money + sync

| Check                                         | Result | Note |
| --------------------------------------------- | ------ | ---- |
| After POD → auto-invoice + Mailpit HTML       |        |      |
| Assign in 360 → Fleetbase same driver         |        |      |
| `fleetbase_order_id` is `order_*`             |        |      |
| Assist accept/reject logged in audit/timeline |        |      |

## Sign-off

**Release ready?** Yes / No  
**Blockers:**
