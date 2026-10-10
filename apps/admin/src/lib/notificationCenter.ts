import { adminFetch } from "@/lib/api";

const BASE = "/v1/admin/notifications/center";

export type Persona = "receiver" | "customer" | "merchant" | "driver" | "admin";
export const PERSONAS: Persona[] = ["receiver", "customer", "merchant", "driver", "admin"];

export type CenterMetrics = {
  window_hours: number;
  emails: number;
  accepted: number;
  p50_ms: number | null;
  p95_ms: number | null;
  delivery_pct: number | null;
  open_pct: number | null;
  bounce_pct: number | null;
  tracked: number;
  queued: number;
  held: number;
  failed: number;
  dead_letters: number;
  suppressed: number;
  failures_per_hour: { hour: string; count: number }[];
};

export type LogRow = {
  id: string;
  created_at: string | null;
  event: string | null;
  template: string;
  channel: string;
  persona: string;
  recipient: string | null;
  title: string;
  status: string;
  delivery: string | null;
  failure: string | null;
  retries: number;
  latency_ms: number | null;
  sent_at: string | null;
  delivered_at: string | null;
  opened_at: string | null;
  bounced_at: string | null;
  tracking_number: string | null;
};

export type LogDetail = LogRow & {
  body: string;
  html: string | null;
  priority: string;
  category: string;
  next_retry_at: string | null;
  suppressed: boolean | null;
  replayable: boolean;
  attempts: { at: string | null; status: string; error: string | null }[];
};

export type Suppression = {
  email: string;
  reason: string;
  source: string;
  active: boolean;
  count: number;
  since: string | null;
  updated_at: string | null;
};

export type TemplateItem = {
  key: string;
  category: string;
  receiver: boolean;
  french: boolean;
  edited_en: boolean;
  edited_fr: boolean;
};

export type TemplatePreview = {
  template: string;
  lang: string;
  audience: string;
  subject: string;
  text: string;
  html: string;
};
export type CopyVersion = {
  id: string;
  lang: string;
  version: number;
  subject: string | null;
  intro: string | null;
  active: boolean;
  created_by: string | null;
  created_at: string | null;
};
export type MatrixCell = { channels: string[]; on: boolean; locked: boolean };
export type Matrix = {
  personas: Persona[];
  rows: { event: string; group: string; cells: Partial<Record<Persona, MatrixCell>> }[];
};
export type DigestSettings = {
  enabled: boolean;
  approved: boolean;
  approved_by: string | null;
  approved_at: string | null;
  last_sent_date: string | null;
  send_hour: number;
};
export type Digest = { settings: DigestSettings; preview: Record<string, number | string | null> };

export type LogFilters = {
  persona?: string;
  event?: string;
  status?: string;
  channel?: string;
  q?: string;
};

export function logQuery(f: LogFilters, limit = 100): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(f)) if (v && String(v).trim()) p.set(k, String(v).trim());
  p.set("limit", String(limit));
  return p.toString();
}

