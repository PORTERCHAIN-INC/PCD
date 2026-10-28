# Invoice adjustments (void, line credit, partial credit): Canada / Ontario compliance

> **Not legal or tax advice.** This page maps PorterChain's invoice-adjustment feature
> to the federal and Ontario rules we found in official sources (checked 2026-10-28).
> A CPA / tax advisor must review it before we rely on it for filing.
> Open questions for them are listed at the end.

PorterChain (the supplier) bills **merchants** monthly or per order (paid by Interac
e-Transfer) and **retail / guest customers** per order (paid by card through Stripe).
There is no cash-on-delivery. Admin finance staff can reduce what a customer owes in
three ways, and **every one of them issues a GST/HST credit note**:

| Action             | What it does                                                | Tax reversed                                                                  |
| ------------------ | ----------------------------------------------------------- | ----------------------------------------------------------------------------- |
| **Void invoice**   | Credits everything still uncredited. Status becomes `void`. | All the HST still on the invoice                                              |
| **Credit lines**   | Removes selected lines (e.g. one failed delivery).          | Exactly the HST charged on those lines                                        |
| **Partial credit** | A tax-inclusive dollar amount (e.g. $20 goodwill).          | Prorated: `amount × invoice HST ÷ invoice total`, rounded half-up to the cent |

We never delete or edit an issued invoice. The original stays as issued, and the
credit note is a separate, numbered document that refers to it.

---

## 1. A reduction in price needs a credit note (GST/HST)

**Rule.** If the price is reduced after the invoice is issued (a discount, a refund,
or a goodwill credit), the supplier _may_ refund or credit the HST on the reduced
amount. If it does, it **must issue a credit note with the prescribed information
within a reasonable time**. It deducts the tax from its own net tax in the reporting
period the note is issued. This must be done within 4 years after the end of the
period in which the price was reduced. Tax charged in error (wrong rate, duplicate
bill) can be adjusted or refunded within 2 years.

**Proof.**

- Excise Tax Act s. 232(1)-(3): https://laws-lois.justice.gc.ca/eng/acts/E-15/section-232.html
- CRA GST/HST Memorandum 12-2, _Refund, Adjustment or Credit of GST/HST under Section 232_: https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/12-2/refund-adjustment-credit-gst-hst-under-section-232-excise-tax-act.html

**How we meet it.**

- Every adjustment creates a `credit_notes` row with its own number, and the tax
  reversed is shown separately.
- We never just quietly lower the balance. The old `POST /finance/credit-notes`
  endpoint wrote a bare ledger row with no document, so it has been **removed**.
- The note is issued, emailed and downloadable at the moment the credit takes effect.
- `issued_at` dates the note, so finance knows which GST/HST return period gets the
  deduction (see the accountant note in §9).
- The reason codes `duplicate_billing` and `pricing_error` show the 2-year "charged
  in error" cases. The other codes are reductions in price under s. 232(2).

## 2. What a credit note must show

**Rule.** The Credit Note and Debit Note Information (GST/HST) Regulations, s. 3, say a
credit note must contain:

- (a) a statement or indication that it is a credit note;
- (b) the supplier's name (or trading name) and GST/HST registration number (BN);
- (c) the recipient's name (or trading name);
- (d) the date it was issued;
- (e) the amount of the adjustment, refund or credit of tax, _or_ the information
  needed to work it out (the rate and the totals).

**Proof.** SOR/91-44 s. 3: https://laws-lois.justice.gc.ca/eng/regulations/SOR-91-44/FullText.html

**How we meet it.** The credit-note PDF (`GET /v1/admin/finance/credit-notes/{id}/pdf`;
merchants and customers have their own download routes) prints:

- the title **"CREDIT NOTE"** and the number `CN-YYYY-NNNNNN`;
- the supplier's legal name and GST/HST number, taken from Admin → Settings → Finance
  (the same source as the invoices);
- the recipient's name and address;
- the issue date;
- the **original invoice number and date**;
- each credited line, the pre-tax amount, the **HST reversed**, the tax rate and
  province, and the total credit.

