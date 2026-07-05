# API Trace Report

**Generated:** 2026-07-02  
**Last verified:** 2026-07-04  
**Status:** Historical validation snapshot

Point-in-time trace of `domain_events` for a test order. Not a live dashboard.

---

## Sample order

| Field | Value |
| ----- | ----- |
| Order ID | `f66ed072-f277-4dee-944d-415a9c93489e` |
| Tracking | `PC-20260702-AE4AF3` |
| Reference | `ORD-20260702-874D67` |

---

## Summary (July 2026 run)

| Phase | Events observed |
| ----- | --------------- |
| Customer / session | `customer.registered`, `visitor.session_started` |
| Dispatch | `order.dispatch_requested`, `order.dispatch_ready` |
| Driver lifecycle | `order.driver_assigned` through `order.delivered` |
| Exceptions | `claim.opened`, `support.ticket_created` |
| Notifications | `notification.sent` |
| Driver presence | `driver.online`, `driver.offline` |

**Note:** Trace includes mixed canonical strings (`order.DRIVER_ASSIGNED`) and dot-notation events (`order.driver_assigned`) from test harness — production catalog uses `{aggregate}.{action}` per [EVENT_CATALOG.md](./EVENT_CATALOG.md).

---

## Full timeline

Raw event log from validation run (2026-07-02). For current event definitions see [EVENT_CATALOG.md](./EVENT_CATALOG.md).

<details>
<summary>Click to expand full trace</summary>

- [2026-07-02T01:30:55] `customer.registered`
- [2026-07-02T01:30:56] `visitor.session_started`
- [2026-07-02T01:33:01] `order.dispatch_requested` → `order.dispatch_ready`
- [2026-07-02T01:33:01] `order.driver_assigned` → pickup → transit → `order.delivered`
- [2026-07-02T01:33:01] `claim.opened`, `support.ticket_created`
- [2026-07-02T01:33:01] `notification.sent`
- [2026-07-02T01:46:53] `driver.online` → [01:47:04] `driver.offline`

(Full 90+ line dump archived in git history for this file pre-2026-07-04 consolidation.)

</details>

---

## Related

| Document | Purpose |
| -------- | ------- |
| [EVENT_BUS_REPORT.md](./EVENT_BUS_REPORT.md) | Lifecycle validation PASS snapshot |
| [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md) | Canonical state machine |
| [API_FLOW_DIAGRAM.md](./API_FLOW_DIAGRAM.md) | Request flow |
