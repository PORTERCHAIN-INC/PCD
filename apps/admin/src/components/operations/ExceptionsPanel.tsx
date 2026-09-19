"use client";

import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { ops } from "@/lib/operations";
import { Badge, Button, EmptyState, SectionCard } from "@/components/crm/primitives";
import { relativeTime, titleCase } from "@/lib/crmFormat";

function ExceptionAgeBadge({ createdAt }: { createdAt: string | null }) {
  if (!createdAt) return null;
  const hrs = (Date.now() - new Date(createdAt).getTime()) / 3_600_000;
  const tone = hrs >= 4 ? "red" : hrs >= 1 ? "amber" : "slate";
  return <Badge tone={tone}>{relativeTime(createdAt)}</Badge>;
}

export function ExceptionsPanel({
  tick,
  onOpenOrder,
}: {
  tick: number;
  onOpenOrder: (id: string) => void;
}) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => ops.exceptions(t), [tick], { key: "ops-exceptions" });
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [note, setNote] = useState("");

  async function run(id: string, fn: (token: string) => Promise<unknown>) {
    setBusy(id);
    setActionError(null);
    try {
      const token = await getApiToken();
      await fn(token);
      setResolvingId(null);
      setNote("");
      await refetch();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-3">
      {actionError && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {actionError}
        </p>
      )}
      <SectionCard title={`Exception center (${data?.length ?? 0})`}>
        <div className="divide-y divide-primary/5">
          {(data ?? []).map((e) => (
            <div key={e.id} className="px-5 py-3">
              <div className="flex items-start justify-between gap-3">
                <div
                  onClick={() => onOpenOrder(e.order_id)}
                  className="-mx-2 -my-1 min-w-0 flex-1 cursor-pointer rounded-lg px-2 py-1 transition-colors hover:bg-gray-bg/70"
                  title="Open Order 360"
                >
                  <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-primary">
                    {titleCase(e.type)}
                    <ExceptionAgeBadge createdAt={e.created_at} />
                  </p>
                  <p className="text-xs text-muted">
                    <span className="font-mono">{e.tracking_number}</span> · {e.merchant ?? "—"} ·
                    reported by {titleCase(e.reported_by)}
                    {e.order_state ? ` · order ${titleCase(e.order_state)}` : ""}
                  </p>
                  {e.acknowledged_by && (
                    <p className="mt-0.5 text-[11px] text-muted">
                      Acknowledged by {e.acknowledged_by} {relativeTime(e.acknowledged_at)}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
                  <Badge tone={e.status === "acknowledged" ? "blue" : "amber"}>
                    {titleCase(e.status)}
                  </Badge>
                  {e.status === "open" && (
                    <Button
                      variant="outline"
                      className="px-3 py-1.5 text-xs"
                      disabled={busy === e.id}
                      onClick={() => void run(e.id, (t) => ops.acknowledgeException(t, e.id))}
                    >
                      Acknowledge
                    </Button>
                  )}
                  {e.order_state === "FAILED" && (
                    <Button
                      variant="outline"
                      className="px-3 py-1.5 text-xs"
                      disabled={busy === e.id}
                      onClick={() => void run(e.id, (t) => ops.retryException(t, e.id))}
                    >
                      Retry dispatch
                    </Button>
                  )}
                  <Button
                    className="px-3 py-1.5 text-xs"
                    disabled={busy === e.id}
                    onClick={() => {
                      setResolvingId(resolvingId === e.id ? null : e.id);
                      setNote("");
                    }}
                  >
                    Resolve
                  </Button>
                  {e.customer_email && (
                    <a
                      href={`mailto:${e.customer_email}?subject=Delivery ${e.tracking_number}`}
                      className="inline-flex items-center gap-1 rounded-xl border border-primary/15 bg-white px-3 py-1.5 text-xs font-medium text-primary hover:bg-gray-bg"
                    >
                      Contact
                    </a>
                  )}
                </div>
              </div>
              {resolvingId === e.id && (
                <div className="mt-2 flex items-center gap-2 pl-2">
                  <input
                    value={note}
                    onChange={(ev) => setNote(ev.target.value)}
                    placeholder="Resolution note (optional)…"
                    className="w-72 rounded-xl border border-primary/15 px-3 py-1.5 text-sm outline-none focus:border-secondary"
                  />
                  <Button
                    className="px-3 py-1.5 text-xs"
                    disabled={busy === e.id}
                    onClick={() =>
                      void run(e.id, (t) => ops.resolveException(t, e.id, note || undefined))
                    }
                  >
                    Confirm resolve
                  </Button>
                  <Button
                    variant="ghost"
                    className="px-3 py-1.5 text-xs"
                    onClick={() => {
                      setResolvingId(null);
                      setNote("");
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              )}
            </div>
          ))}
          {(!data || data.length === 0) && <EmptyState title="No open exceptions" />}
        </div>
      </SectionCard>
    </div>
  );
}
