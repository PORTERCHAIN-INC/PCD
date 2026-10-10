"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import AdminPage from "@/components/layout/AdminPage";
import { cn } from "@porterchain/ui/utils";
import {
  centerApi,
  failureSummary,
  fmtMs,
  fmtPct,
  outcome,
  PERSONAS,
  type CenterMetrics,
  type LogFilters,
  type LogRow,
} from "@/lib/notificationCenter";
import { Empty, NAVY, PrimaryButton, QuietButton, Select, Tone, when } from "./ui";
import TemplateManager from "./TemplateManager";
import { DigestPanel, MatrixPanel } from "./MatrixDigest";

type Tab = "log" | "dead" | "suppressed" | "templates" | "matrix" | "digest";
const TABS: [Tab, string][] = [
  ["log", "Live log"],
  ["dead", "Dead letters"],
  ["suppressed", "Suppressed"],
  ["templates", "Templates"],
  ["matrix", "Matrix"],
  ["digest", "Digest"],
];

function useToken() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  return { getApiToken, ready: isLoaded && isSignedIn };
}

function Stat({
  label,
  value,
  sub,
  alert,
}: {
  label: string;
  value: string;
  sub?: string;
  alert?: boolean;
}) {
  return (
    <div className="min-w-0">
      <p
        className={cn(
          "text-2xl font-extrabold tabular-nums tracking-tight sm:text-3xl",
          alert ? "text-[#fca5a5]" : "text-white"
        )}
      >
        {value}
      </p>
      <p className="mt-1 text-[11px] font-semibold uppercase tracking-wider text-slate-300">
        {label}
      </p>
      {sub ? <p className="text-xs text-slate-400">{sub}</p> : null}
    </div>
  );
}

function Spark({ buckets }: { buckets: { hour: string; count: number }[] }) {
  const peak = Math.max(1, ...buckets.map((b) => b.count));
  return (
    <div
      className="flex h-8 items-end gap-[2px]"
      role="img"
      aria-label={`Failures per hour, peak ${peak}`}
    >
      {buckets.map((b) => (
        <span
          key={b.hour}
          title={`${when(b.hour)}: ${b.count}`}
          className={cn("w-full min-w-[2px] rounded-sm", b.count ? "bg-[#fca5a5]" : "bg-white/15")}
          style={{ height: `${Math.max(8, (b.count / peak) * 100)}%` }}
        />
      ))}
    </div>
  );
}

function SpeedStrip({ m }: { m: CenterMetrics | undefined }) {
  const f = failureSummary(m?.failures_per_hour ?? []);
  return (
    <section aria-label="Speed" className="rounded-3xl p-5 sm:p-7" style={{ background: NAVY }}>
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#93c5fd]">
          Last 24 h · event → email accepted
        </p>
        <p className="text-xs text-slate-400">
          {m ? `${m.accepted.toLocaleString()} accepted` : "Loading…"}
        </p>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="p50" value={fmtMs(m?.p50_ms)} />
        <Stat label="p95" value={fmtMs(m?.p95_ms)} alert={(m?.p95_ms ?? 0) > 60_000} />
        <Stat
          label="Delivered"
          value={fmtPct(m?.delivery_pct)}
          sub={m?.tracked ? `${m.tracked} tracked` : "awaiting webhooks"}
        />
        <Stat label="Bounce" value={fmtPct(m?.bounce_pct)} alert={(m?.bounce_pct ?? 0) > 2} />
        <Stat
          label="Failures / h"
          value={String(f.last)}
          sub={`peak ${f.peak}`}
          alert={f.last > 0}
        />
        <Stat
          label="Dead letters"
          value={String(m?.dead_letters ?? "—")}
          alert={(m?.dead_letters ?? 0) > 0}
          sub={`${m?.suppressed ?? 0} suppressed`}
        />
      </div>
      <div className="mt-5">
        <Spark buckets={m?.failures_per_hour ?? []} />
      </div>
    </section>
  );
}

