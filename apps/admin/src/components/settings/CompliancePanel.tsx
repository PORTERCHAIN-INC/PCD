"use client";

import { useCallback, useEffect, useState } from "react";
import { Button, Input } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { adminFetch } from "@/lib/api";
import { settingsApi } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";

/* eslint-disable @typescript-eslint/no-explicit-any */
type O = Record<string, any>;

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <details className="rounded-xl border border-primary/10 p-4" open={title === "Region"}>
      <summary className="cursor-pointer text-sm font-semibold text-primary">{title}</summary>
      <div className="mt-3">{children}</div>
    </details>
  );
}

function Rows({ rows, cols }: { rows: O[]; cols: string[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="text-left text-muted">
          <tr>
            {cols.map((c) => (
              <th key={c} className="py-1 pr-3 font-medium capitalize">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-primary/5">
          {rows.map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c} className="py-1.5 pr-3 align-top">
                  {String(r[c] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function CompliancePanel() {
  const { getApiToken } = useAdminAuth();
  const [o, setO] = useState<O | null>(null);
  const [cfg, setCfg] = useState<O>({});
  const [breach, setBreach] = useState<O>({
    title: "",
    detected_at: "",
    data_types: "",
    subjects_affected: 0,
  });
  const [req, setReq] = useState<O>({ type: "access", subject: "" });
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    const t = await getApiToken();
    const data = await adminFetch<O>("/v1/admin/compliance", t);
    setO(data);
    setCfg(data.config);
  }, [getApiToken]);
  useEffect(() => void load(), [load]);

  async function put(key: string, value: unknown, label: string) {
    setMsg(null);
    try {
      const t = await getApiToken();
      await withStaffStepUp(t, () => settingsApi.updateConfig(t, key, value, label));
      setMsg("Saved");
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    }
  }

  if (!o) return <p className="text-sm text-muted">Loading…</p>;
  const strip = (rows: O[], drop: string[]) =>
    rows.map((r) => Object.fromEntries(Object.entries(r).filter(([k]) => !drop.includes(k))));

  return (
    <div className="max-w-4xl space-y-3">
      <Card title="Region">
        <div className="grid gap-2 sm:grid-cols-3">
          <label className="text-xs text-muted">
            Region
            <select
              className="mt-1 block w-full rounded-md border border-primary/15 bg-white px-2 py-2 text-sm"
              value={cfg.region}
              onChange={(e) => setCfg({ ...cfg, region: e.target.value })}
            >
              {Object.entries(o.regions).map(([k, v]) => (
                <option key={k} value={k}>
                  {String(v)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-muted">
            Data residency
            <select
              className="mt-1 block w-full rounded-md border border-primary/15 bg-white px-2 py-2 text-sm"
              value={cfg.data_residency ?? ""}
              onChange={(e) => setCfg({ ...cfg, data_residency: e.target.value || null })}
            >
              <option value="">Region default</option>
              <option value="ca-central">Canada (Toronto)</option>
              <option value="eu-central">EU (Frankfurt)</option>
            </select>
          </label>
          <label className="text-xs text-muted">
            Privacy contact / DPO
            <Input
              value={cfg.dpo_contact ?? ""}
              onChange={(e) => setCfg({ ...cfg, dpo_contact: e.target.value })}
            />
          </label>
        </div>
        <p className="mt-2 text-xs text-muted">
          {o.region.currency} · {o.region.tax.name} {o.region.tax.rate_pct}% · {o.region.locale} ·{" "}
          {o.region.privacy_law} · invoices kept {o.region.invoice_retention_years} y · cookie
          opt-in {o.region.cookie_banner ? "on" : "off"}
          {o.region.einvoice ? ` · e-invoice: ${o.region.einvoice}` : ""}
        </p>
        <div className="mt-3 flex items-center gap-3">
          <Button onClick={() => void put("compliance", cfg, "Compliance region")}>Save</Button>
          {msg && <span className="text-xs text-muted">{msg}</span>}
        </div>
      </Card>

      <Card title={`Breach log (72 h to notify) · ${o.breaches.length}`}>
        <Rows
          rows={o.breaches.map((b: O) => ({
            ...b,
            clock: b.authority_notified_at
              ? "notified"
              : b.overdue
                ? "OVERDUE"
                : `${b.hours_left} h left`,
          }))}
          cols={["title", "detected_at", "risk", "subjects_affected", "clock"]}
        />
        <div className="mt-2 grid gap-2 sm:grid-cols-4">
          <Input
            placeholder="What happened"
            value={breach.title}
            onChange={(e) => setBreach({ ...breach, title: e.target.value })}
          />
          <Input
            type="datetime-local"
            value={breach.detected_at}
            onChange={(e) => setBreach({ ...breach, detected_at: e.target.value })}
          />
          <Input
            placeholder="Data types"
            value={breach.data_types}
            onChange={(e) => setBreach({ ...breach, data_types: e.target.value })}
          />
          <Button
            disabled={!breach.title || !breach.detected_at}
            onClick={() =>
              void put(
                "breach_log",
                [
                  ...o.breaches.map(
                    (b: O) => strip([b], ["authority_due_at", "hours_left", "overdue"])[0]
                  ),
                  { ...breach, detected_at: new Date(breach.detected_at).toISOString() },
                ],
                "Breach logged"
              )
            }
          >
            Log breach
          </Button>
        </div>
      </Card>

      <Card
        title={`Data-subject requests (30 days) · ${o.requests.filter((r: O) => r.status === "open").length} open`}
      >
        <Rows
          rows={o.requests.map((r: O) => ({
            ...r,
            due: r.overdue ? `OVERDUE ${r.due_at.slice(0, 10)}` : r.due_at.slice(0, 10),
          }))}
          cols={["type", "subject", "status", "due"]}
        />
        <div className="mt-2 grid gap-2 sm:grid-cols-3">
          <select
            className="rounded-md border border-primary/15 bg-white px-2 py-2 text-sm"
            value={req.type}
            onChange={(e) => setReq({ ...req, type: e.target.value })}
          >
            {o.request_types.map((t: string) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          <Input
            placeholder="Email or phone"
            value={req.subject}
            onChange={(e) => setReq({ ...req, subject: e.target.value })}
          />
          <Button
            disabled={!req.subject}
            onClick={() =>
              void put(
                "privacy_requests",
                [...strip(o.requests, ["overdue"]), req],
                "Privacy request"
              )
            }
          >
            Open request
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted">
          Access/portability: Privacy Requests → download. Erasure: Privacy Requests → erase.
          Rectification: edit the customer/order. Restriction/objection: record here; marketing
          objection = unsubscribe.
        </p>
      </Card>

      <Card title="Retention schedule">
        <Rows rows={o.retention} cols={["data", "keep", "basis"]} />
      </Card>
      <Card title="Records of processing (GDPR Art. 30)">
        <Rows
          rows={o.ropa}
          cols={["activity", "subjects", "data", "purpose", "basis", "recipients", "transfer"]}
        />
      </Card>
      <Card title="Subprocessors">
        <Rows
          rows={o.subprocessors.map((s: O) => ({ ...s, dpa: s.dpa ? "signed" : "missing" }))}
          cols={["name", "purpose", "location", "dpa"]}
        />
      </Card>
      <Card title="DPIA — driver GPS">
        <p className="text-xs leading-relaxed">{o.dpia_gps}</p>
      </Card>
      {o.monitoring_policy ? (
        <Card title="Electronic monitoring policy (Ontario ESA)">
          <p className="text-xs text-muted">
            Version {o.monitoring_policy.version} · effective {o.monitoring_policy.date} ·{" "}
            {o.monitoring_policy.acknowledged}/{o.monitoring_policy.drivers} drivers acknowledged
            {o.monitoring_policy.pending ? ` · ${o.monitoring_policy.pending} pending` : ""}
          </p>
          <details className="mt-2 text-xs leading-relaxed">
            <summary className="cursor-pointer font-semibold">Read policy</summary>
            {o.monitoring_policy.sections.map((sec: O) => (
              <div key={sec.heading} className="mt-2">
                <p className="font-semibold">{sec.heading}</p>
                {sec.body ? <p>{sec.body}</p> : null}
                {sec.items ? (
                  <ul className="list-disc pl-4">
                    {sec.items.map((i: string) => (
                      <li key={i}>{i}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ))}
          </details>
        </Card>
      ) : null}
    </div>
  );
}