If the GST/HST number isn't set, the PDF leaves the line blank (it never prints a
placeholder) and admin already warns about it. Finance must set it before issuing
notes.

## 3. The recipient's input tax credit records ($30 / $100 / $500 tiers)

**Rule.** A business customer that claimed an input tax credit (ITC) on our invoice
has to reduce that ITC by the tax on the credit note. Its invoice evidence needs more
detail as the amount grows:

- **under $100 (formerly $30):** the supplier's name, date and total;
- **$100–$499.99:** also the BN and the tax amount (or the rate);
- **$500 and up:** also the recipient's name, the terms and a description of each supply.

**Proof.**

- Input Tax Credit Information (GST/HST) Regulations, SOR/91-45 s. 3: https://laws-lois.justice.gc.ca/eng/regulations/SOR-91-45/FullText.html
- CRA RC4022 _General Information for GST/HST Registrants_: https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/rc4022/general-information-gst-hst-registrants.html

**How we meet it.** Every credit note carries the full $500+ set of information,
whatever its amount: the description of each credited line, the recipient, the BN
and the tax. So the merchant's bookkeeper can always reverse the ITC.

## 4. The right rate, shown as one HST figure

**Rule.** The rate depends on the place of supply. Ontario's HST is 13%. Show the
total HST, not its federal and provincial parts.

**Proof.** CRA, _Charge and collect the tax – Which rate to charge_: https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/gst-hst-businesses/charge-collect-which-rate.html

**How we meet it.** The credit note never recalculates tax at today's rate. It
reverses **the tax the original invoice actually charged** (`invoices.tax_cents` /
`invoice_lines.tax_cents`) and copies the invoice's `tax_province`. So a 13% ON
invoice is credited at 13% and a 5% GST-only invoice at 5%, and the total credited
never exceeds the tax charged. The rounding rule is ROUND_HALF_UP to the cent. On
the final credit (or a void), we reverse exactly the tax still remaining, so the
rounding can never leave a cent of tax behind.

## 5. Bad debt is different from a waiver

**Rule.** A s. 231 bad-debt adjustment is only for debts with an arm's-length
recipient that have been **written off as uncollectible** in the books. It is not for
a voluntary waiver, which is a reduction of price under s. 232.

**Proof.** Excise Tax Act s. 231: https://laws-lois.justice.gc.ca/eng/acts/E-15/section-231.html

**How we meet it.** This feature is for adjustments we choose to make
(`service_failure`, `goodwill`, `test_delivery` …). Writing off an unpaid debt as bad
is **not** a reason code. Finance does that through the accountant's write-off
process (open item §9).

## 6. Records: keep them 6 years, in Canada, readable

**Rule.** GST/HST and income-tax records must be kept for 6 years after the end of
the year they relate to, in an electronically readable form.

**Proof.**

- Excise Tax Act s. 286: https://laws-lois.justice.gc.ca/eng/acts/E-15/section-286.html
- Income Tax Act s. 230(4): https://laws-lois.justice.gc.ca/eng/acts/I-3.3/section-230.html

**How we meet it.**

- Credit notes are never deleted. A rejected request stays `rejected`, and a void
  keeps the invoice. Each note stores a snapshot of the original invoice number and
  date, the lines, the tax, the reason, who issued it and who approved it.
- Each note also writes an `admin_audit_logs` row and an `invoice_credit_note`
  billing-ledger row (plus `merchant_credit` / refund rows when money is owed back).
- **Open item:** confirm the production database and backups are stored in Canada
  (§9).

## 7. Ontario consumers (retail / guest customers)

**Rule.** Under Ontario's _Consumer Protection Act, 2002_:

- required disclosures must be clear, comprehensible and in a form the consumer can
  keep (s. 5);
- consumers can't be made to waive their rights (s. 7);
- services must be of a reasonably acceptable quality (s. 9);
- money that a supplier wasn't entitled to charge must be refunded (s. 98, with
  refunds within 15 days under O. Reg. 17/05 for cancellations);
