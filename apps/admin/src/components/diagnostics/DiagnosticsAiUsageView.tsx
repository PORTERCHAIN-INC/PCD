"use client";

import { RefreshCw, Sparkles } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { Badge, Button } from "@/components/crm/primitives";
import { PageSkeleton } from "@porterchain/ui/loading";
import { SettingsCard, SettingsPageHeader } from "@/components/settings/ui/SettingsPrimitives";
import { useApiData } from "@/hooks/useApiData";
import { diagnosticsApi } from "@/lib/diagnostics";
import { relativeTime } from "@/lib/crmFormat";

export function DiagnosticsAiUsageView({ embedded = false }: { embedded?: boolean } = {}) {
  const { data, loading, error, refetch, isFetching } = useApiData(
    (t) => diagnosticsApi.aiUsage(t, 40),
    [],
    { key: "diagnostics-ai-usage", staleTime: 30_000 }
  );

  return (
    <div className="space-y-6">
      {!embedded ? (
        <SettingsPageHeader
          title="AI usage"
          description="NVIDIA NIM / LLM metering — read-only language assist. Never on pay or Valhalla."
          actions={
            <Button variant="outline" disabled={isFetching} onClick={() => void refetch()}>
              <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
              Refresh
            </Button>
          }
        />
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-primary">
            <Sparkles className="h-4 w-4 text-secondary" />
            AI usage (24h)
          </div>
          <Button variant="outline" disabled={isFetching} onClick={() => void refetch()}>
            <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
            Refresh
          </Button>
        </div>
      )}

      {loading && !data ? <PageSkeleton rows={3} /> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {data ? (
        <>
          <div className="flex flex-wrap gap-2">
            <Badge tone={data.nim.configured ? "green" : "slate"}>
              NIM {data.nim.configured ? "configured" : "unconfigured"}
            </Badge>
            <Badge tone={data.nim.circuit_open ? "red" : "slate"}>
              Circuit {data.nim.circuit_open ? "open" : "closed"}
            </Badge>
            <Badge tone={data.phase2.intelligence ? "sky" : "slate"}>
              phase2 intelligence {data.phase2.intelligence ? "on" : "off"}
            </Badge>
            <Badge tone={data.phase2.ai_dispatch ? "sky" : "slate"}>
              ai_dispatch {data.phase2.ai_dispatch ? "on" : "off"}
            </Badge>
            <span className="text-xs text-muted self-center">
              {data.nim.model} · checked {relativeTime(data.checked_at)}
            </span>
          </div>

          <SettingsCard
            title="By feature (24h)"
            description="Ops enrichers and Ask NIM — tokens are metering only"
          >
            {!data.by_feature.length ? (
              <p className="px-5 py-6 text-sm text-muted">
                No AI calls in the last 24 hours. Enable NVIDIA_API_KEY + phase2 to record usage.
              </p>
            ) : (
              <div className="divide-y divide-primary/5">
                {data.by_feature.map((row) => (
                  <div
                    key={`${row.feature}-${row.provider}`}
                    className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm"
                  >
                    <div>
                      <p className="font-medium text-primary">{row.feature}</p>
                      <p className="text-xs text-muted">{row.provider}</p>
                    </div>
                    <div className="text-right text-xs text-muted">
                      <p>
                        {row.calls} calls · {row.total_tokens} tokens
                      </p>
                      <p>
                        {row.errors > 0 ? (
                          <span className="text-red-600">{row.errors} errors</span>
                        ) : (
                          "0 errors"
                        )}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SettingsCard>

          <SettingsCard title="Recent calls" description="Latest ai_usage_logs rows">
            {!data.recent.length ? (
              <p className="px-5 py-6 text-sm text-muted">No rows yet.</p>
            ) : (
              <div className="divide-y divide-primary/5">
                {data.recent.map((row) => (
                  <div key={row.id} className="px-5 py-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-medium text-primary">
                        {row.feature}{" "}
                        <Badge tone={row.status === "ok" ? "green" : "red"}>{row.status}</Badge>
                      </p>
                      <p className="text-xs text-muted">
                        {row.created_at ? relativeTime(row.created_at) : "—"}
                        {row.latency_ms != null ? ` · ${row.latency_ms}ms` : ""}
                      </p>
                    </div>
                    <p className="mt-0.5 text-xs text-muted">
                      {row.provider} · {row.model} · {row.total_tokens} tokens
                    </p>
                    {row.error ? <p className="mt-1 text-xs text-red-600">{row.error}</p> : null}
                  </div>
                ))}
              </div>
            )}
          </SettingsCard>

          <p className="text-xs text-muted">
            Self-hosted NIM: set NVIDIA_API_BASE to your OpenAI-compatible endpoint when free-tier
            RPM (~40) saturates. See env/api.env.example.
          </p>
        </>
      ) : null}
    </div>
  );
}
