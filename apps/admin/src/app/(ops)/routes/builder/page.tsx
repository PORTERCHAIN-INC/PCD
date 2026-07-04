"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Plus } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { routeCenter } from "@/lib/route-center";
import { Button, Field, Input, Spinner } from "@/components/crm/primitives";
import {
  RouteErrorState,
  RoutePlanList,
  RouteSectionCard,
} from "@/components/routes/RouteCenterPrimitives";

export default function RouteBuilderPage() {
  const params = useSearchParams();
  const prefill = params.get("orders")?.split(",").filter(Boolean) ?? [];
  const { getApiToken } = useAdminAuth();
  const [name, setName] = useState(`Route ${new Date().toLocaleDateString()}`);
  const [busy, setBusy] = useState(false);
  const { data: plans, error, refetch } = useApiData((t) => routeCenter.listPlans(t), [], { key: "route-plans" });

  const createRoute = useCallback(async () => {
    setBusy(true);
    try {
      const token = await getApiToken();
      await routeCenter.createPlan(token, { name, order_ids: prefill, strategy: "balanced" });
      refetch();
    } finally {
      setBusy(false);
    }
  }, [getApiToken, name, prefill, refetch]);

  if (error) return <RouteErrorState message={error} />;
  if (!plans) return <Spinner label="Loading routes…" />;

  return (
    <div className="space-y-6">
      <RouteSectionCard
        title="Create Route Plan"
        description="Name your route and attach orders from the planning queue or start empty."
      >
        <div className="flex flex-wrap items-end gap-4">
          <Field label="Route name" className="min-w-[240px] flex-1">
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Morning GTA West" />
          </Field>
          <Button onClick={createRoute} disabled={busy} className="gap-2">
            <Plus className="h-4 w-4" />
            {prefill.length ? `Create with ${prefill.length} orders` : "Create empty route"}
          </Button>
        </div>
        {prefill.length > 0 && (
          <p className="mt-3 rounded-xl border border-secondary/20 bg-secondary/5 px-3 py-2 text-xs text-muted">
            <span className="font-medium text-primary">{prefill.length} orders</span> pre-selected from planning queue.
          </p>
        )}
      </RouteSectionCard>

      <RouteSectionCard title="Route Plans" description={`${plans.length} active and draft plans.`}>
        <RoutePlanList
          plans={plans}
          emptyTitle="No route plans yet"
          emptyHint="Create a plan above or start from a template."
        />
      </RouteSectionCard>
    </div>
  );
}