/** "180 ms", "2.4 s", "3 min" — numbers first, one unit. */
export function fmtMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)} s`;
  return `${Math.round(ms / 60_000)} min`;
}

export function fmtPct(v: number | null | undefined): string {
  return v == null ? "—" : `${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)}%`;
}

/** One word for the row: the furthest thing we know happened. */
export function outcome(row: Pick<LogRow, "status" | "delivery" | "channel">): {
  label: string;
  tone: "ok" | "warn" | "bad" | "idle";
} {
  const d = row.delivery;
  if (d === "hard_bounce" || d === "complaint" || row.status === "bounced")
    return { label: d === "complaint" ? "Complaint" : "Bounced", tone: "bad" };
  if (row.status === "dead_letter") return { label: "Dead letter", tone: "bad" };
  if (row.status === "failed") return { label: "Failed", tone: "bad" };
  if (d === "soft_bounce") return { label: "Soft bounce", tone: "warn" };
  if (d === "clicked") return { label: "Clicked", tone: "ok" };
  if (d === "opened") return { label: "Opened", tone: "ok" };
  if (d === "delivered" || row.status === "delivered") return { label: "Delivered", tone: "ok" };
  if (row.status === "sent")
    return { label: row.channel === "email" ? "Accepted" : "Sent", tone: "ok" };
  if (row.status === "held") return { label: "Held", tone: "warn" };
  if (row.status === "queued" || row.status === "deferred")
    return { label: "Queued", tone: "idle" };
  return { label: row.status, tone: "idle" };
}

/** Failures/hour summary: latest hour and the peak in the window. */
export function failureSummary(buckets: { count: number }[]): {
  last: number;
  peak: number;
  total: number;
} {
  const counts = buckets.map((b) => b.count);
  return {
    last: counts.length ? counts[counts.length - 1] : 0,
    peak: counts.length ? Math.max(...counts) : 0,
    total: counts.reduce((a, b) => a + b, 0),
  };
}

export const centerApi = {
  metrics: (t: string, hours = 24) =>
    adminFetch<CenterMetrics>(`${BASE}/metrics?hours=${hours}`, t),
  log: (t: string, f: LogFilters) => adminFetch<LogRow[]>(`${BASE}/log?${logQuery(f)}`, t),
  detail: (t: string, id: string) =>
    adminFetch<LogDetail>(`${BASE}/log/${encodeURIComponent(id)}`, t),
  deadLetters: (t: string) => adminFetch<LogRow[]>(`${BASE}/dead-letters`, t),
  replay: (t: string, id: string) =>
    adminFetch<{ ok: boolean }>(`${BASE}/dead-letters/${encodeURIComponent(id)}/replay`, t, {
      method: "POST",
    }),
  replayAll: (t: string) =>
    adminFetch<{ replayed: number }>(`${BASE}/dead-letters/replay-all`, t, { method: "POST" }),
  suppressions: (t: string) => adminFetch<Suppression[]>(`${BASE}/suppressions`, t),
  release: (t: string, email: string) =>
    adminFetch<{ ok: boolean }>(`${BASE}/suppressions/release`, t, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  templates: (t: string) => adminFetch<TemplateItem[]>(`${BASE}/templates`, t),
  preview: (t: string, key: string, lang: string) =>
    adminFetch<TemplatePreview>(`${BASE}/templates/${key}/preview?lang=${lang}`, t),
  previewDraft: (t: string, key: string, body: { lang: string; subject: string; intro: string }) =>
    adminFetch<TemplatePreview>(`${BASE}/templates/${key}/preview`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  saveCopy: (t: string, key: string, body: { lang: string; subject: string; intro: string }) =>
    adminFetch<{ version: number; active: boolean }>(`${BASE}/templates/${key}/copy`, t, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  history: (t: string, key: string) =>
    adminFetch<CopyVersion[]>(`${BASE}/templates/${key}/history`, t),
  test: (t: string, key: string, lang: string) =>
    adminFetch<{ queued: boolean; to: string }>(`${BASE}/templates/${key}/test`, t, {
      method: "POST",
      body: JSON.stringify({ lang }),
    }),
  matrix: (t: string) => adminFetch<Matrix>(`${BASE}/matrix`, t),
  setCell: (t: string, event: string, persona: Persona, enabled: boolean) =>
    adminFetch<{ off: string[] }>(`${BASE}/matrix`, t, {
      method: "PUT",
      body: JSON.stringify({ event, persona, enabled }),
    }),
  digest: (t: string) => adminFetch<Digest>(`${BASE}/digest`, t),
  setDigest: (t: string, enabled: boolean, approve = false) =>
    adminFetch<{ settings: DigestSettings }>(`${BASE}/digest`, t, {
      method: "PUT",
      body: JSON.stringify({ enabled, approve }),
    }),
};
