# Security incident & privacy breach response runbook

Owner / accountable person: **Ravi Chauhan, Owner** — privacy@porterchain.com, sales@porterchain.com.
All times recorded in **UTC** (servers are NTP-synchronised; verify with `timedatectl`).

## 0. First hour — contain and preserve

1. Open a breach entry: Admin → Settings → Compliance → Breach log (title + detected time). This starts
   the 72 h clock (GDPR) and the PIPEDA record (kept at least 24 months, cannot be shortened).
2. Contain without destroying evidence:
   - Suspend the affected staff/driver/merchant account (Admin). Driver suspension also revokes all
     Clerk sessions. Staff: revoke sessions (Admin → Security) and, if needed, enable the
     Admin IP allowlist (Settings → Admin access).
   - Rotate exposed secrets (Doppler/`/opt/porterchain/.env`), then redeploy.
   - Do **not** delete logs, containers or DB rows. Do not reboot unless needed to stop harm.
3. Preserve evidence immediately (on the droplet, as the deploy user with sudo):
   ```bash
   sudo systemctl start porterchain-postgres-backup.service   # encrypted DB + evidence bundle
   cd /opt/porterchain && docker compose -f docker-compose.prod.yml exec -T api \
     python -m porterchain_api.forensics_cli checkpoint         # signed head of the audit chain
   ```
   Record in the breach timeline what you did and when.

## 1. Assess — real risk of significant harm (RROSH, PIPEDA s.10.1)

Fill the breach entry fields. Consider:

- **Sensitivity** of the information (identity documents, payment, precise location history,
  health, contact info combined with addresses = higher).
- **Probability of misuse**: who had access, was it encrypted, was it recovered, evidence of
  malicious intent, how long exposed, number of people.
- "Significant harm" includes bodily harm, humiliation, damage to reputation or relationships,
  loss of employment/business opportunities, financial loss, identity theft, negative credit
  effects, damage to or loss of property.
  Conclude **real_risk = yes / no / undetermined** and write the reasoning.

## 2. Notify (if RROSH = yes) — "as soon as feasible"

- **OPC** (Office of the Privacy Commissioner of Canada): online breach report form. Use
  _Evidence pack_ (Compliance → Breach log) — its `opc_report_fields` map 1:1 to the form:
  description of circumstances, cause, date/period, personal information involved, number of
  individuals, steps taken to reduce harm, steps to notify individuals, contact person.
- **Individuals**: direct notification (email/phone/letter) containing: what happened and when,
  what information, steps we took, steps they can take, contact for questions. Indirect notice
  (website) only if direct would cause further harm or is prohibitively costly.
- **Other organisations/government** that can reduce the harm (e.g. banks, police) — notify and
  record it.
- EU/UK data subjects: supervisory authority within **72 h** of awareness (GDPR Art. 33).
- Record every notification in the breach entry (`notifications`: at, to, method, note) and set
  `opc_reported_at`.

## 3. Police / RCMP

Criminal activity (intrusion, extortion, theft): report to local police or RCMP and the Canadian
Anti-Fraud Centre. Provide the evidence pack + the encrypted nightly bundle(s) covering the period.
Chain-of-custody: note who exported what and when in the breach timeline; hand over copies, keep
originals; give investigators the audit public key (in the pack) so they can verify integrity.

## 4. Verifying evidence integrity

- Every audit entry: `hash = sha256(prev_hash || canonical_json(entry))`, genesis = 64 zeros.
  `python -m porterchain_api.forensics_cli verify` re-computes the chain.
- Checkpoints are Ed25519 signatures over `porterchain-audit|<seq>|<head_hash>|<time>`; the public
  key is in every export. A checkpoint copied off-server (nightly bundle) proves later edits.
- The audit tables reject UPDATE/DELETE/TRUNCATE at the database level.
- Bundles contain `SHA256SUMS`, Caddy access logs (JSON, UTC), host auth log, and time-sync state.

## 5. Close

Root cause, fixes, lessons; update the breach entry (`contained_at`, `measures`). Keep the record
at least 24 months (PIPEDA) — the system enforces `retain_until` ≥ detected + 24 months.

## What is logged (minimal, privacy-preserving)

Staff sign-ins and failed sign-ins (IP, factor), every mutating Admin call, every data export /
privacy request / erasure, merchant webhook & API-key changes, settings/pricing/permission changes,
deploys. Never logged: passwords, tokens, cookies, request bodies. Emails/phones are masked in
audit details. Retention: audit chain indefinitely (append-only); access/auth logs ≥ 1 year.
