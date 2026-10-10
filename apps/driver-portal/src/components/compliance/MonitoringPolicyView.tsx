"use client";

import { useEffect, useState } from "react";
import { driverApi, type MonitoringPolicy } from "@/lib/api";

/** Ontario ESA electronic monitoring policy: read anytime, acknowledge with timestamp + version. */
export default function MonitoringPolicyView({ compact = false }: { compact?: boolean }) {
  const [policy, setPolicy] = useState<MonitoringPolicy | null>(null);
  const [open, setOpen] = useState(!compact);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    driverApi
      .monitoringPolicy()
      .then(setPolicy)
      .catch(() => setError("Could not load the monitoring policy."));
  }, []);

  async function acknowledge() {
    setBusy(true);
    try {
      setPolicy(await driverApi.ackMonitoringPolicy());
    } catch {
      setError("Could not save. Try again.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !policy)
    return (
      <p role="alert" className="text-sm text-red-700">
        {error}
      </p>
    );
  if (!policy) return null;
  return (
    <section
      aria-labelledby="monitoring-policy-title"
      className="rounded-2xl bg-white p-5 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="monitoring-policy-title" className="text-lg font-bold text-[var(--primary)]">
            {policy.title}
          </h2>
          <p className="text-xs text-[var(--muted)]">
            Version {policy.version} · effective {policy.date}
          </p>
        </div>
        {compact ? (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="text-sm font-semibold text-[var(--secondary)] underline"
          >
            {open ? "Hide" : "Read policy"}
          </button>
        ) : null}
      </div>
      {open ? (
        <div className="mt-4 space-y-4 text-sm text-[var(--primary)]">
          {policy.sections.map((s) => (
            <div key={s.heading}>
              <h3 className="font-semibold">{s.heading}</h3>
              {s.body ? <p className="mt-1">{s.body}</p> : null}
              {s.items ? (
                <ul className="mt-1 list-disc space-y-1 pl-5">
                  {s.items.map((i) => (
                    <li key={i}>{i}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
      <div className="mt-4">
        {policy.acknowledged && policy.acknowledgment ? (
          <p className="text-sm text-emerald-800">
            You acknowledged version {policy.acknowledgment.version} on{" "}
            {new Date(policy.acknowledgment.at).toLocaleString()}.
          </p>
        ) : (
          <button
            type="button"
            onClick={() => void acknowledge()}
            disabled={busy}
            className="min-h-11 rounded-xl bg-[var(--secondary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {busy ? "Saving…" : "I have read and understand this policy"}
          </button>
        )}
        {error ? (
          <p role="alert" className="mt-2 text-sm text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}
