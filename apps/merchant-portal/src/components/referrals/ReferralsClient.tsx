"use client";

import Button from "@/components/ui/Button";
import { EmptyState } from "@porterchain/ui/empty-state";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { referralsApi, type ReferralSubmitInput } from "@/lib/referrals";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";

function money(cents: number, currency = "CAD"): string {
  return (cents / 100).toLocaleString(undefined, {
    style: "currency",
    currency: currency.toUpperCase(),
  });
}

export default function ReferralsClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const qc = useQueryClient();
  const referralQuery = useQuery({
    queryKey: ["merchant-referrals", orgId ?? null],
    enabled: Boolean(isLoaded && isSignedIn),
    queryFn: async () => referralsApi.overview(await getApiToken(), orgId),
  });
  const data = referralQuery.data ?? null;
  const error = referralQuery.error
    ? referralQuery.error instanceof Error
      ? referralQuery.error.message
      : "Failed to load referrals"
    : null;
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState("");
  const [formOk, setFormOk] = useState("");
  const [form, setForm] = useState<ReferralSubmitInput>({
    company_name: "",
    email: "",
    phone: "",
    contact_name: "",
    notes: "",
  });

  const load = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: ["merchant-referrals", orgId ?? null] });
  }, [orgId, qc]);

  async function copyShare() {
    if (!data?.share_url) return;
    try {
      await navigator.clipboard.writeText(data.share_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    setFormOk("");
    if (!form.company_name.trim()) {
      setFormError("Company name is required");
      return;
    }
    if (!(form.email || "").trim() && !(form.phone || "").trim()) {
      setFormError("Email or phone is required");
      return;
    }
    setBusy(true);
    try {
      const token = await getApiToken();
      await referralsApi.submit(
        token,
        {
          company_name: form.company_name.trim(),
          email: form.email?.trim() || undefined,
          phone: form.phone?.trim() || undefined,
          contact_name: form.contact_name?.trim() || undefined,
          notes: form.notes?.trim() || undefined,
        },
        orgId
      );
      setFormOk("Referral submitted — our team will follow up.");
      setForm({ company_name: "", email: "", phone: "", contact_name: "", notes: "" });
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Submit failed");
    } finally {
      setBusy(false);
    }
  }

  if (!data && (!isLoaded || referralQuery.isLoading)) {
    return <PageSkeleton rows={4} />;
  }
  if (error && !data) {
    return <EmptyState title="Referrals unavailable" hint={error} />;
  }
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Referrals</h1>
        <p className="mt-1 text-sm text-muted">
          Introduce another business to PorterChain. When they convert, you earn{" "}
          {money(data.credit_cents, data.currency)} in account credit.
        </p>
      </div>

      <section className="rounded-2xl border border-primary/10 bg-white p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-primary">Share your link</h2>
        <p className="mt-1 text-sm text-muted">
          Anyone who opens this link and requests capacity is attributed to your merchant account.
        </p>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
          <code className="flex-1 truncate rounded-lg bg-slate-50 px-3 py-2 text-xs text-primary">
            {data.share_url}
          </code>
          <Button type="button" size="sm" variant="outline" onClick={() => void copyShare()}>
            {copied ? "Copied" : "Copy link"}
          </Button>
        </div>
      </section>

      <section className="rounded-2xl border border-primary/10 bg-white p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-primary">Refer a business</h2>
        <p className="mt-1 text-sm text-muted">
          Prefer a warm intro? Send their details and we will open a high-priority lead.
        </p>
        <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={(e) => void onSubmit(e)}>
          <label className="block text-sm sm:col-span-2">
            <span className="text-muted">Company</span>
            <input
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              value={form.company_name}
              onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
              required
            />
          </label>
          <label className="block text-sm">
            <span className="text-muted">Contact name</span>
            <input
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              value={form.contact_name}
              onChange={(e) => setForm((f) => ({ ...f, contact_name: e.target.value }))}
            />
          </label>
          <label className="block text-sm">
            <span className="text-muted">Email</span>
            <input
              type="email"
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            />
          </label>
          <label className="block text-sm">
            <span className="text-muted">Phone</span>
            <input
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              value={form.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="text-muted">Notes</span>
            <textarea
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              rows={3}
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            />
          </label>
          {formError ? <p className="text-sm text-red-600 sm:col-span-2">{formError}</p> : null}
          {formOk ? <p className="text-sm text-green-700 sm:col-span-2">{formOk}</p> : null}
          <div className="sm:col-span-2">
            <Button type="submit" size="sm" disabled={busy}>
              {busy ? "Submitting…" : "Submit referral"}
            </Button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border border-primary/10 bg-white p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-primary">Your referrals</h2>
        {data.referred_leads.length === 0 ? (
          <p className="mt-2 text-sm text-muted">No referred leads yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-primary/5 text-sm">
            {data.referred_leads.map((lead) => (
              <li key={lead.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <div>
                  <p className="font-medium text-primary">{lead.company_name}</p>
                  <p className="text-xs text-muted">
                    {lead.primary_contact_name ?? "—"}
                    {lead.email ? ` · ${lead.email}` : ""}
                  </p>
                </div>
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs capitalize text-slate-700">
                  {lead.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-2xl border border-primary/10 bg-white p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-primary">Credits</h2>
        {data.credits.length === 0 ? (
          <p className="mt-2 text-sm text-muted">
            Credits appear here after a referred business converts to a merchant.
          </p>
        ) : (
          <ul className="mt-3 divide-y divide-primary/5 text-sm">
            {data.credits.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span className="text-muted">
                  {money(c.amount_cents, c.currency || data.currency)}
                  {c.notes ? ` · ${c.notes}` : ""}
                </span>
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs capitalize text-slate-700">
                  {c.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
