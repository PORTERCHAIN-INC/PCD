# CRM Lead 360 — freeze & channel honesty

**Status:** Lead Workspace hub is `CrmLead` + admin Lead 360 (`GET /v1/admin/leads/{id}/360`).

## Keep / compose

- Lead ingest bus, identities, merge, scoring, assist, CAPI, nurture, territory/SLA
- Pipeline board (same hub, stage view)
- Convert → company / retail customer / driver partner
- VisitorSession + BookingDraft + AbandonedCheckout **composed** into Lead 360 (not merged tables)

## Freeze (do not build UI)

- CRM quotations / `CrmInvoice` / `CrmDocument` as a sales AR stack — charter fail; unused in admin
- Standalone Companies app — companies are convert artifacts only
- `AdminCrmService` — **deleted**; metrics live on `lead_channel_metrics`

## Channel honesty

| Surface                                                              | Creates CrmLead?         |
| -------------------------------------------------------------------- | ------------------------ |
| Website contact / business / newsletter (`submitInquiry` + `pc_vid`) | Yes                      |
| Capacity guide                                                       | Yes                      |
| Retail booking mirror                                                | Yes                      |
| Meta / LinkedIn / ad webhooks                                        | Yes                      |
| WhatsApp **Cloud API** webhooks                                      | Yes                      |
| WhatsApp FAB deep-link on marketing site                             | **No** — opens chat only |
| `HomeVehicleLeadCapture`                                             | **No** — CTA only        |

## Support / claims

Separate products. Do not merge support tickets or claims into Lead 360.

## Privacy / CASL / retention

- Lead consent bag includes CASL evidence (`captured_at`, `source`, `text_version`, `actor`, `legal_basis`) plus marketing/sms/whatsapp flags. Website CMP cookie consent (`consent.ts`) is **not** the same bag.
- `legal_basis`: `consent` | `legitimate_interest` | `contract` (GDPR Art.6 / PIPEDA purpose). Marketing forms default to `consent`; booking terms → `contract`; merchant referral → `legitimate_interest` with marketing off.
- Public unsubscribe: `POST /v1/public/leads/unsubscribe` (signed token from nurture emails) → website `/unsubscribe`. Also upserts `CrmSuppression` (hashed email/phone).
- Global DNC: nurture intro/D1 enqueue checks `CrmSuppression`. Merge must not resurrect `marketing=true` after unsubscribe without a fresh stamped opt-in that clears suppression.
- PIPEDA soft erase / export: `GET|POST /v1/admin/leads/{id}/privacy/*` (distinct from hard `DELETE` lead). Erase upserts suppression; audit via admin_audit + CrmActivity.
- Retention: converted ~7 years; inactive unconverted soft-archive (`status=archived`) after ~24 months via worker drain. No automated purge in this release.
- Inbox default sort=`smart` (SLA breached → priority → score → created_at).
- Domain events: `lead.created` / `lead.merged` on ingest; `lead.engagement` on ESP open/click (`POST /v1/public/leads/engagement`).
- WhatsApp outbound gate: consent or 24h care window (`lead360.nurture.whatsapp`); Cloud send via `META_WA_*` + `lead_whatsapp_cloud` when configured.
- Zero-human **lead_agent**: on non-quiet ingest + worker tick, NBA → auto `lead_nurture_intro` email when marketing consent; kill switch `LEAD_AGENT_AUTO_SEND`. Vendor phone-only → `needs_enrich` (no cold WA blast).
- Suppression admin: `GET/DELETE /v1/admin/leads/suppressions` + Lead Ingest settings card (hashes only).
- Nurture drip: D0 intro + D+1 email + D+3 call/WA task + D+7 re-engage email (consent + DNC gated).
- RoPA: `GET /v1/admin/leads/privacy/ropa` + included on DSAR export; Lead Ingest settings card. Primary residency `CA-ON`; `multi_region=false`.
- Staff escalation for unassigned high/urgent uses `StaffTopic=growth` → `crm` module roles.

## Still deferred

- Full Salesforce-style sequence builder UI · FR admin i18n / full WCAG redesign · multi-region residency product · ESP vendor-specific webhook adapters beyond open/click hook.
- Worker sweeps SLA-breached **new** leads hourly (`escalate_sla_breached_leads`) with the same growth fanout (idempotent per day).
