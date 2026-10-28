"use client";

import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { financeApi, GST_HST_PATTERN } from "@/lib/finance";
import { withStaffStepUp } from "@/lib/staff-step-up";
import { Button, Field, Input, SectionCard } from "@/components/crm/primitives";
import { FinanceShell } from "./FinanceShell";

function today(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Toronto" }).format(new Date());
}

function errorText(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e);
  const map: Record<string, string> = {
    gst_hst_number_invalid: "Number must be 9 digits + RT + 4 digits, e.g. 123456789RT0001.",
    legal_name_required: "Legal name (as registered with CRA) is required.",
    effective_from_before_latest_change: "Date cannot be before the latest change in the history.",
    registration_unchanged: "That is already the registration in force on that date.",
    effective_from_invalid: "Pick a valid effective date.",
  };
  const key = Object.keys(map).find((k) => msg.includes(k));
  return key ? map[key] : msg || "Could not save";
}

/** Settings for our own GST/HST registration. Unset = no GST/HST anywhere in the system. */
export default function TaxRegistrationClient() {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => financeApi.taxRegistration(t), [], {
    key: "finance-tax-registration",
  });
  const [number, setNumber] = useState("");
  const [legal, setLegal] = useState("");
  const [from, setFrom] = useState(today());
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const numberOk = number.trim() === "" || GST_HST_PATTERN.test(number.trim());

  async function save(end: boolean) {
    setError(null);
    setMessage(null);
    if (!end && !GST_HST_PATTERN.test(number.trim())) {
      setError(errorText("gst_hst_number_invalid"));
      return;
    }
    if (!end && !legal.trim()) {
      setError(errorText("legal_name_required"));
      return;
    }
    setBusy(true);
    try {
      const token = await getApiToken();
      await withStaffStepUp(token, () =>
        financeApi.changeTaxRegistration(token, {
          gst_hst_number: end ? null : number.trim(),
          legal_name: end ? null : legal.trim(),
          effective_from: from,
          note: note.trim() || null,
        })
      );
      setMessage(end ? "Registration ended from that date." : "Registration saved.");
      setNumber("");
      setLegal("");
      setNote("");
      void refetch();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <FinanceShell
      title="GST/HST registration"
      subtitle="Until a number is registered, PorterChain charges and shows no GST/HST anywhere."
    >
      <SectionCard title="Status">
        {data ? (
          data.registered ? (
            <p className="text-sm">
              Registered: <span className="font-semibold">{data.gst_hst_number}</span> ·{" "}
              {data.legal_name} · from {data.effective_from}
            </p>
          ) : (
            <p className="text-sm">
              Not registered (small supplier). Quotes, checkouts, invoices, credit notes, emails and
              PDFs carry no GST/HST.
            </p>
          )
        ) : (
          <p className="text-sm text-muted">Loading…</p>
        )}
        {data?.upcoming ? (
          <p className="mt-2 text-sm">
            Scheduled from {data.upcoming.effective_from}:{" "}
            {data.upcoming.gst_hst_number
              ? `${data.upcoming.gst_hst_number} (${data.upcoming.legal_name})`
              : "registration ends"}
          </p>
        ) : null}
      </SectionCard>

      <SectionCard title="Register or change">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="GST/HST number" hint="9-digit BN + RT + 4 digits, e.g. 123456789RT0001">
            <Input
              value={number}
              onChange={(e) => setNumber(e.target.value.toUpperCase())}
              placeholder="123456789RT0001"
              aria-invalid={!numberOk}
            />
          </Field>
          <Field label="Legal name (as registered with CRA)">
            <Input value={legal} onChange={(e) => setLegal(e.target.value)} />
          </Field>
          <Field
            label="Effective date"
            hint="Tax applies to invoices and quotes from this date. Issued invoices never change."
          >
            <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </Field>
          <Field label="Note (optional)">
            <Input value={note} onChange={(e) => setNote(e.target.value)} />
          </Field>
        </div>
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="mt-3 text-sm text-emerald-700">{message}</p> : null}
        <div className="mt-4 flex gap-2">
          <Button disabled={busy || !numberOk} onClick={() => void save(false)}>
            Save registration
          </Button>
          {data?.registered ? (
            <Button variant="secondary" disabled={busy} onClick={() => void save(true)}>
              End registration from date
            </Button>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard title="History">
        {data && data.history.length ? (
          <ul className="divide-y text-sm">
            {data.history.map((h) => (
              <li key={h.id} className="py-2">
                <span className="font-semibold">{h.effective_from}</span> ·{" "}
                {h.gst_hst_number ? `${h.gst_hst_number} (${h.legal_name})` : "Not registered"}
                {h.note ? ` · ${h.note}` : ""}
                {h.created_at ? (
                  <span className="text-muted"> · changed {h.created_at.slice(0, 10)}</span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">No changes yet.</p>
        )}
      </SectionCard>
    </FinanceShell>
  );
}
