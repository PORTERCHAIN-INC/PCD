"use client";

import { useState } from "react";
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { routeCenter, type RoutePlan } from "@/lib/route-center";
import { Button, Field, Select, Spinner } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";
import {
  RouteErrorState,
  RoutePlanList,
  RouteSectionCard,
} from "@/components/routes/RouteCenterPrimitives";

const STRATEGIES = [
  "fastest",
  "shortest",
  "balanced",
  "lowest_fuel",
  "lowest_cost",
  "priority_deliveries",
  "time_windows",
  "merchant_sla",
  "custom",
];

export default function OptimizationPage() {
  const { getApiToken } = useAdminAuth();
  const [strategy, setStrategy] = useState("balanced");
  const [busyId, setBusyId] = useState<string | null>(null);
  const {
    data: plans,
    error,
    refetch,
  } = useApiData((t) => routeCenter.listPlans(t), [], { key: "route-plans" });

  const optimize = async (id: string) => {
    setBusyId(id);
    try {
      const token = await getApiToken();
      await routeCenter.optimizePlan(token, id, { strategy, engine: "valhalla" });
      refetch();
    } finally {
      setBusyId(null);
    }
  };

  if (error) return <RouteErrorState message={error} />;
  if (!plans) return <Spinner label="Loading optimization queue…" />;

  const candidates = plans.filter((p) => ["planned", "waiting", "optimized"].includes(p.status));

  return (
    <div className="space-y-6">
      <RouteSectionCard
        title="Optimization Strategy"
        description="Valhalla sequences multi-stop routes. OSRM refines distance matrix and ETAs."
      >
        <Field label="Strategy" hint="Applies to the next optimization run." className="max-w-sm">
          <Select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
            {STRATEGIES.map((s) => (
              <option key={s} value={s}>
                {titleCase(s.replace(/_/g, " "))}
              </option>
            ))}
          </Select>
        </Field>
      </RouteSectionCard>

      <RouteSectionCard
        title="Routes to Optimize"
        description={`${candidates.length} routes ready for optimization.`}
      >
        <RoutePlanList
          plans={candidates}
          emptyTitle="No routes ready to optimize"
          emptyHint="Create a plan in Route Builder first."
          renderMeta={(plan: RoutePlan) =>
            plan.simulation?.distance_meters ? (
              <p className="mt-1 text-xs text-muted">
                {Math.round(Number(plan.simulation.distance_meters) / 1000)} km ·{" "}
                {plan.simulation.duration_minutes} min · fuel {plan.simulation.fuel_liters} L
              </p>
            ) : null
          }
          renderActions={(plan) => (
            <>
              <Link href={`/routes/${plan.id}`}>
                <Button variant="outline" className="px-2.5 py-1.5 text-xs">
                  Preview
                </Button>
              </Link>
              <Button
                className="gap-1 px-2.5 py-1.5 text-xs"
                disabled={busyId === plan.id}
                onClick={() => optimize(plan.id)}
              >
                <Sparkles className="h-3.5 w-3.5" />
                {busyId === plan.id ? "Optimizing…" : "Optimize"}
              </Button>
            </>
          )}
        />
      </RouteSectionCard>
    </div>
  );
}
