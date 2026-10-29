# 78 · Leads / CRM module (ops console → Sales → Leads)

Status: PLANNED, docs only (Ravi ask, 29 Oct 2026, America/Toronto). Self-hosted, no paid CRM, free or official channel APIs only. Reuses the existing CRM code; nothing new is built beside it. Placement follows doc 75 (ops console) and doc 16 (admin IA, Sales group). Onboarding hand-off follows docs 70–71 (being written by the parallel job; verify after).

## 1. What already exists (repo scan, 29 Oct 2026) and what happens to it

| Existing code                                                                                                                                                                                                | Verdict                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Admin pages `apps/admin/src/app/(ops)/leads/` (list, `[id]`, today, pipeline, calendar, attribution, agent) + `components/leads/*`, `components/crm/*`, `lib/crm.ts`                                         | **Reuse** as the Leads module UI; `leads/agent` hidden while `FEATURE_AI=false` (P1)                                                                         |
| `collaboration_engine/crm_*.py`, `lead_*.py`, `lead360_service.py`, `lead_convert_flow.py`, `routers/admin/leads*.py`, `routers/lead_webhooks.py`, `schemas_crm.py`, `crm_models.py`, `domain/crm_states.py` | **Reuse**; the module's backend                                                                                                                              |
| `lead_ingest_service.py` + `lead_ingest_resolve.py` + `crm_lead_identities` + `crm_lead_ingest_events` (ingest bus, identity spine)                                                                          | **Reuse** as the single fan-in and dedupe path                                                                                                               |
| `lead_channel_adapters.py` (Meta leadgen/messaging, WhatsApp, Google)                                                                                                                                        | Untracked in git today: **commit it in week 9** behind tests or delete; no second adapter layer                                                              |
| `lead_whatsapp_cloud.py`                                                                                                                                                                                     | **Dormant** (flag off). Conflicts with L27/L30-7 (WhatsApp = Business app + wa.me, human sends). Kept only for a later Ravi decision                         |
| `lead_whatsapp_gate.py` (consent + 24 h window)                                                                                                                                                              | **Reuse** as the consent check for any WhatsApp reply                                                                                                        |
| `lead_capi.py` (Meta / LinkedIn Conversions API)                                                                                                                                                             | **Off by default**; sends hashed PII to ad platforms, so only with explicit marketing consent and a privacy-policy line (doc 68). Remove if Ravi runs no ads |
| `lead_desk/ai.py`, `intelligence_engine/lead_assist.py`, `lead_nba.py`, `lead_agent*.py`                                                                                                                     | **P1** (FEATURE_AI=false in P0). `lead_desk/fit_score.py` + `lead_scoring.py` stay as the P0 rules score                                                     |
| `lead_email_inbound.py` (Zoho Mail IMAP poll)                                                                                                                                                                | **Reuse**, converted from polling to a DBOS scheduled/IDLE workflow (G12)                                                                                    |
| `lead_dial.py`                                                                                                                                                                                               | Reuse for call dispositions; dialling is from Ravi's phone (no Twilio, L26)                                                                                  |
| `lead_enrich.py` (email discovery by scraping)                                                                                                                                                               | **Remove** (PIPEDA: collecting contact data a person did not give us)                                                                                        |
| `crm_quotations`, `crm_invoices`                                                                                                                                                                             | Become views over `ordering.quotes` / `billing.invoices` (A19, doc 60 §8)                                                                                    |
| `crm_task_zoho_calendar` migration                                                                                                                                                                           | Calendar sync off; tasks stay in-app                                                                                                                         |
| Enum `LeadSourceChannel.TWITTER`                                                                                                                                                                             | Renamed value `x` with a data migration                                                                                                                      |
| Scripts `import_crm_from_json.py`, `import_crm_leads.py`, `backfill_lead_companies.py`                                                                                                                       | Triage per doc 32 (one-off imports: archive)                                                                                                                 |

