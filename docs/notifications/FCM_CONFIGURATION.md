# FCM Configuration

**Type:** CANONICAL
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**See also:** [NOTIFICATION_ARCHITECTURE.md](./NOTIFICATION_ARCHITECTURE.md) · [DEVICE_REGISTRATION_FLOW.md](./DEVICE_REGISTRATION_FLOW.md)

Firebase Cloud Messaging — server-side only via Notification Engine (`fcm_service.py`).

---

## Overview

Porterchain uses **Firebase Admin SDK** (`firebase-admin`) inside the Notification Engine. Client apps obtain FCM tokens; the API never exposes service account credentials to browsers or mobile clients.

## Supported Platforms

| Platform | Client                                   | Token registration                        |
| -------- | ---------------------------------------- | ----------------------------------------- |
| Android  | Driver mobile (Expo)                     | `POST /v1/notifications/devices/register` |
| iOS      | Driver / customer mobile (Expo)          | Same                                      |
| Web Push | Admin / merchant / customer (when wired) | Same + VAPID                              |

Push resolves tokens from `notification_devices` when no explicit token is passed in the delivery payload.

## Environment Variables

| Variable                    | Required   | Description                                  |
| --------------------------- | ---------- | -------------------------------------------- |
| `FIREBASE_PROJECT_ID`       | Yes (prod) | GCP Firebase project ID                      |
| `FIREBASE_CREDENTIALS_JSON` | Yes (prod) | Service account JSON inline                  |
| `FIREBASE_CREDENTIALS_PATH` | Alt        | Path to service account file                 |
| `FIREBASE_WEB_VAPID_KEY`    | Web push   | VAPID public key for browser clients         |
| `PORTERCHAIN_PUSH_ENABLED`  | Yes        | Master toggle — when false, push is log-only |
| `PORTERCHAIN_PUSH_SEND`     | Yes        | When false, validate but do not call FCM     |

Aliases in `porterchain_shared/config/settings.py`: `push_enabled`, `push_send`.

## Service Account Setup

1. GCP Console → Firebase project → Project settings → Service accounts
2. Generate new private key (JSON)
3. Grant **Firebase Cloud Messaging Admin** role
4. Store JSON in secret manager or mount at `FIREBASE_CREDENTIALS_PATH`
5. Never commit JSON to git

## Code Touchpoints

| File                                                  | Role                                                          |
| ----------------------------------------------------- | ------------------------------------------------------------- |
| `notification_engine/fcm_service.py`                  | Initialize Admin SDK, send to token(s), invalidate bad tokens |
| `notification_engine/delivery_service.py`             | Calls FCMService for `channel=push`                           |
| `notification_engine/device_service.py`               | Token storage and invalidation                                |
| `shared/python/porterchain_shared/config/settings.py` | Reads env vars                                                |

## Security

- Service account credentials server-only (API + worker)
- Invalid tokens removed on FCM `registration-token-not-registered` / `invalid-argument`
- RBAC on admin device-token views (`/v1/admin/notifications/devices`)
- Audit every push in `notification_records` + `notification_delivery_logs`

## Local Development

Without credentials or with `PORTERCHAIN_PUSH_SEND=false`, push runs in **log-only mode**:

```
push (log-only): token=ExponentPush… title=Driver assigned
```

## Verification Checklist

- [ ] `FIREBASE_PROJECT_ID` set in API + worker
- [ ] Service account JSON accessible
- [ ] `PORTERCHAIN_PUSH_ENABLED=true` in staging/prod
- [ ] Device registers via `POST /v1/notifications/devices/register`
- [ ] Test push appears on physical device
- [ ] Invalid token removed from `notification_devices`

---

## Governance

| Document                                         | Role              |
| ------------------------------------------------ | ----------------- |
| [masterrule.md](../../masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../../CTO_AUDIT_REPORT.md) | Doc vs code audit |
