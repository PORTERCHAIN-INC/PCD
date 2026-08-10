# Annual penetration test program

**Type:** CANONICAL  
**Checklist:** §11.1.3  
**Last verified:** 2026-07-09  
**Owner:** Security / CTO

---

## Scope (annual)

| Surface                                   | In scope                                        |
| ----------------------------------------- | ----------------------------------------------- |
| `api.porterchain.com`                     | REST + webhooks                                 |
| Admin, merchant, driver, customer portals | Auth, RBAC, IDOR                                |
| Clerk multi-portal JWT                    | Session fixation, role escalation               |
| Stripe + Fleetbase webhooks               | Signature bypass, replay                        |
| Doppler-synced prod secrets               | No dev defaults (`JWT_SECRET`, webhook secrets) |

Out of scope until prod live: mobile apps (Expo shells), Shopify/Woo native apps.

---

## Cadence

| Activity                  | When                     | Artifact                        |
| ------------------------- | ------------------------ | ------------------------------- |
| Vendor RFP / SOW          | Q3 each year             | Signed SOW                      |
| Black-box + grey-box test | 2-week window            | Executive summary PDF           |
| Remediation sprint        | Within 30 days of report | GitHub issues tagged `security` |
| Retest critical/high      | Before sign-off          | Clean retest letter             |

**Dev layer (now):** program doc + scope frozen. **Prod layer:** execute first engagement after droplet go-live (FND-G5).

---

## Pre-engagement checklist

- [ ] `GET /health/status` public status page documented ([PRIORITY_TODOS.md](../PRIORITY_TODOS.md))
- [ ] RBAC matrix exported (`pnpm validate:investor-monopoly`)
- [ ] Webhook signature verification on Stripe + Fleetbase ([SECURITY.md](../../SECURITY.md))
- [ ] Rate limits on portal prefixes (`PortalRateLimitMiddleware`)
- [ ] Privacy export/delete APIs documented ([PIPEDA.md](./PIPEDA.md))
- [ ] Staging environment with prod-like Clerk apps (optional grey-box)

---

## Reporting

Store under `docs/compliance/pen-test/` (gitignored raw reports; index only in repo):

```
docs/compliance/pen-test/
  INDEX.md          # year, vendor, critical/high counts, remediation status
  YYYY-summary.md   # redacted executive summary (no exploitable detail)
```

Update [SOC2.md](./SOC2.md) control CC7.1 when the first report is received.
