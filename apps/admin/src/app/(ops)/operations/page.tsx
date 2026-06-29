"use client";

import { useState } from "react";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { api } from "@/lib/api";

export default function OperationsPage() {
  const { data: queue } = useApiData((t) => api.dispatchQueue(t));
  const { data: exceptions } = useApiData((t) => api.claims(t));
  const { getApiToken } = useAdminAuth();
  const [ssoLoading, setSsoLoading] = useState(false);

  async function openFleetbaseConsole() {
    setSsoLoading(true);
    try {
      const token = await getApiToken();
      const session = await api.fleetbaseSso(token);
      window.open(session.console_url, "_blank", "noopener,noreferrer");
    } finally {
      setSsoLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-primary">Operations</h1>
        <button
          type="button"
          onClick={openFleetbaseConsole}
          disabled={ssoLoading}
          className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {ssoLoading ? "Opening…" : "Open Fleetbase Console (SSO)"}
        </button>
      </div>
      <section>
        <h2 className="mb-3 font-semibold">Dispatch Queue</h2>
        <div className="rounded-2xl border border-primary/10 bg-white">
          {(queue || []).map((o) => (
            <div key={String(o.order_id)} className="flex justify-between border-b border-primary/5 px-4 py-3 text-sm">
              <span className="font-mono">{String(o.tracking_number)}</span>
              <span className="text-muted">{String(o.state)}</span>
            </div>
          ))}
          {(!queue || queue.length === 0) && <p className="p-6 text-center text-muted">Queue empty</p>}
        </div>
      </section>
      <section>
        <h2 className="mb-3 font-semibold">Exception / Claims Queue</h2>
        <div className="rounded-2xl border border-primary/10 bg-white">
          {(exceptions || []).slice(0, 20).map((c) => (
            <div key={String(c.id)} className="border-b border-primary/5 px-4 py-3 text-sm">
              <span className="font-medium">{String(c.claim_type)}</span>
              <span className="ml-2 text-muted">{String(c.status)}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
