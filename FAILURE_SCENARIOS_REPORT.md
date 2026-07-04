# Failure Scenarios Report

Generated: 2026-07-02T20:51:20.327221+00:00

**Overall:** PASS

| Step | Status | Layer | Root Cause | Fix | Priority |
|------|--------|-------|------------|-----|----------|
| authentication_failed | ✅ PASS | auth | — | Configure Clerk or enable CLERK_DEV_BYPASS | P2 |
| payment_failed | ✅ PASS | operations | — | PaymentService records FAILED status + draft PAYMENT_FAILED | P2 |
| stripe_webhook_failure | ✅ PASS | billing_engine | — | Configure STRIPE_WEBHOOK_SECRET (ADR-006) | P2 |
| driver_rejects | ✅ PASS | operations | — | Verify retry/fallback path in operations | P2 |
| driver_cancels | ✅ PASS | operations | — | Handled via domain.states.ExceptionType + claims/ops queue | P2 |
| vehicle_breakdown | ✅ PASS | operations | — | Verify retry/fallback path in operations | P2 |
| driver_offline | ✅ PASS | operations | — | Handled via domain.states.ExceptionType + claims/ops queue | P2 |
| fleetbase_offline | ✅ PASS | fleetbase_adapter | — | Verify retry/fallback path in fleetbase_adapter | P2 |
| fleetbase_adapter_failure | ✅ PASS | fleetbase_adapter | — | Verify retry/fallback path in fleetbase_adapter | P2 |
| google_maps_failure | ✅ PASS | integrations | — | Verify retry/fallback path in integrations | P2 |
| osrm_failure | ✅ PASS | operations | — | Verify retry/fallback path in operations | P2 |
| valhalla_failure | ✅ PASS | operations | — | Verify retry/fallback path in operations | P2 |
| redis_restart | ✅ PASS | operations | — | Verify retry/fallback path in operations | P2 |
| postgresql_restart | ✅ PASS | operations | — | Verify retry/fallback path in operations | P2 |
| firebase_failure | ✅ PASS | operations | — | Verify retry/fallback path in operations | P2 |
| websocket_failure | ✅ PASS | operations | — | Verify retry/fallback path in operations | P2 |
| notification_failure | ✅ PASS | notification_engine | — | — | P2 |
| customer_cancels | ✅ PASS | operations | — | Handled via domain.states.ExceptionType + claims/ops queue | P2 |
| merchant_cancels | ✅ PASS | operations | — | Handled via domain.states.ExceptionType + claims/ops queue | P2 |
| pickup_failed | ✅ PASS | operations | — | Handled via domain.states.ExceptionType + claims/ops queue | P2 |
| delivery_failed | ✅ PASS | operations | — | Handled via domain.states.ExceptionType + claims/ops queue | P2 |
| customer_not_home | ✅ PASS | operations | — | Handled via domain.states.ExceptionType + claims/ops queue | P2 |
| otp_failed | ✅ PASS | operations | — | Handled via domain.states.ExceptionType + claims/ops queue | P2 |
| signature_failed | ✅ PASS | operations | — | Handled via domain.states.ExceptionType + claims/ops queue | P2 |
| photo_upload_failed | ✅ PASS | operations | — | Handled via domain.states.ExceptionType + claims/ops queue | P2 |
| pod_failed | ✅ PASS | operations | — | Handled via domain.states.ExceptionType + claims/ops queue | P2 |