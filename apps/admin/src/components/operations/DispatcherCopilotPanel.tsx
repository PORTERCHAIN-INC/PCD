"use client";

import { useState } from "react";
import { Check, Pencil, Sparkles, X } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { ops, type CopilotAction } from "@/lib/operations";
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { relativeTime, titleCase } from "@/lib/crmFormat";

export function DispatcherCopilotPanel({
  tick,
  onOpenOrder,
  onChanged,
}: {
  tick: number;
  onOpenOrder: (id: string) => void;
  onChanged: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch, loading } = useApiData((t) => ops.copilot(t), [tick], {
    key: "ops-copilot",
  });
  const { data: audit } = useApiData((t) => ops.copilotAudit(t), [tick], {
    key: "ops-copilot-audit",
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [modifyFor, setModifyFor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function act(
    action: CopilotAction,
    kind: "accept" | "dismiss" | "modify",
    driverId?: string
  ) {
    setBusy(action.id);
    setError(null);
    try {
      const token = await getApiToken();
      if (kind === "accept") {
        await ops.copilotAccept(token, {
          action_id: action.id,
          order_id: action.order_id,
          driver_id: action.driver_id,
        });
      } else if (kind === "modify") {
        await ops.copilotModify(token, {
          action_id: action.id,
          order_id: action.order_id,
          driver_id: driverId || action.driver_id,
        });
        setModifyFor(null);
      } else {
        await ops.copilotDismiss(token, {
          action_id: action.id,
          order_id: action.order_id,
        });
      }
      await refetch();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  if (loading && !data) return <Spinner />;

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <SectionCard
        title={
          <span className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-secondary" /> Next-best actions
          </span>
        }
      >
        <div className="space-y-3 p-4">
          <p className="text-xs text-muted">
            Concrete assign recommendations from Valhalla-ranked suggestions. Accept runs the
            existing dispatch assign path — never auto-assigns.
          </p>
          {error && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}
          {!data?.actions?.length ? (
            <EmptyState title="No recommendations" hint={data?.note} />
          ) : (
            data.actions.map((a) => (
              <div
                key={a.id}
                className="rounded-2xl border border-primary/10 bg-white px-4 py-3 shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <button
                      type="button"
                      className="text-left text-sm font-semibold text-primary hover:text-secondary"
                      onClick={() => onOpenOrder(a.order_id)}
                    >
                      {a.title}
                    </button>
                    <p className="mt-0.5 text-xs text-muted">{a.summary}</p>
                    <p className="mt-1 text-[11px] text-muted">{(a.reasons ?? []).join(" · ")}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {a.savings_minutes != null && a.savings_minutes > 0 && (
                      <Badge tone="green">−{a.savings_minutes} min</Badge>
                    )}
                    {a.eta_minutes != null && <Badge tone="slate">{a.eta_minutes} min ETA</Badge>}
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    className="text-xs"
                    disabled={busy === a.id}
                    onClick={() => void act(a, "accept")}
                  >
                    <Check className="h-3.5 w-3.5" /> Accept
                  </Button>
                  <Button
                    variant="outline"
                    className="text-xs"
                    disabled={busy === a.id}
                    onClick={() => setModifyFor(modifyFor === a.id ? null : a.id)}
                  >
                    <Pencil className="h-3.5 w-3.5" /> Modify
                  </Button>
                  <Button
                    variant="ghost"
                    className="text-xs"
                    disabled={busy === a.id}
                    onClick={() => void act(a, "dismiss")}
                  >
                    <X className="h-3.5 w-3.5" /> Dismiss
                  </Button>
                </div>
                {modifyFor === a.id && (
                  <div className="mt-2 space-y-1 rounded-xl border border-primary/10 bg-gray-bg/50 p-2">
                    <p className="text-[11px] font-medium text-muted">Pick alternate driver</p>
                    {(a.alternates ?? []).map((alt) => (
                      <button
                        key={alt.driver_id}
                        type="button"
                        disabled={busy === a.id}
                        onClick={() => void act(a, "modify", alt.driver_id)}
                        className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-sm hover:bg-white"
                      >
                        <span>{alt.driver_name}</span>
                        <span className="text-xs text-muted">
                          {alt.eta_minutes != null ? `${alt.eta_minutes} min` : "—"} · score{" "}
                          {alt.score}
                        </span>
                      </button>
                    ))}
                    {!a.alternates?.length && (
                      <p className="px-2 py-1 text-xs text-muted">No alternates ranked.</p>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </SectionCard>

      <SectionCard title="Override audit trail">
        <div className="divide-y divide-primary/5">
          {(audit ?? []).map((e) => (
            <div key={e.id} className="px-4 py-2.5">
              <p className="text-sm text-primary">
                {titleCase(e.event_type.replace("ops.copilot.", "").replace(/\./g, " "))}
              </p>
              <p className="text-xs text-muted">
                Order {e.order_id.slice(0, 8)}… · {relativeTime(e.occurred_at)}
                {e.payload?.driver_id
                  ? ` · driver ${String(e.payload.driver_id).slice(0, 8)}…`
                  : ""}
                {e.payload?.modified ? " · modified" : ""}
              </p>
            </div>
          ))}
          {(!audit || audit.length === 0) && (
            <EmptyState
              title="No copilot actions yet"
              hint="Accept, modify, or dismiss to audit."
            />
          )}
        </div>
      </SectionCard>
    </div>
  );
}