- card chargebacks are available (s. 99).

The _Consumer Protection Act, 2023_ was **not yet in force** when this was checked.

**Proof.**

- CPA 2002: https://www.ontario.ca/laws/statute/02c30
- O. Reg. 17/05: https://www.ontario.ca/laws/regulation/r05017
- CPA 2023 (not in force): https://www.ontario.ca/laws/statute/23c23
- Ontario, _Your rights under the Consumer Protection Act_: http://www.ontario.ca/page/your-rights-under-consumer-protection-act

**How we meet it.**

- A credit for a failed service (`service_failure`) on a card-paid order goes back to
  the **same card** through the existing idempotent Stripe refund. It isn't held as
  store credit, so the consumer gets their money back.
- The customer gets a plain-language email and a credit-note PDF they can keep.
- Our wording never asks the customer to give up any right or chargeback.
- Refunds are issued straight away in the same action, well within 15 days.

## 8. Privacy (PIPEDA)

**Rule.** Collect and use only what is needed for the stated purpose, and protect
personal information with suitable safeguards.

**Proof.** PIPEDA Schedule 1, principles 4.4, 4.5 and 4.7: https://laws-lois.justice.gc.ca/eng/acts/P-8.6/section-sched417658.html

**How we meet it.**

- Each note has two texts. The **internal note** (staff only) is never put in the
  email, the PDF or the merchant or customer API. The customer sees only a fixed,
  friendly **customer reason** for the reason code, or a short custom message the
  admin types.
- Recipient email addresses are passed through `platform.log_redact` before they are
  logged.
- The audit payload stores the code, the amounts and the note, not the recipient's
  address.

## Controls (internal, good practice rather than law)

- Only admins with the `finance` module can see this, and every write needs **staff
  step-up** (a recent re-authentication).
- **Approval above a threshold.** If a credit is over
  `finance.credit_note_approval_threshold_cents` (default **$500.00**, set in
  Admin → Settings → Finance), it waits as `pending_approval`. It has no number and
  no effect on the balance until a **different** admin approves it. The issuer can't
  approve their own note.
- **Reason code is required:** `service_failure` (our fault), `test_delivery`,
  `goodwill`, `duplicate_billing`, `pricing_error` or `other`. `other` also needs a
  note.
- Numbering is gap-free and sequential per year (`CN-2026-000001`). It uses the same
  row-locked counter as invoice numbers, and a number is allocated only when the note
  is actually issued.

## How the money moves

| Customer                | Credit ≤ open balance                                                              | Credit > what's still owed (already paid)                                                                    |
| ----------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Merchant (Interac)      | Lowers the invoice balance. Reminders and the Interac matcher use the new balance. | The excess goes to the merchant's **credit balance** (`merchant_credit`) and is applied to the next invoice. |
| Retail / guest (Stripe) | Lowers the balance.                                                                | The excess is **refunded to the card** through the existing Stripe refund path (idempotent).                 |

## 9. Open items for the accountant

1. Should the credit-note **date** (the ITC / net-tax period) be the issue date, or
   the date the invoice was originally issued? We use the issue date, per s. 232(3)(b).
2. Is our ROUND_HALF_UP proration of HST on partial goodwill credits acceptable, or do
   you prefer crediting tax only on whole lines?
3. Is $500 the right threshold for a second approver?
4. What is the write-off (s. 231 bad debt) process for unpaid Interac invoices? It's
   deliberately not in this tool.
5. Confirm the production data residency (s. 286 records kept in Canada, or CRA
   permission to keep them elsewhere).
6. QST / out-of-province merchants: we reverse whatever province's rate was charged.
   Confirm that no Québec QST registration is needed for our current volumes.
7. Time limits: the tool does **not** refuse any credit by age today. For
   `duplicate_billing` / `pricing_error` (tax charged in error, s. 232(1), 2-year limit)
   on an invoice older than 2 years it only shows a warning and records it on the
   credit note response. Confirm whether the tool should block those cases, and whether
   any credit older than 4 years (s. 232(2)) should be blocked too.
