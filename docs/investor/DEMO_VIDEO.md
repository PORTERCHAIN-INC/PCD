# 3-minute investor demo — recording guide

**Type:** CANONICAL  
**Checklist:** §10.2.2  
**Companion:** [WEBSITE_GTM_EXECUTION_PLAN.md](../WEBSITE_GTM_EXECUTION_PLAN.md) (5-minute spoken narrative)  
**Last verified:** 2026-07-09

Record a **≤3 minute** screen capture for the data room. Use the beats below; trim the 5-minute script to these timestamps.

---

## Pre-flight

```bash
pnpm install && pnpm db:migrate
pnpm dev:website & pnpm dev:admin & pnpm dev:merchant   # slice — not full turbo
pnpm validate:p0:fast
```

- Clerk dev bypass (`Bearer dev`) for admin + merchant portals.
- One completed booking with a live tracking number (website widget + Stripe test card `4242…`).

---

## Shot list (3:00)

| Time | Beat            | URL / surface                          | On-screen must-show                        |
| ---- | --------------- | -------------------------------------- | ------------------------------------------ |
| 0:00 | Positioning     | `localhost:3000` homepage              | Hero + “orchestration platform” copy       |
| 0:20 | Quote + book    | Homepage booking widget                | Instant quote → checkout → tracking number |
| 0:50 | Customer track  | `/track/{tracking}`                    | Map, route polyline, ETA panel             |
| 1:25 | Merchant portal | `localhost:3003` → order live tracking | Timeline + map layers                      |
| 1:55 | Admin ops       | `localhost:3004` live map / operations | Active drivers + in-flight orders          |
| 2:25 | Platform API    | `/developers` or footer Developers     | API docs link, webhooks, scoped keys       |
| 2:45 | Close           | Homepage                               | Logo + “Book a pilot” CTA                  |

**Voiceover (one line):** “Porterchain is the system of record for last-mile orchestration — quote, pay, dispatch, and live visibility in one platform.”

---

## Export checklist

| Step                                                              | Done |
| ----------------------------------------------------------------- | ---- |
| 1080p MP4, H.264, ≤50 MB                                          | [ ]  |
| No dev URLs in final cut (use `porterchain.com` for prod version) | [ ]  |
| No WIP / beta / disclaimer language                               | [ ]  |
| Uploaded to data room (`investor/demo/porterchain-3min.mp4`)      | [ ]  |
| Linked from [DATA_ROOM_INDEX.md](./DATA_ROOM_INDEX.md)            | [ ]  |

---

## Troubleshooting

| Issue           | Fix                                                      |
| --------------- | -------------------------------------------------------- |
| Map blank       | `pnpm validate:tracking-maps`; confirm Valhalla `:8002`  |
| No ETA          | Seed order in `in_transit`; check TrackEtaPanel          |
| Admin map empty | Complete one dispatch via operations or Fleetbase bridge |
