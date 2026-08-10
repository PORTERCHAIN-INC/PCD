"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Sparkles, X } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { ordersApi, type AssistPayload, type AssistProposal, type Playbook } from "@/lib/orders";
import { Badge, Button, EmptyState, Spinner } from "@/components/crm/primitives";

export function OrderAssistPanel({
  orderId,
  onChanged,
  onOpenAssign,
  onOpenException,
  compact,
}: {
  orderId: string;
  onChanged?: () => void;
  onOpenAssign?: () => void;
  onOpenException?: (suggested?: string) => void;
  compact?: boolean;
}) {
  const { getApiToken } = useAdminAuth();
  const [data, setData] = useState<AssistPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      setData(await ordersApi.assist(token, orderId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Assist failed to load");
    } finally {
      setLoading(false);
    }
  }, [getApiToken, orderId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(proposal: AssistProposal, decision: "accept" | "reject") {
    setBusy(proposal.id);
    setError(null);
    setInfo(null);
    try {
      if (decision === "accept" && proposal.kind === "exception_coach") {
        onOpenException?.(String(proposal.payload?.suggested_state || ""));
        const token = await getApiToken();
        await ordersApi.assistDecide(token, orderId, {
          proposal_id: proposal.id,
          decision: "accept",
        });
        setInfo("Open Mark exception and enter a reason — assist will not auto-transition.");
        await load();
        return;
      }
      if (decision === "accept" && (proposal.kind === "assign" || proposal.kind === "reassign")) {
        // Prefer shared Assign modal when available; else API accept.
        if (onOpenAssign) {
          onOpenAssign();
          const token = await getApiToken();
          await ordersApi.assistDecide(token, orderId, {
            proposal_id: proposal.id,
            decision: "accept",
            payload: proposal.payload,
          });
          await load();
          onChanged?.();
          return;
        }
      }
      const token = await getApiToken();
      const res = await ordersApi.assistDecide(token, orderId, {
        proposal_id: proposal.id,
        decision,
        payload: proposal.payload,
      });
      setInfo(
        decision === "accept"
          ? `Accepted: ${proposal.title}`
          : `Rejected proposal ${proposal.id.slice(0, 8)}`
      );
      if (res.result && typeof res.result === "object" && "claim_id" in (res.result as object)) {
        setInfo(`Claim opened`);
      }
      await load();
      onChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Decision failed");
    } finally {
      setBusy(null);
    }
  }

  async function runPlaybook(pb: Playbook) {
    if (!pb.enabled) return;
    if (!window.confirm(`Run playbook “${pb.label}”? This will write using existing APIs.`)) return;
    setBusy(pb.id);
    setError(null);
    setInfo(null);
    try {
      const token = await getApiToken();
      const res = await ordersApi.runPlaybook(token, orderId, pb.id, { confirm: true });
      setInfo(`${pb.label} completed`);
      if (res.result && typeof res.result === "object" && "claim_id" in (res.result as object)) {
        const claimId = String((res.result as { claim_id: string }).claim_id);
        setInfo(`Claim ${claimId.slice(0, 8)}… opened`);
      }
      await load();
      onChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Playbook failed");
    } finally {
      setBusy(null);
    }
  }

  if (loading && !data) {
    return (
      <div className="py-6">
        <Spinner label="Loading assist…" />
      </div>
    );
  }

  return (
    <div className={compact ? "space-y-3" : "space-y-5"}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold text-primary">
            <Sparkles className="h-4 w-4 text-secondary" />
            Order assist
          </p>
          <p className="mt-0.5 text-xs text-muted">
            Propose · human confirms. Never advances Accept→Delivered (Fleetbase-owned).
          </p>
        </div>
        <Button variant="outline" className="px-2 py-1 text-xs" onClick={() => void load()}>
          Refresh
        </Button>
      </div>

      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {info && (
        <p className="rounded-xl border border-secondary/20 bg-secondary/5 px-3 py-2 text-sm text-primary">
          {info}
        </p>
      )}

      <div>
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
          Playbooks
        </p>
        <div className="flex flex-wrap gap-1.5">
          {(data?.playbooks ?? []).map((pb) => (
            <Button
              key={pb.id}
              variant="outline"
              className="px-2 py-1 text-xs"
              disabled={!pb.enabled || busy === pb.id}
              title={pb.disabled_reason || pb.description}
              onClick={() => void runPlaybook(pb)}
            >
              {busy === pb.id ? "…" : pb.label}
            </Button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
          Proposals
        </p>
        {!data?.proposals?.length ? (
          <EmptyState title="No proposals" hint="State has no ranked assist actions right now." />
        ) : (
          <div className="space-y-2">
            {data.proposals.map((p) => (
              <div
                key={p.id}
                className="rounded-xl border border-primary/10 bg-white px-3 py-2.5 shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-primary">{p.title}</p>
                      <Badge tone={p.confidence === "high" ? "green" : "slate"}>
                        {p.confidence}
                      </Badge>
                      <span className="text-[10px] uppercase tracking-wide text-muted">
                        {p.kind}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-muted">{p.summary}</p>
                    {p.preview?.sms || p.preview?.email_body ? (
                      <pre className="mt-2 max-h-28 overflow-auto rounded-lg bg-gray-bg p-2 text-[11px] text-primary/80 whitespace-pre-wrap">
                        {String(p.preview.email_body || p.preview.sms)}
                      </pre>
                    ) : null}
                    {Array.isArray(p.preview?.bullets) ? (
                      <ul className="mt-1 list-disc pl-4 text-xs text-muted">
                        {(p.preview.bullets as string[]).map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    ) : null}
                    {Array.isArray(p.preview?.reasons) ? (
                      <ul className="mt-1 list-disc pl-4 text-xs text-muted">
                        {(p.preview.reasons as string[]).slice(0, 3).map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                  {p.requires_confirm ? (
                    <div className="flex shrink-0 gap-1">
                      <Button
                        className="px-2 py-1 text-xs"
                        disabled={busy === p.id}
                        onClick={() => void decide(p, "accept")}
                      >
                        <Check className="h-3.5 w-3.5" /> Confirm
                      </Button>
                      <Button
                        variant="outline"
                        className="px-2 py-1 text-xs"
                        disabled={busy === p.id}
                        onClick={() => void decide(p, "reject")}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