function Row({ r, onOpen, active }: { r: LogRow; onOpen: (id: string) => void; active: boolean }) {
  const o = outcome(r);
  return (
    <li>
      <button
        type="button"
        onClick={() => onOpen(r.id)}
        className={cn(
          "grid w-full grid-cols-[1fr_auto] gap-x-3 gap-y-1 px-4 py-3 text-left hover:bg-slate-50 focus-visible:bg-slate-50 focus-visible:outline-none sm:grid-cols-[7rem_1fr_9rem_6rem_6rem]",
          active && "bg-blue-50/60"
        )}
      >
        <span className="order-3 text-xs tabular-nums text-slate-600 sm:order-none sm:text-sm">
          {when(r.created_at)}
        </span>
        <span className="min-w-0">
          <span className="block truncate text-sm font-semibold text-slate-900">
            {r.title || r.template}
          </span>
          <span className="block truncate text-xs text-slate-600">
            {r.persona} · {r.channel} · {r.recipient ?? "—"}
          </span>
        </span>
        <span className="hidden truncate text-xs text-slate-600 sm:block">
          {r.event ?? r.template}
        </span>
        <span className="hidden text-sm tabular-nums text-slate-700 sm:block">
          {fmtMs(r.latency_ms)}
        </span>
        <span className="justify-self-end">
          <Tone tone={o.tone}>{o.label}</Tone>
        </span>
      </button>
    </li>
  );
}

