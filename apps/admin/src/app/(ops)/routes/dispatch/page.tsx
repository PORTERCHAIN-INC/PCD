"use client";

import { useState } from "react";
import Link from "next/link";
import { Send } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { ops, type AssignableDriver } from "@/lib/operations";
import { routeCenter, type RoutePlan } from "@/lib/route-center";
import { Button, Select, Spinner } from "@/components/crm/primitives";
import {
  RouteErrorState,
  RoutePlanList,
  RouteSectionCard,
} from "@/components/routes/RouteCenterPrimitives";

export default function DispatchPage() {
  const { getApiToken } = useAdminAuth();
  const [driverByPlan, setDriverByPlan] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const {
    data: plans,
    error,
    refetch,
  } = useApiData((t) => routeCenter.listPlans(t, { status: "optimized" }), [], {
    key: "route-dispatch-plans",
  });
  const { data: drivers } = useApiData((t) => ops.assignableDrivers(t), [], {
    key: "ops-assignable-drivers",
  });

  const dispatch = async (planId: string) => {
    const driverId = driverByPlan[planId];
    if (!driverId) return;
    setBusyId(planId);
    try {
      const token = await getApiToken();
      await routeCenter.dispatchPlan(token, planId, { driver_id: driverId });
      refetch();
    } finally {
      setBusyId(null);
    }
  };

  if (error) return <RouteErrorState message={error} />;
  if (!plans) return <Spinner label="Loading dispatch queue…" />;

  return (
    <div className="space-y-6">
      <RouteSectionCard
        title="Dispatch Queue"
        description="Assign a driver per route, then dispatch through the Fleetbase adapter."
      >
        <RoutePlanList
          plans={plans}
          emptyTitle="No optimized routes ready"
          emptyHint="Run optimization on planned routes first."
          renderActions={(plan: RoutePlan) => {
            const driverId = driverByPlan[plan.id] ?? "";
            return (
              <>
                <Select
                  value={driverId}
                  onChange={(e) =>
                    setDriverByPlan((prev) => ({ ...prev, [plan.id]: e.target.value }))
                  }
                  className="min-w-[180px] text-xs"
                >
                  <option value="">Select driver…</option>
                  {(drivers ?? []).map((d: AssignableDriver) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                      {d.online ? " · online" : ""}
                    </option>
                  ))}
                </Select>
                <Button
                  className="gap-1 px-2.5 py-1.5 text-xs"
                  disabled={!driverId || busyId === plan.id}
                  onClick={() => dispatch(plan.id)}
                >
                  <Send className="h-3.5 w-3.5" />
                  {busyId === plan.id ? "Dispatching…" : "Dispatch"}
                </Button>
                <Link href={`/routes/${plan.id}`}>
                  <Button variant="outline" className="px-2.5 py-1.5 text-xs">
                    Route 360
                  </Button>
                </Link>
              </>
            );
          }}
        />
      </RouteSectionCard>
    </div>
  );
}
