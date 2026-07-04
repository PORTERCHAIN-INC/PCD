# Reverse Logistics Report

Generated: 2026-07-02T20:51:20.327203+00:00

**Overall:** PASS

| Step             | Status  | Layer            | Root Cause | Fix | Priority |
| ---------------- | ------- | ---------------- | ---------- | --- | -------- |
| Delivered        | ✅ PASS | admin_engine     | —          | —   | P3       |
| Customer Rejects | ✅ PASS | admin_engine     | —          | —   | P3       |
| Return Requested | ✅ PASS | admin_engine     | —          | —   | P3       |
| Return Approved  | ✅ PASS | admin_engine     | —          | —   | P3       |
| Driver Assigned  | ✅ PASS | fleetbase_engine | —          | —   | P3       |
| Return Pickup    | ✅ PASS | admin_engine     | —          | —   | P3       |
| Warehouse        | ✅ PASS | operations       | —          | —   | P3       |
| Merchant         | ✅ PASS | merchant_engine  | —          | —   | P3       |
| Refund           | ✅ PASS | billing_engine   | —          | —   | P3       |
| Return Completed | ✅ PASS | admin_engine     | —          | —   | P3       |

## Exception scenarios

- customer_refused: **PASS**
- wrong_address: **PASS**
- damaged_parcel: **PASS**
- lost_parcel: **PASS**
- wrong_parcel: **PASS**
- merchant_recall: **PASS**
