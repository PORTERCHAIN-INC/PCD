"use client";

import Link from "next/link";
import {
  CheckCircle2,
  Clock,
  Fuel,
  Gauge,
  MapPin,
  TrendingDown,
  TrendingUp,
  Truck,
  Users,
} from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { routeCenter } from "@/lib/route-center";
import { Spinner } from "@/components/crm/primitives";
import { money } from "@/lib/crmFormat";
import {
  RouteErrorState,
  RouteKpiTile,
  RouteSectionCard,
} from "@/components/routes/RouteCenterPrimitives";

export default function RouteAnalyticsPage() {
  const { data, error } = useApiData((t) => routeCenter.analytics(t), [], {
    key: "route-analytics",
  });

  if (error) return <RouteErrorState message={error} />;
  if (!data) return <Spinner label="Loading analytics…" />;

  return (
    <div className="space-y-6">
      <RouteSectionCard
        title="Efficiency Gains"
        description="Savings from route optimization vs. unoptimized baselines."
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <RouteKpiTile
            label="Distance Saved"
            value={`${data.distance_saved_km} km`}
            icon={MapPin}
            tone="success"
          />
          <RouteKpiTile
            label="Fuel Saved"
            value={`${data.fuel_saved_liters} L`}
            icon={Fuel}
            tone="success"
          />
          <RouteKpiTile
            label="Time Saved"
            value={`${data.time_saved_minutes} min`}
            icon={Clock}
            tone="success"
          />
        </div>
      </RouteSectionCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <RouteSectionCard title="Financial Performance">
          <div className="grid gap-3 sm:grid-cols-2">
            <RouteKpiTile
              label="Revenue"
              value={money(data.revenue_cents ?? 0)}
              icon={TrendingUp}
            />
            <RouteKpiTile
              label="Profit"
              value={money(data.profit_cents ?? 0)}
              icon={TrendingUp}
              tone="success"
            />
            <RouteKpiTile
              label="Avg Stops / Route"
              value={String(data.average_stops)}
              icon={MapPin}
            />
            <RouteKpiTile
              label="Failed Routes"
              value={String(data.failed_routes)}
              icon={TrendingDown}
              tone={data.failed_routes > 0 ? "danger" : "default"}
            />
          </div>
        </RouteSectionCard>

        <RouteSectionCard title="Utilization & Reliability">
          <div className="grid gap-3 sm:grid-cols-2">
            <RouteKpiTile
              label="Driver Utilization"
              value={`${data.driver_utilization_pct}%`}
              icon={Users}
            />
            <RouteKpiTile
              label="Vehicle Utilization"
              value={`${data.vehicle_utilization_pct}%`}
              icon={Truck}
            />
            <RouteKpiTile
              label="On-Time %"
              value={`${data.on_time_pct}%`}
              icon={CheckCircle2}
              tone={data.on_time_pct >= 90 ? "success" : "warning"}
            />
            <RouteKpiTile
              label="Late %"
              value={`${data.late_pct}%`}
              icon={Gauge}
              tone={data.late_pct > 10 ? "danger" : "default"}
            />
          </div>
        </RouteSectionCard>
      </div>

      <p className="text-center text-xs text-muted">
        For trend charts and date ranges, see{" "}
        <Link href="/reports" className="font-medium text-secondary hover:underline">
          Reports
        </Link>
        .
      </p>
    </div>
  );
}
