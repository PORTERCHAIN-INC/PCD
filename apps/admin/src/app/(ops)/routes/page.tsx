"use client";

import {
  CheckCircle2,
  Clock,
  Fuel,
  Gauge,
  MapPin,
  Package,
  Route,
  Timer,
  Truck,
  Users,
} from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { routeCenter } from "@/lib/route-center";
import { Spinner } from "@/components/crm/primitives";
import {
  RouteErrorState,
  RouteKpiTile,
  RouteSectionCard,
} from "@/components/routes/RouteCenterPrimitives";

export default function RouteCenterDashboardPage() {
  const { data, error } = useApiData((t) => routeCenter.dashboard(t), [], { key: "route-dashboard" });

  if (error) return <RouteErrorState message={error} />;
  if (!data) return <Spinner label="Loading Route Center…" />;

  return (
    <div className="space-y-6">
      <RouteSectionCard
        title="Route Pipeline"
        description="Orders moving through planning, optimization, dispatch, and completion."
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <RouteKpiTile label="Waiting" value={String(data.routes_waiting)} icon={Clock} href="/routes/planning-queue" tone="warning" />
          <RouteKpiTile label="Planned" value={String(data.routes_planned)} icon={Route} href="/routes/builder" />
          <RouteKpiTile label="Optimized" value={String(data.routes_optimized)} icon={Gauge} href="/routes/optimization" />
          <RouteKpiTile label="Dispatched" value={String(data.routes_dispatched)} icon={Truck} href="/routes/dispatch" />
          <RouteKpiTile label="Active" value={String(data.routes_active)} icon={MapPin} href="/routes/live" tone="success" />
          <RouteKpiTile label="Completed" value={String(data.routes_completed)} icon={CheckCircle2} href="/routes/history" tone="success" />
        </div>
      </RouteSectionCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <RouteSectionCard title="Fleet Capacity" description="Available resources and queue depth.">
          <div className="grid gap-3 sm:grid-cols-2">
            <RouteKpiTile label="Drivers Available" value={String(data.drivers_available)} icon={Users} tone="success" />
            <RouteKpiTile label="Drivers Busy" value={String(data.drivers_busy)} icon={Users} />
            <RouteKpiTile label="Vehicles Available" value={String(data.vehicles_available)} icon={Truck} tone="success" />
            <RouteKpiTile label="Vehicles Busy" value={String(data.vehicles_busy)} icon={Truck} />
            <RouteKpiTile label="Orders Waiting" value={String(data.orders_waiting)} icon={Package} href="/routes/planning-queue" tone="warning" />
            <RouteKpiTile
              label="Capacity Utilization"
              value={`${data.capacity_utilization_pct}%`}
              icon={Gauge}
              tone={data.capacity_utilization_pct > 85 ? "danger" : data.capacity_utilization_pct > 65 ? "warning" : "default"}
            />
          </div>
        </RouteSectionCard>

        <RouteSectionCard title="Today's Performance" description="Distance, fuel, and on-time delivery metrics.">
          <div className="grid gap-3 sm:grid-cols-2">
            <RouteKpiTile label="Distance" value={`${data.todays_distance_km} km`} icon={MapPin} />
            <RouteKpiTile label="Fuel Estimate" value={`${data.fuel_estimate_liters} L`} icon={Fuel} />
            <RouteKpiTile label="Average ETA" value={`${data.average_eta_minutes} min`} icon={Timer} />
            <RouteKpiTile
              label="On-Time %"
              value={`${data.on_time_pct}%`}
              icon={CheckCircle2}
              tone={data.on_time_pct >= 90 ? "success" : data.on_time_pct >= 75 ? "warning" : "danger"}
            />
            <RouteKpiTile label="Late Routes" value={String(data.late_routes)} icon={Clock} tone={data.late_routes > 0 ? "danger" : "default"} />
            <RouteKpiTile label="In Flight" value={String(data.orders_in_flight)} icon={Package} href="/routes/live" />
          </div>
        </RouteSectionCard>
      </div>
    </div>
  );
}