function Detail({ id, onClose }: { id: string; onClose: () => void }) {
  const { getApiToken, ready } = useToken();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const { data: d } = useQuery({
    queryKey: ["nc-detail", id],
    enabled: ready,
    queryFn: async () => centerApi.detail(await getApiToken(), id),
  });
  const replay = async () => {
    setBusy(true);
    try {
      await centerApi.replay(await getApiToken(), id);
      await qc.invalidateQueries({ queryKey: ["nc-detail", id] });
      await qc.invalidateQueries({ queryKey: ["nc-log"] });
      await qc.invalidateQueries({ queryKey: ["nc-dead"] });
    } finally {
      setBusy(false);
    }
  };
  const steps: [string, string | null | undefined][] = d
    ? [
        ["Created", d.created_at],
        ["Accepted", d.sent_at],
        ["Delivered", d.delivered_at],
        ["Opened", d.opened_at],
        ["Bounced", d.bounced_at],
      ]
    : [];
  return (
    <>
      <div aria-hidden="true" onClick={onClose} className="fixed inset-0 z-[60] cursor-default bg-slate-950/30" />
      <aside
        aria-label="Message detail"
        role="dialog"
        aria-modal="true"
        className="fixed inset-0 z-[70] overflow-y-auto bg-white p-5 sm:inset-y-0 sm:left-auto sm:w-[30rem] sm:border-l sm:border-slate-200 sm:shadow-2xl"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-600">
              {d?.template ?? "Message"}
            </p>
            <h2 className="mt-1 text-lg font-bold text-slate-900">{d?.title ?? "Loading…"}</h2>
          </div>
          <QuietButton onClick={onClose} aria-label="Close detail">
            Close
          </QuietButton>
        </div>
        {d ? (
          <>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Tone tone={outcome(d).tone}>{outcome(d).label}</Tone>
              <span className="text-sm tabular-nums text-slate-700">
                {fmtMs(d.latency_ms)} to accept
              </span>
              {d.suppressed ? <Tone tone="bad">Address suppressed</Tone> : null}
            </div>
            <ol className="mt-5 space-y-2 border-l-2 border-slate-200 pl-4">
              {steps.map(([label, at]) => (
                <li key={label} className={cn("text-sm", at ? "text-slate-900" : "text-slate-400")}>
                  <span className="font-semibold">{label}</span>{" "}
                  <span className="tabular-nums">{when(at)}</span>
                </li>
              ))}
            </ol>
            <dl className="mt-5 grid grid-cols-[7rem_1fr] gap-y-2 text-sm">
              <dt className="text-slate-600">To</dt>
              <dd className="break-all text-slate-900">{d.recipient ?? "—"}</dd>
              <dt className="text-slate-600">Persona</dt>
              <dd className="text-slate-900">{d.persona}</dd>
              <dt className="text-slate-600">Event</dt>
              <dd className="text-slate-900">{d.event ?? "—"}</dd>
              <dt className="text-slate-600">Retries</dt>
              <dd className="tabular-nums text-slate-900">{d.retries}</dd>
              {d.failure ? (
                <>
                  <dt className="text-slate-600">Failure</dt>
                  <dd className="break-words font-mono text-xs text-red-800">{d.failure}</dd>
                </>
              ) : null}
            </dl>
            {d.replayable ? (
              <PrimaryButton className="mt-5 w-full" disabled={busy} onClick={replay}>
                {busy ? "Replaying…" : "Replay this message"}
              </PrimaryButton>
            ) : null}
            {d.attempts.length ? (
              <div className="mt-6">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                  Attempts
                </h3>
                <ul className="mt-2 divide-y divide-slate-100 text-sm">
                  {d.attempts.map((a, i) => (
                    <li key={i} className="flex justify-between gap-3 py-2">
                      <span className="text-slate-900">{a.status}</span>
                      <span className="truncate text-xs text-slate-600">
                        {a.error ?? when(a.at)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {d.html ? (
              <div className="mt-6">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                  As sent
                </h3>
                <iframe
                  title="Email as sent"
                  sandbox=""
                  srcDoc={d.html}
                  className="mt-2 h-[28rem] w-full rounded-xl border border-slate-200"
                />
              </div>
            ) : null}
          </>
        ) : null}
      </aside>
    </>
  );
}

function LogPanel({ onOpen, openId }: { onOpen: (id: string) => void; openId: string | null }) {
  const { getApiToken, ready } = useToken();
  const [f, setF] = useState<LogFilters>({});
  const { data, isLoading } = useQuery({
    queryKey: ["nc-log", f],
    enabled: ready,
    refetchInterval: 10_000,
    queryFn: async () => centerApi.log(await getApiToken(), f),
  });
  const set = (k: keyof LogFilters) => (v: string) => setF((p) => ({ ...p, [k]: v }));
  return (
    <div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <Select
          label="Persona"
          value={f.persona ?? ""}
          onChange={set("persona")}
          options={[["", "All"], ...PERSONAS.map((p) => [p, p] as [string, string])]}
        />
        <Select
          label="Event"
          value={f.event ?? ""}
          onChange={set("event")}
          options={[
            ["", "All"],
            ["order.delivered", "Delivered"],
            ["order.failed", "Failed attempt"],
            ["order.rescheduled", "Rescheduled"],
            ["order.in_transit", "Out for delivery"],
            ["notification.ops_digest", "Ops digest"],
          ]}
        />
        <Select
          label="Status"
          value={f.status ?? ""}
          onChange={set("status")}
          options={[
            ["", "All"],
            ["sent", "Accepted"],
            ["delivered", "Delivered"],
            ["opened", "Opened"],
            ["bounced", "Bounced"],
            ["held", "Held"],
            ["queued", "Queued"],
            ["failed", "Failed"],
            ["dead_letter", "Dead letter"],
          ]}
        />
        <Select
          label="Channel"
          value={f.channel ?? ""}
          onChange={set("channel")}
          options={[
            ["", "All"],
            ["email", "Email"],
            ["in_app", "In-app"],
            ["push", "Push"],
          ]}
        />
        <label className="col-span-2 flex flex-col gap-1 sm:col-span-1">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
            Search
          </span>
          <input
            value={f.q ?? ""}
            onChange={(e) => set("q")(e.target.value)}
            placeholder="email or id"
            className="h-10 rounded-lg border border-slate-300 px-3 text-sm text-slate-900 placeholder:text-slate-500 focus:border-[#2563eb] focus:outline-none focus:ring-2 focus:ring-[#2563eb]/30"
          />
        </label>
      </div>
      <div className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {isLoading ? (
          <p className="p-6 text-sm text-slate-600">Loading…</p>
        ) : data?.length ? (
          <ul className="divide-y divide-slate-100">
            {data.map((r) => (
              <Row key={r.id} r={r} onOpen={onOpen} active={openId === r.id} />
            ))}
          </ul>
        ) : (
          <Empty title="Nothing matches" hint="Clear a filter to see more." />
        )}
      </div>
      <p className="mt-2 text-xs text-slate-600">
        Refreshes every 10 s. Delivered and opened come from ZeptoMail webhooks.
      </p>
    </div>
  );
}

function DeadPanel({ onOpen }: { onOpen: (id: string) => void }) {
  const { getApiToken, ready } = useToken();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const { data } = useQuery({
    queryKey: ["nc-dead"],
    enabled: ready,
    queryFn: async () => centerApi.deadLetters(await getApiToken()),
  });
  const replayAll = async () => {
    setBusy(true);
    try {
      await centerApi.replayAll(await getApiToken());
      await qc.invalidateQueries();
    } finally {
      setBusy(false);
    }
  };
  if (!data?.length)
    return (
      <Empty title="Zero dead letters" hint="Every message either went out or is still retrying." />
    );
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-slate-700">
          <span className="text-2xl font-extrabold tabular-nums text-slate-900">{data.length}</span>{" "}
          gave up after 5 retries or a bad template.
        </p>
        <PrimaryButton disabled={busy} onClick={replayAll}>
          {busy ? "Replaying…" : "Replay all"}
        </PrimaryButton>
      </div>
      <ul className="mt-4 divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {data.map((r) => (
          <Row key={r.id} r={r} onOpen={onOpen} active={false} />
        ))}
      </ul>
    </div>
  );
}

function SuppressedPanel() {
  const { getApiToken, ready } = useToken();
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["nc-sup"],
    enabled: ready,
    queryFn: async () => centerApi.suppressions(await getApiToken()),
  });
  const release = async (email: string) => {
    if (!window.confirm(`Email ${email} again? Only do this if the person fixed their mailbox.`))
      return;
    await centerApi.release(await getApiToken(), email);
    await qc.invalidateQueries({ queryKey: ["nc-sup"] });
    await qc.invalidateQueries({ queryKey: ["nc-metrics"] });
  };
  if (!data?.length)
    return (
      <Empty
        title="No suppressed addresses"
        hint="Hard bounces and complaints land here automatically."
      />
    );
  return (
    <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200 bg-white">
      {data.map((s) => (
        <li key={s.email} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">{s.email}</p>
            <p className="text-xs text-slate-600">
              {s.reason.replace("_", " ")} · {s.count}× · since {when(s.since)}
            </p>
          </div>
          <QuietButton onClick={() => release(s.email)}>Unsuppress</QuietButton>
        </li>
      ))}
    </ul>
  );
}

