"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RefreshCw, X } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import ClaimsGrid from "@/components/claims/ClaimsGrid";
import { Button, Spinner } from "@/components/crm/primitives";
import { CLAIM_STATUSES, CLAIM_TYPES, claimsApi, type ClaimFilters } from "@/lib/claims";

export default function ClaimsPage() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const searchParams = useSearchParams();
  const qc = useQueryClient();
  const [filters, setFilters] = useState<ClaimFilters>({});
  const [selected, setSelected] = useState<string[]>([]);
  const filterKey = JSON.stringify(filters);

  useEffect(() => {
    const customerId = searchParams.get("customer_id");
    const merchantId = searchParams.get("merchant_id");
    if (!customerId && !merchantId) return;
    setFilters((f) => ({
      ...f,
      ...(customerId ? { customer_id: customerId } : {}),
      ...(merchantId ? { merchant_id: merchantId } : {}),
    }));
  }, [searchParams]);

  const {
    data: rows = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["claims", filterKey],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const token = await getApiToken();
      return claimsApi.list(token, filters);
    },
  });

  const { data: dashboard } = useQuery({
    queryKey: ["claims-dashboard"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const token = await getApiToken();
      return claimsApi.dashboard(token);
    },
  });

  async function createClaim() {
    const orderId = prompt("Order ID");
    const claimType = prompt(`Claim type:\n${CLAIM_TYPES.join("\n")}`);
    if (!orderId || !claimType) return;
    const token = await getApiToken();
    await claimsApi.create(token, { order_id: orderId, claim_type: claimType });
    await qc.invalidateQueries({ queryKey: ["claims"] });
    await qc.invalidateQueries({ queryKey: ["claims-dashboard"] });
    void refetch();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Claims Management</h1>
          <p className="text-sm text-muted">
            Logistics claims platform — investigation, compensation, and insurance
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void refetch()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
          <Button variant="primary" onClick={() => void createClaim()}>
            <Plus className="h-4 w-4" /> New claim
          </Button>
        </div>
      </div>

      {dashboard && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
          <Kpi label="Open" value={dashboard.open_claims} />
          <Kpi label="Investigating" value={dashboard.under_investigation} />
          <Kpi label="Waiting customer" value={dashboard.waiting_customer} />
          <Kpi label="Waiting merchant" value={dashboard.waiting_merchant} />
          <Kpi label="Insurance" value={dashboard.insurance_claims} />
          <Kpi
            label="Chargebacks"
            value={dashboard.chargebacks}
            alert={dashboard.chargebacks > 0}
          />
          <Kpi label="Resolved" value={dashboard.resolved_claims} />
          <Kpi label="Rejected" value={dashboard.rejected_claims} />
          <Kpi label="Avg resolution" value={`${dashboard.avg_resolution_hours}h`} />
          <Kpi label="Compensation" value={formatCents(dashboard.total_compensation_cents)} />
          <Kpi label="This month" value={dashboard.monthly_claims} />
          <Kpi label="Avg risk" value={String(dashboard.avg_risk_score)} />
        </div>
      )}

      <div className="rounded-2xl border border-primary/10 bg-white p-4">
        {(filters.customer_id || filters.merchant_id) && (
          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl bg-secondary/5 px-3 py-2 text-sm">
            {filters.customer_id && (
              <span className="text-primary">
                Customer filter: <code className="text-xs">{filters.customer_id}</code>
              </span>
            )}
            {filters.merchant_id && (
              <span className="text-primary">
                Merchant filter: <code className="text-xs">{filters.merchant_id}</code>
              </span>
            )}
            <Button
              variant="ghost"
              className="text-xs"
              onClick={() =>
                setFilters((f) => {
                  const next = { ...f };
                  delete next.customer_id;
                  delete next.merchant_id;
                  return next;
                })
              }
            >
              <X className="h-3.5 w-3.5" /> Clear entity filter
            </Button>
          </div>
        )}
        <div className="mb-4 flex flex-wrap gap-2">
          <input
            type="search"
            placeholder="Claim #, tracking, merchant, email…"
            value={filters.search ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
            className="min-w-[200px] flex-1 rounded-xl border border-primary/10 px-3 py-2 text-sm"
          />
          <select
            value={filters.status ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {CLAIM_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <select
            value={filters.claim_type ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, claim_type: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All types</option>
            {CLAIM_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <select
            value={filters.priority ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, priority: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">Priority</option>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <input
            type="number"
            placeholder="Min risk"
            value={filters.risk_min ?? ""}
            onChange={(e) =>
              setFilters((f) => ({
                ...f,
                risk_min: e.target.value ? Number(e.target.value) : undefined,
              }))
            }
            className="w-24 rounded-xl border border-primary/10 px-3 py-2 text-sm"
          />
        </div>

        {selected.length > 0 && (
          <div className="mb-3 flex gap-2 rounded-xl bg-secondary/5 px-3 py-2">
            <span className="text-sm font-medium">{selected.length} selected</span>
            <Button
              variant="outline"
              onClick={async () => {
                const token = await getApiToken();
                await claimsApi.bulk(token, selected, "status", { status: "under_investigation" });
                setSelected([]);
                void refetch();
              }}
            >
              Bulk investigate
            </Button>
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        ) : (
          <ClaimsGrid rows={rows} selected={selected} onSelect={setSelected} />
        )}
      </div>
    </div>
  );
}

function Kpi({ label, value, alert }: { label: string; value: string | number; alert?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-primary/10 bg-white px-3 py-2 shadow-sm",
        alert && "border-amber-200 bg-amber-50"
      )}
    >
      <p className="text-xs text-muted">{label}</p>
      <p className="text-lg font-bold text-primary">{value}</p>
    </div>
  );
}
