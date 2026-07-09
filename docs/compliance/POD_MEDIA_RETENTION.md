# POD media storage & retention (DD-32 · B.17)

**Type:** CANONICAL  
**Checklist:** B.17  
**Last verified:** 2026-07-09

## Current behavior (Phase 1)

| Surface              | Storage                                     | Retention            |
| -------------------- | ------------------------------------------- | -------------------- |
| Driver POD photo URL | `DriverStopMeta.meta` + order timeline      | DB until order purge |
| Signature / barcode  | Same meta blob (truncated signature)        | Same                 |
| Fleetbase sync       | `fleetbase_bridge.upload_pod_*` when linked | Vendor retention     |

POD capture API: `POST /v1/driver/routes/{route_id}/stops/{stop_id}/pod-photo` → `ProofOfDeliveryService.capture_photo`.

## Phase 2 target (prod CDN)

1. Upload to object storage (GCS/S3) with signed PUT from driver app
2. Store CDN URL only in `DriverStopMeta` — never raw binary in Postgres
3. Retention: **7 years** for dispute/insurance (align with claims export)
4. Lifecycle rule: move to cold storage after 90 days

## Dev verification

```bash
pnpm validate:pod-media
```

## Security

- Driver must own stop (`order.assigned_driver_id`)
- Merchant/admin POD gallery reads via `merchant_engine` / admin ops — tenant-scoped
