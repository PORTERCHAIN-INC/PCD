# FCM Configuration

> Firebase Cloud Messaging — server-side only via Notification Engine.

## Overview

Porterchain uses **Firebase Admin SDK** (`firebase-admin`) inside the Notification Engine. Client apps obtain FCM tokens; the API never exposes service account credentials.

## Supported Platforms

| Platform | Client                              | Token type             |
| -------- | ----------------------------------- | ---------------------- |
| Android  | Driver mobile (Expo)                | FCM registration token |
| iOS      | Driver mobile (Expo)                | APNs via FCM           |
| Web Push | Admin / Merchant / Customer portals | FCM web token + VAPID  |

## Environment Variables

| Variable                    | Required   | Description                                   |
| --------------------------- | ---------- | --------------------------------------------- |
| `FIREBASE_PROJECT_ID`       | Yes (prod) | GCP Firebase project ID                       |
| `FIREBASE_CREDENTIALS_JSON` | Yes (prod) | Service account JSON inline (worker/API)      |
| `FIREBASE_CREDENTIALS_PATH` | Alt        | Path to service account file (mounted volume) |
| `FIREBASE_WEB_VAPID_KEY`    | Web push   | VAPID public key for browser clients          |
| `PORTERCHAIN_PUSH_ENABLED`  | Yes        | Master toggle — when false, push is log-only  |
| `PORTERCHAIN_PUSH_SEND`     | Yes        | When false, validate but do not call FCM      |

## Service Account Setup

1. GCP Console → Firebase project → Project settings → Service accounts
2. Generate new private key (JSON)
3. Grant **Firebase Cloud Messaging Admin** role
4. Store JSON in secret manager or mount at `FIREBASE_CREDENTIALS_PATH`
5. Never commit JSON to git

## Docker / Fleetbase Storage

Production path (documented): `/fleetbase/api/storage/app/firebase/service-account.json`

Mount read-only into API and worker containers.

## Code Touchpoints

| File                                                  | Role                                   |
| ----------------------------------------------------- | -------------------------------------- |
| `notification_engine/fcm_service.py`                  | Initialize Admin SDK, send to token(s) |
| `notification_engine/delivery_service.py`             | Calls FCMService for `channel=push`    |
| `shared/python/porterchain_shared/config/settings.py` | Reads env vars                         |

## Security

- Service account credentials server-only
- Validate token format before storage
- Remove tokens on FCM `registration-token-not-registered` / `invalid-argument`
- RBAC on admin device-token views
- Audit every push in `notification_records`

## Local Development

Without credentials, push runs in **log-only mode**:

```
push (log-only): token=ExponentPush… title=Driver assigned
```

Set `PORTERCHAIN_PUSH_SEND=false` in local `.env` to suppress FCM calls entirely.

## Verification Checklist

- [ ] `FIREBASE_PROJECT_ID` set in API + worker
- [ ] Service account JSON accessible
- [ ] `PORTERCHAIN_PUSH_ENABLED=true` in staging/prod
- [ ] Device registers via `POST /v1/notifications/devices/register`
- [ ] Test push appears on physical device
- [ ] Invalid token removed from `notification_devices`
