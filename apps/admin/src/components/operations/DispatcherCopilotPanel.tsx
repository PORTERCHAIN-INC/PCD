"use client";

import { useState } from "react";
import { Check, Pencil, Sparkles, X } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { ops, type CopilotAction } from "@/lib/operations";
import { formatSuggestionEta } from "@/lib/telemetryLabels";
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { relativeTime, titleCase } from "@/lib/crmFormat";

type LlmSuggestRow = {
  action: string;
  rationale: string;
  priority?: string;
  confidence?: number;
  auto_apply: boolean;
};

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
  const { data: aiOps } = useApiData((t) => ops.ai(t), [tick], { key: "ops-ai" });
  const [busy, setBusy] = useState<string | null>(null);
  const [modifyFor, setModifyFor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [llmBusy, setLlmBusy] = useState(false);
  const [llmError, setLlmError] = useState<string | null>(null);
  const [llmRows, setLlmRows] = useState<LlmSuggestRow[]>([]);
  const [llmMeta, setLlmMeta] = useState<{
    status?: string;
    provider?: string;
    model?: string;
    latency_ms?: number;
    tools_used?: string[];
  } | null>(null);

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

  async function askNim() {
    setLlmBusy(true);
    setLlmError(null);
    try {
      const token = await getApiToken();
      const risk = (aiOps?.risk_orders ?? [])
        .slice(0, 8)
        .map(
          (o) =>
            `${o.order_number || o.id}: state=${o.state} risk=${o.risk_score ?? "?"} ${(o.reasons ?? []).join(",")}`
        )
        .join("\n");
      const context =
        risk || "Ops board idle — suggest safe Operations checks and SLA queue hygiene.";
      const out = await ops.copilotLlmSuggest(token, {
        context: `PorterChain control tower snapshot:\n${context}\nRecommendation: ${aiOps?.recommendation ?? "n/a"}`,
        enable_intelligence: true,
        include_sla_queue: true,
      });
      setLlmRows(out.suggestions ?? []);
      const toolNames = (out.tools?.results ?? [])
        .map((row) =>
          row && typeof row === "object" && "tool" in row
            ? String((row as { tool?: string }).tool || "")
            : ""
        )
        .filter(Boolean);
      setLlmMeta({
        status: out.status,
        provider: out.provider,
        model: out.model,
        latency_ms: out.latency_ms,
        tools_used: toolNames,
      });
    } catch (e) {
      setLlmError(e instanceof Error ? e.message : "LLM suggest failed");
    } finally {
      setLlmBusy(false);
    }
  }

  if (loading && !data) return <Spinner />;

  const llm = aiOps?.llm;
  const phase2On = Boolean(aiOps?.phase2?.intelligence || aiOps?.phase2?.ai_dispatch);
  const nimTone = !llm?.configured ? "slate" : llm.circuit_open ? "amber" : "green";
  const askDisabled = llmBusy || !llm?.configured || Boolean(llm?.circuit_open) || !phase2On;

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
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={nimTone}>
              NIM{" "}
              {!llm ? "…" : !llm.configured ? "off" : llm.circuit_open ? "circuit open" : "ready"}
            </Badge>
            <Badge tone={phase2On ? "sky" : "slate"}>phase2 {phase2On ? "on" : "off"}</Badge>
            {llm?.configured && (
              <span className="text-[11px] text-muted truncate max-w-[280px]">{llm.model}</span>
            )}
            <Button
              type="button"
              variant="outline"
              disabled={askDisabled}
              onClick={() => void askNim()}
              className="text-xs px-3 py-1.5"
              title={
                !phase2On
                  ? "Set PORTERCHAIN_PHASE2_INTELLIGENCE=true and restart API"
                  : !llm?.configured
                    ? "Set NVIDIA_API_KEY"
                    : undefined
              }
            >
              {llmBusy ? "Asking NIM…" : "Ask NIM (read-only)"}
            </Button>
            <a href="/system?tab=ai" className="text-[11px] text-secondary hover:underline">
              AI usage →
            </a>
          </div>
          {!phase2On && llm?.configured ? (
            <p className="text-[11px] text-muted">
              NIM key is set but phase2 intelligence is off — enable PORTERCHAIN_PHASE2_INTELLIGENCE
              and restart the API.
            </p>
          ) : null}
          {llmError && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {llmError}
            </p>
          )}
          {llmRows.length > 0 && (
            <div className="space-y-2 rounded-2xl border border-primary/10 bg-gray-bg/40 p-3">
              <p className="text-[11px] text-muted">
                {llmMeta?.provider ?? "llm"} · {llmMeta?.status}
                {llmMeta?.latency_ms != null ? ` · ${llmMeta.latency_ms}ms` : ""}
                {llmMeta?.model ? ` · ${llmMeta.model}` : ""} — never auto-applies
              </p>
              {llmMeta?.tools_used && llmMeta.tools_used.length > 0 ? (
                <p className="text-[11px] text-muted">
                  Grounded with {llmMeta.tools_used.join(", ")}
                </p>
              ) : null}
              {llmRows.map((row) => (
                <div key={`${row.action}-${row.rationale.slice(0, 24)}`} className="text-sm">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-medium text-primary">{row.action}</span>
                    {row.priority && <Badge tone="slate">{row.priority}</Badge>}
                    {row.confidence != null && (
                      <Badge tone="slate">{Math.round(row.confidence * 100)}%</Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted mt-0.5">{row.rationale}</p>
                </div>
              ))}
            </div>
          )}
          <p className="text-xs text-muted">
            Concrete assign recommendations from Valhalla-ranked suggestions. Accept runs the
            existing dispatch assign path — never auto-assigns. Ask NIM grounds on the live SLA
            queue (read-only).
          </p>
          {error && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}
          {!data?.actions?.length ? (
            <EmptyState
              title={data?.pending_ranking ? "Ranking drivers…" : "No recommendations"}
              hint={data?.note}
            />
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
                    {a.rationale_narrative ? (
                      <p className="mt-1 text-[11px] text-secondary">{a.rationale_narrative}</p>
                    ) : null}
                    <p className="mt-1 text-[11px] text-muted">{(a.reasons ?? []).join(" · ")}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {a.savings_minutes != null && a.savings_minutes > 0 && (
                      <Badge tone="green">−{a.savings_minutes} min</Badge>
                    )}
                    {a.eta_minutes != null && (
                      <Badge tone="slate">
                        {formatSuggestionEta(a.eta_minutes, a.eta_source)} ETA
                      </Badge>
                    )}
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
                          {formatSuggestionEta(alt.eta_minutes, alt.eta_source)} · score {alt.score}
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