No second CRM, no new tables where a `crm_*` table already fits.

## 2. Channels (free / official only)

| Channel                                                                 | Route in P0                                                                                                                                                                                             | Honest limit                                                                                      | Fallback                                                                              |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Website forms: contact, quote, sign-up started, help-centre forms, chat | Direct POST to ingest bus (same API, no third party)                                                                                                                                                    | none                                                                                              | —                                                                                     |
| Email (sales@, privacy@ excluded)                                       | Zoho Mail IMAP → DBOS workflow                                                                                                                                                                          | —                                                                                                 | —                                                                                     |
| Facebook Page DMs + comments + Lead Ads                                 | Meta Graph API webhooks (Messenger Platform, `leadgen`, `feed`), free                                                                                                                                   | Needs a Meta app, Page admin, App Review for `pages_messaging`; replies within Meta's 24 h window | Manual capture form                                                                   |
| Instagram DMs + comments                                                | Instagram Graph API (business/creator account linked to the Page), free                                                                                                                                 | App Review for `instagram_manage_messages`, `instagram_manage_comments`; 24 h window              | Manual capture                                                                        |
| WhatsApp                                                                | **Business app + wa.me links** (L27/L30-7). Inbound chats are logged by Ravi with one-tap "save as lead" (share chat to the capture form) or by forwarding to the lead inbox email. Cloud API stays off | No API read of Business-app chats                                                                 | Manual capture; Cloud API needs a Ravi decision (free service window, paid templates) |
| LinkedIn                                                                | Company page messages are not available by API to us; Lead Gen Forms API needs Marketing Developer Platform approval                                                                                    | Restricted                                                                                        | Forward LinkedIn notification emails to the lead inbox (parsed), or manual capture    |
| X                                                                       | **X API is paid** (no free read of DMs/mentions) — against L26                                                                                                                                          | Not used                                                                                          | X notification emails forwarded to the lead inbox, or manual capture                  |
| YouTube                                                                 | YouTube Data API v3 (free quota, 10,000 units/day) reads comments on our videos in a DBOS scheduled workflow every 30 min (a DBOS schedule, not a worker polling sweep, so G12 holds)                   | No DMs exist on YouTube                                                                           | Manual capture                                                                        |
| Phone call                                                              | Manual log in `lead_dial`                                                                                                                                                                               | —                                                                                                 | —                                                                                     |

Every channel lands as one `CanonicalLeadEvent` in `crm_lead_ingest_events`, then resolves to a lead.

## 3. Website leads: instant landing

- **Instant:** the form POST writes the ingest event and the lead in one transaction and emits `pc.crm.v1 lead.created` through the outbox; the lead shows in Sales → Leads within 2 s.
- **Alert to Ravi:** in-app notification + web-push/ntfy (doc 36 channels), respecting quiet hours (doc 56 single on-call: queued in quiet hours, summarised at 07:00; a quote request over the high-value threshold still pushes).
- **Auto-acknowledgement:** ZeptoMail email within 1 min ("We got your request, reference L-…, we reply within 1 business hour"), plain-language, PorterChain-branded, EN/FR by page locale; transactional, so CASL-exempt, no marketing content.
- **WhatsApp reply** only when the person ticked WhatsApp consent: the thank-you page shows a wa.me button with a prefilled message carrying the reference; Ravi replies from the Business app (its free greeting message covers the instant reply). No automated sends (L27).
- **First-response SLA target:** 1 business hour (08:00–20:00 Toronto), 4 h outside; SLA timer on the lead; amber at 75 %, red at breach, shown on Today. Targets, not promises (D-68-4).
- **One click to talk:** from the lead, "Reply" opens the composer on the lead's channel (email via ZeptoMail, Meta DM via Graph inside 24 h, WhatsApp via wa.me deep link); the conversation is stored in `crm_conversations`.
- **Spam protection without friction:** honeypot field, minimum fill time (3 s), per-IP and per-email rate limits (5/10 min, Redis), disposable-domain and link-count heuristics flagged to a "Possible spam" view (never silently dropped), no captcha.
- **Dedupe with social:** same identity spine as every channel (§4).

