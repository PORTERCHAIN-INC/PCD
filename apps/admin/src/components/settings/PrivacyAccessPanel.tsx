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
    </div>
  );
}
