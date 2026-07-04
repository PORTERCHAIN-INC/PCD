"use client";

import Link from "next/link";
import { useApiData } from "@/hooks/useApiData";
import { routeCenter, type RoutePlan } from "@/lib/route-center";
import { Button, Spinner } from "@/components/crm/primitives";
import {
  RouteEmptyState,
  RouteErrorState,
  RoutePlanRow,
  RouteSectionCard,
} from "@/components/routes/RouteCenterPrimitives";

function formatWhen(iso?: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function RouteHistoryPage() {
  const { data, error } = useApiData((t) => routeCenter.history(t), [], { key: "route-history" });

  if (error) return <RouteErrorState message={error} />;
  if (!data) return <Spinner label="Loading history…" />;

  return (
    <RouteSectionCard title="Route History" description={`${data.length} completed or cancelled routes.`}>
      {data.length === 0 ? (
        <RouteEmptyState title="No route history yet" hint="Completed and cancelled routes will appear here." />
      ) : (
        <div className="space-y-3">
          {data.map((plan: RoutePlan) => (
            <RoutePlanRow
              key={plan.id}
              plan={plan}
              meta={
                <p className="mt-1 text-xs text-muted">
                  Completed {formatWhen(plan.completed_at ?? plan.updated_at)}
                </p>
              }
              actions={
                <Link href={`/routes/${plan.id}`}>
                  <Button variant="outline" className="px-2.5 py-1.5 text-xs">
                    Route 360
                  </Button>
                </Link>
              }
            />
          ))}
        </div>
      )}
    </RouteSectionCard>
  );
}