## 4. Identity and dedupe

One contact per person across channels. `crm_lead_identities` holds `(kind, value)` with kinds email, phone (E.164), meta_psid, ig_scoped_id, whatsapp_wa_id, youtube_channel_id, linkedin_url, x_handle. Exact match on email or phone auto-merges; weaker matches (name + company, handle) are suggested, never auto-merged; every merge is logged and reversible.

## 5. Pipeline, ownership, SLA, notes

- **Lead stages** (reuse `PIPELINE_STATUSES`): new → replied → quoted → won / lost (reason required). **Deal stages** (reuse `PIPELINE_STAGES`) for B2B: prospecting → qualified → meeting → quote sent → negotiation → contract review → won / lost.
- Owner (default Ravi; a round-robin rule when staff exist), SLA timers (first response, follow-up 48 h after quote), notes and tasks (`crm_activities`, `crm_sales_tasks`), activity timeline.
- **Conversion:** "Convert" creates an organisation with a business type and opens the short sign-up in docs 70–71 prefilled (name, email, business type from the lead form); the lead keeps `org_id` for attribution. Retail askers convert to a customer account or a guest quote.

## 6. Consent, CASL, PIPEDA

- Consent stored per channel (`consent_records`, doc 68): express (tick box, unticked by default) or implied (inquiry: 6 months, CASL s.10); expiry date on the lead; marketing sends blocked when expired; unsubscribe in every commercial email, honoured within 10 business days (we do it at once). Suppression list reused (`crm_suppressions`).
- PIPEDA: purpose shown at collection; access/delete requests via privacy@ (D-68-6) and `lead_privacy.py`; retention: lost/no-contact leads deleted after 24 months (`lead_retention.py`); data stays on our hosts (doc 28).

## 7. Attribution and UTM

First-touch and last-touch per lead: `utm_source/medium/campaign/content/term`, referrer, landing page, channel, campaign id for Meta Lead Ads; reports in leads/attribution: leads, conversion rate and won revenue per source.

## 8. Scoring

- **P0, rules only (FEATURE_AI=false):** points for business type fit (merchant/warehouse > retail), in service area (Toronto + 150 km), stated volume, complete contact, B2B email domain, replied; minus for out of area or spam flags. Bands Hot ≥ 70, Warm 40–69, Cold < 40. Transparent: the lead shows why.
- **P1:** local-model suggestions (next action, reply draft, classification) under doc 27/43, human approves every send.

## 9. Data model (domain schemas, doc 60 §8 / 63)

Schema `crm`: `leads`, `lead_identities`, `lead_ingest_events`, `contacts`, `companies` (→ links to `org.organisations`), `deals`, `conversations`, `conversation_messages`, `activities`, `sales_tasks`, `suppressions`, `referral_credits`; views `crm.quotations` → `ordering.quotes`, `crm.invoices` → `billing.invoices`. Status columns become enums (G13). Events `pc.crm.v1`: `lead.created`, `lead.merged`, `lead.stage_changed`, `lead.converted`, `lead.sla_breached`.

## 10. Ops console placement (doc 75 / doc 16)

Sales → Leads: Inbox (a filtered view of the one unified inbox in doc 75 Support S1, so lead and ticket conversations share one store and one composer; no second inbox), Today (due follow-ups, SLA breaches), Pipeline (board), Lead detail (timeline, identities, consent, score reasons, Convert), Attribution, Calendar. Settings → Lead channels (connect status per channel, spam rules, auto-ack text). The Today tile on the main console shows new leads and SLA breaches.

## 11. Acceptance tests (written before code, doc 76 style)

