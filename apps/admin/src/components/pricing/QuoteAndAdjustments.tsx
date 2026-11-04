"use client";

import { useCallback, useEffect, useState } from "react";
import { formatCents } from "@porterchain/ui/utils";
import { Button, Input } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import {
  adjustmentError,
  dollarsToCents,
  hoursLeft,
  rateCardApi,
  type OrderAdjustments,
  type SentQuote,
} from "@/lib/rate-card";

/** Doc 72 §9.3: price on the Standard card and email a 72-hour quote link. */
export function SendQuotePanel({
  orgId,
  leadId,
  defaultEmail,
}: {
  orgId?: string;
  leadId?: string;
  defaultEmail?: string;
}) {
  const { getApiToken } = useAdminAuth();
  const [email, setEmail] = useState(defaultEmail ?? "");
  const [kg, setKg] = useState("4");
  const [dims, setDims] = useState("40x30x20");
  const [zone, setZone] = useState("Z1");
  const [audience, setAudience] = useState<"retail" | "b2b">(orgId ? "b2b" : "retail");
  const [sent, setSent] = useState<SentQuote[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    const t = await getApiToken();
    if (!t) return;
    const r = await rateCardApi.sentQuotes(t, {
      ...(orgId ? { org_id: orgId } : {}),
      ...(leadId ? { lead_id: leadId } : {}),
    });
    setSent(r.items);
  }, [getApiToken, orgId, leadId]);
  useEffect(() => {
    void load().catch(() => undefined);
  }, [load]);

  async function send() {
    setMsg(null);
    const t = await getApiToken();
    if (!t) return;
    const [l, w, h] = dims.split(/x/i).map(Number);
    try {
      const q = await rateCardApi.sendQuote(t, {
        email,
        zone,
        audience,
        org_id: orgId,
        lead_id: leadId,
        items: [
          { weight_kg: Number(kg) || 0, length_cm: l || 0, width_cm: w || 0, height_cm: h || 0 },
        ],
      });
      setMsg(
        `${formatCents(q.total_cents)} quote ${q.delivery?.sent ? "emailed" : "saved (copy the link)"} · valid 72 h`
      );
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Could not send");
    }
  }

  return (
    <section className="space-y-2 rounded-xl border border-primary/10 p-3">
      <h3 className="text-sm font-semibold text-primary">Send quote (valid 72 h)</h3>
      <div className="flex flex-wrap gap-2">
        <Input
          aria-label="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email"
        />
        <Input
          aria-label="Weight kg"
          value={kg}
          onChange={(e) => setKg(e.target.value)}
          className="w-20"
        />
        <Input
          aria-label="Dimensions cm"
          value={dims}
          onChange={(e) => setDims(e.target.value)}
          className="w-28"
        />
        <select
          aria-label="Zone"
          value={zone}
          onChange={(e) => setZone(e.target.value)}
          className="rounded border px-2 text-sm"
        >
          <option value="Z1">Z1 Toronto</option>
          <option value="Z2">Z2 Near GTA</option>
          <option value="Z3">Z3 Regional</option>
        </select>
        <select
          aria-label="Audience"
          value={audience}
          onChange={(e) => setAudience(e.target.value as "retail" | "b2b")}
          className="rounded border px-2 text-sm"
        >
          <option value="retail">Retail</option>
          <option value="b2b">Business</option>
        </select>
        <Button onClick={() => void send()} disabled={!email.includes("@")}>
          Send
        </Button>
      </div>
      {msg ? <p className="text-xs text-muted">{msg}</p> : null}
      <ul className="text-xs">
        {sent.map((q) => (
          <li key={q.id} className="flex gap-2">
            <span>{q.email}</span>
            <span>{formatCents(q.total_cents)}</span>
            <span>{q.status === "sent" ? `${hoursLeft(q.expires_at)} h left` : q.status}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Doc 72 §9.4: per-order adjustments within the role limit, reason required. */
export function OrderAdjustmentsPanel({ orderId }: { orderId: string }) {
  const { getApiToken } = useAdminAuth();
  const [data, setData] = useState<OrderAdjustments | null>(null);
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("waiting");
  const [reason, setReason] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    const t = await getApiToken();
    if (t) setData(await rateCardApi.adjustments(t, orderId));
  }, [getApiToken, orderId]);
  useEffect(() => {
    void load().catch(() => setData(null));
  }, [load]);
  if (!data) return null;

  const cents = dollarsToCents(amount);
  const invalid = adjustmentError(cents, reason, data.limit_cents);

  async function save() {
    const t = await getApiToken();
    if (!t || cents == null) return;
    try {
      setData(await rateCardApi.addAdjustment(t, orderId, { cents, category, reason }));
      setAmount("");
      setReason("");
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Refused");
    }
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">Adjustments</p>
      <p className="text-xs">
        Order {formatCents(data.order_amount_cents)} · adjustments{" "}
        {formatCents(data.adjustments_cents)} · total{" "}
        <strong>{formatCents(data.adjusted_total_cents)}</strong> · your limit ±
        {formatCents(data.limit_cents)}
      </p>
      <ul className="text-xs">
        {data.items.map((a) => (
          <li key={a.id}>
            {formatCents(a.cents)} · {a.category} · {a.reason}
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-2">
        <Input
          aria-label="Amount"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="-5.00"
          className="w-24"
        />
        <select
          aria-label="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded border px-2 text-sm"
        >
          {data.categories.map((c) => (
            <option key={c} value={c}>
              {c.replace("_", " ")}
            </option>
          ))}
        </select>
        <Input
          aria-label="Reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="reason"
        />
        <Button onClick={() => void save()} disabled={invalid != null}>
          Add
        </Button>
      </div>
      {invalid && amount ? <p className="text-xs text-amber-700">{invalid}</p> : null}
      {err ? <p className="text-xs text-red-700">{err}</p> : null}
    </div>
  );
}
