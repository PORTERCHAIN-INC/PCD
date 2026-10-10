"use client";

import { useState } from "react";
import { Button, Input } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { adminFetch } from "@/lib/api";

type Bundle = { respond_by: string; counts: Record<string, number> };

/** PIPEDA access request: find everything held for one person, download it, send it yourself. */
export default function PrivacyAccessPanel() {
  const { getApiToken } = useAdminAuth();
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [erasePlan, setErasePlan] = useState<Record<string, unknown> | null>(null);

  async function erase(dry: boolean) {
    setErr(null);
    try {
      const t = await getApiToken();
      const res = await adminFetch<Record<string, unknown>>("/v1/admin/privacy/erase", t, {
        method: "POST",
        body: JSON.stringify({
          email: email || undefined,
          phone: phone || undefined,
          dry_run: dry,
        }),
      });
      setErasePlan(res);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erase failed");
    }
  }

  async function find() {
    setErr(null);
    setBundle(null);
    try {
      const t = await getApiToken();
      const qs = new URLSearchParams({ ...(email && { email }), ...(phone && { phone }) });
      const b = await adminFetch<Bundle>(`/v1/admin/privacy/access-export?${qs}`, t);
      setBundle(b);
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(b, null, 2)], { type: "application/json" })
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = `access-request-${(email || phone).replace(/\W+/g, "-")}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Lookup failed");
    }
  }

  return (
    <div className="max-w-xl space-y-3">
      <p className="text-sm text-muted">
        A person can ask what PorterChain holds about them (PIPEDA). Find it here, review the file,
        and send it to them within 30 days. Nothing is sent automatically.
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        <Input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Input placeholder="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
      </div>
      <Button disabled={!email && !phone} onClick={() => void find()}>
        Find &amp; download
      </Button>
      {err && <p className="text-sm text-red-700">{err}</p>}
      {bundle && (
        <p className="text-sm">
          {bundle.counts.customers} accounts · {bundle.counts.orders} orders ·{" "}
          {bundle.counts.support_tickets} tickets — respond by <b>{bundle.respond_by}</b>
        </p>
      )}
      <div className="rounded-xl border border-red-200 p-3">
        <p className="text-sm font-semibold text-red-800">Erase this person</p>
        <p className="text-xs text-muted">
          Removes names, emails, phones and street addresses from their account and orders.
          Invoices, payments and order city/FSA stay (tax law: CA 6 y, AT 7 y).
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Button disabled={!email && !phone} onClick={() => void erase(true)}>
            Preview erase
          </Button>
          {erasePlan?.dry_run === true && (
            <button
              type="button"
              className="rounded-md bg-red-700 px-3 py-2 text-sm font-semibold text-white"
              onClick={() => void erase(false)}
            >
              Erase {String(erasePlan.orders_scrubbed)} orders, {String(erasePlan.customers)}{" "}
              accounts
            </button>
          )}
          {erasePlan?.erased_at != null && <span className="text-xs">Erased.</span>}
        </div>
      </div>
    </div>
  );
}