1. Website quote form → lead visible in Leads ≤ 2 s, push to Ravi (or queued in quiet hours), ack email sent ≤ 60 s.
2. Honeypot filled or < 3 s fill → flagged spam, not alerted; 6th post in 10 min from one IP → 429; real user with no captcha passes.
3. Same email via website then Instagram DM → one contact, two identities, one timeline.
4. Phone-only WhatsApp lead + later email lead with same phone → auto-merge; name-only match → suggestion only.
5. Meta webhook with a bad signature → rejected (`verify_meta_signature`).
6. Convert lead → org created with business type, sign-up prefilled (docs 70–71), lead shows `org_id`.
7. SLA: no reply for 1 business hour → `lead.sla_breached`, red on Today.
8. Implied consent older than 6 months → marketing send blocked; unsubscribe link → suppressed.
9. `FEATURE_AI=false` → no AI route reachable, leads/agent page hidden; score reasons shown.
10. `lead_whatsapp_cloud` and `lead_capi` flags off by default → no outbound call (network test).
11. Polling gone: inbound email handled by a DBOS workflow (G12).
12. Delete request → lead PII erased, audit row kept.

## 12. Schedule (fits the 12 weeks, no new week)

- **Week 9** (DB step 2 + admin IA already there): `crm` schema, A19 views, enums, identity spine tests, website instant-lead path, spam rules, ack email, SLA timers.
- **Week 10:** Meta Graph (FB/IG) webhooks after App Review, YouTube comments workflow, forwarded-email parsers (LinkedIn, X), unified inbox polish, acceptance tests 1–12 green.
- Meta App Review is submitted in **week 6** so approval lands by week 10; if it is late, FB/IG stay on manual capture and the gate still passes.
- Gate: part of G17 rehearsal (lead → convert → first quote) and G13 (enums).

## 13. Keys and credentials Ravi must provide (names only; stored in SOPS, doc 37)

| Channel               | Secret names                                                                                                                   | Where Ravi gets it                   |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------ |
| Website forms         | `LEAD_FORM_HMAC_SECRET` (generated by us)                                                                                      | —                                    |
| Email inbound         | `ZOHO_MAIL_USER`, `ZOHO_MAIL_APP_PASSWORD`, `ZOHO_IMAP_HOST`                                                                   | Zoho Mail app password               |
| Auto-ack email        | `ZEPTOMAIL_API_TOKEN`, `ZEPTOMAIL_FROM`                                                                                        | ZeptoMail (existing)                 |
| Push alerts           | `NTFY_TOPIC_TOKEN`, `WEBPUSH_VAPID_PRIVATE_KEY`                                                                                | generated by us                      |
| Facebook / Instagram  | `META_APP_ID`, `META_APP_SECRET`, `META_PAGE_ID`, `META_PAGE_ACCESS_TOKEN`, `META_IG_BUSINESS_ID`, `META_WEBHOOK_VERIFY_TOKEN` | Meta for Developers app + Page admin |
| WhatsApp              | none in P0 (Business app + wa.me number `WHATSAPP_PUBLIC_NUMBER`, not secret)                                                  | —                                    |
| YouTube               | `YOUTUBE_API_KEY`, `YOUTUBE_CHANNEL_ID`                                                                                        | Google Cloud console (free quota)    |
| LinkedIn              | none (forwarded emails); `LINKEDIN_CLIENT_ID/SECRET` only if MDP is approved later                                             | —                                    |
| X                     | none (paid API not used)                                                                                                       | —                                    |
| Conversions API (off) | `META_CAPI_TOKEN`, `LINKEDIN_CAPI_TOKEN` only if Ravi turns ads tracking on                                                    | —                                    |

## Unknowns

- U78-1 Meta App Review timing for messaging permissions.
- U78-2 Whether Ravi runs paid ads (decides `lead_capi` keep or remove).
- U78-3 `lead_channel_adapters.py` is untracked: commit or delete in week 9.