export default function DeliveryCenter() {
  const { getApiToken, ready } = useToken();
  const [tab, setTab] = useState<Tab>("log");
  const [openId, setOpenId] = useState<string | null>(null);
  const { data: m } = useQuery({
    queryKey: ["nc-metrics"],
    enabled: ready,
    refetchInterval: 30_000,
    queryFn: async () => centerApi.metrics(await getApiToken()),
  });
  const badge = useMemo<Partial<Record<Tab, number>>>(
    () => ({ dead: m?.dead_letters ?? 0, suppressed: m?.suppressed ?? 0 }),
    [m]
  );
  return (
    <AdminPage>
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">
              Delivery center
            </h1>
            <p className="text-sm text-slate-600">Every email, how fast, and whether it landed.</p>
          </div>
          <Link
            href="/notifications"
            className="text-sm font-semibold text-[#1d4ed8] hover:underline"
          >
            My inbox →
          </Link>
        </header>
        <SpeedStrip m={m} />
        <nav aria-label="Sections" className="-mx-1 flex gap-1 overflow-x-auto px-1">
          {TABS.map(([k, label]) => (
            <button
              key={k}
              type="button"
              onClick={() => setTab(k)}
              aria-current={tab === k ? "page" : undefined}
              className={cn(
                "whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold",
                tab === k ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
              )}
            >
              {label}
              {badge[k] ? (
                <span
                  className={cn("ml-2 tabular-nums", tab === k ? "text-[#93c5fd]" : "text-red-700")}
                >
                  {badge[k]}
                </span>
              ) : null}
            </button>
          ))}
        </nav>
        {tab === "log" ? <LogPanel onOpen={setOpenId} openId={openId} /> : null}
        {tab === "dead" ? <DeadPanel onOpen={setOpenId} /> : null}
        {tab === "suppressed" ? <SuppressedPanel /> : null}
        {tab === "templates" ? <TemplateManager /> : null}
        {tab === "matrix" ? <MatrixPanel /> : null}
        {tab === "digest" ? <DigestPanel /> : null}
      </div>
      {openId ? <Detail id={openId} onClose={() => setOpenId(null)} /> : null}
    </AdminPage>
  );
}
