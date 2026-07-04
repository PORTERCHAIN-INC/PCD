"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  BarChart3,
  ClipboardList,
  Map,
  Package,
  ScrollText,
  Sparkles,
  Truck,
  User,
} from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { routeCenter } from "@/lib/route-center";
import { Button, Spinner } from "@/components/crm/primitives";
import { money, titleCase } from "@/lib/crmFormat";
import { cn } from "@porterchain/ui/utils";
import {
  Route360Header,
  RouteEmptyState,
  RouteErrorState,
  RouteSectionCard,
  RouteStopTimeline,
} from "@/components/routes/RouteCenterPrimitives";

const TABS = [
  { id: "overview", label: "Overview", icon: ClipboardList },
  { id: "stops", label: "Stops", icon: Map },
  { id: "orders", label: "Orders", icon: Package },
  { id: "driver", label: "Driver", icon: User },
  { id: "vehicle", label: "Vehicle", icon: Truck },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "audit", label: "Audit Log", icon: ScrollText },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function Route360Page() {
  const { id } = useParams<{ id: string }>();
  const [tab, setTab] = useState<TabId>("overview");
  const { getApiToken } = useAdminAuth();
  const { data: plan, error, refetch } = useApiData((t) => routeCenter.getPlan(t, id), [id]);

  const simulate = async () => {
    const token = await getApiToken();
    await routeCenter.simulatePlan(token, id);
    refetch();
  };

  if (error) return <RouteErrorState message={error} />;
  if (!plan) return <Spinner label="Loading Route 360…" />;

  const sim = plan.simulation ?? {};
  const rec = plan.recommendations ?? {};

  return (
    <div className="space-y-6">
      <Link
        href="/routes/builder"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-secondary"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Route Builder
      </Link>

      <Route360Header
        plan={plan}
        actions={
          <>
            <Button variant="outline" className="gap-2" onClick={simulate}>
              <Sparkles className="h-4 w-4" />
              Simulate
            </Button>
            <Link href={`/routes/dispatch`}>
              <Button className="gap-2">Go to Dispatch</Button>
            </Link>
          </>
        }
      />

      <div className="flex gap-1 overflow-x-auto rounded-2xl border border-primary/10 bg-gray-bg/60 p-1">
        {TABS.map(({ id: tid, label, icon: Icon }) => (
          <button
            key={tid}
            type="button"
            onClick={() => setTab(tid)}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
              tab === tid
                ? "bg-white text-secondary shadow-sm"
                : "text-primary/70 hover:bg-white/70"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <RouteSectionCard title="Route Simulation">
            <dl className="grid grid-cols-2 gap-4 text-sm">
              {[
                ["Distance", `${Math.round(Number(sim.distance_meters ?? 0) / 1000)} km`],
                ["Travel time", `${sim.duration_minutes ?? "—"} min`],
                ["Fuel", `${sim.fuel_liters ?? "—"} L`],
                ["Est. cost", money(Number(sim.estimated_cost_cents ?? 0))],
                ["Revenue", money(Number(sim.estimated_revenue_cents ?? 0))],
                ["Profit", money(Number(sim.estimated_profit_cents ?? 0))],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-xl border border-primary/10 bg-gray-bg/30 px-3 py-2.5"
                >
                  <dt className="text-xs text-muted">{label}</dt>
                  <dd className="mt-0.5 font-semibold text-primary">{value}</dd>
                </div>
              ))}
            </dl>
          </RouteSectionCard>
          <RouteSectionCard title="Smart Recommendations">
            <ul className="space-y-3 text-sm">
              <li className="rounded-xl border border-primary/10 bg-gray-bg/30 px-3 py-2.5">
                Vehicle class: <strong>{String(rec.vehicle_class ?? "—")}</strong>
              </li>
              {Array.isArray(rec.warnings) && rec.warnings.length > 0 ? (
                <li className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-amber-900">
                  Warnings: {(rec.warnings as string[]).join(", ")}
                </li>
              ) : (
                <li className="text-muted">No active warnings</li>
              )}
            </ul>
          </RouteSectionCard>
        </div>
      )}

      {tab === "stops" && (
        <RouteSectionCard
          title="Stop Sequence"
          description={`${plan.stops.length} stops in delivery order.`}
        >
          <RouteStopTimeline stops={plan.stops} />
        </RouteSectionCard>
      )}

      {tab === "orders" && (
        <RouteSectionCard title="Orders on Route">
          {plan.order_ids.length === 0 ? (
            <RouteEmptyState title="No orders attached" />
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {plan.order_ids.map((oid) => (
                <Link
                  key={oid}
                  href={`/orders/${oid}`}
                  className="rounded-xl border border-primary/10 bg-gray-bg/30 px-4 py-3 text-sm font-medium text-secondary hover:border-secondary/30 hover:bg-white"
                >
                  View order →
                </Link>
              ))}
            </div>
          )}
        </RouteSectionCard>
      )}

      {tab === "audit" && (
        <RouteSectionCard title="Audit Log">
          {(plan.audit_log ?? []).length === 0 ? (
            <RouteEmptyState title="No audit events yet" />
          ) : (
            <div className="space-y-2">
              {plan.audit_log!.map((row) => (
                <div
                  key={row.id}
                  className="rounded-xl border border-primary/10 bg-gray-bg/30 px-4 py-3 text-sm"
                >
                  <span className="font-medium text-primary">{row.action}</span>
                  <span className="text-muted"> · {row.created_at}</span>
                </div>
              ))}
            </div>
          )}
        </RouteSectionCard>
      )}

      {(tab === "driver" || tab === "vehicle" || tab === "analytics") && (
        <RouteSectionCard title={titleCase(tab)}>
          {tab === "driver" && plan.driver_id ? (
            <Link
              href={`/drivers/${plan.driver_id}`}
              className="text-sm font-medium text-secondary hover:underline"
            >
              View driver profile →
            </Link>
          ) : tab === "vehicle" && plan.vehicle_id ? (
            <p className="text-sm text-primary">Vehicle ID: {plan.vehicle_id}</p>
          ) : (
            <RouteEmptyState
              title={tab === "analytics" ? "Route-level analytics" : `No ${tab} assigned`}
              hint={
                tab === "analytics"
                  ? "Aggregate analytics are available in the Analytics tab."
                  : "Assign during dispatch to populate this section."
              }
            />
          )}
          {tab === "analytics" && (
            <Link
              href="/routes/analytics"
              className="mt-4 inline-block text-sm font-medium text-secondary hover:underline"
            >
              Open Route Center Analytics →
            </Link>
          )}
        </RouteSectionCard>
      )}
    </div>
  );
}
