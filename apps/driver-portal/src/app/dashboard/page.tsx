"use client";

import {
  Bell,
  CheckCircle2,
  Clock,
  Gauge,
  MapPinned,
  Star,
  Target,
  ThumbsUp,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { StatCardsSkeleton } from "@porterchain/ui/loading";
import DriverShell from "@/components/DriverShell";
import { AssignmentPanel } from "@/components/dashboard/AssignmentPanel";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { QuickActions, VehicleCard } from "@/components/dashboard/QuickActions";
import { useDriverWorkspace } from "@/hooks/useDriverWorkspace";
import { formatLastUpdated } from "@/lib/workspace";
import { formatCents } from "@/lib/utils";

export default function DashboardPage() {
  const {
    data,
    error,
    loading,
    refreshing,
    actionPending,
    setOnline,
    startShift,
    endShift,
    triggerEmergency,
    refresh,
  } = useDriverWorkspace();

  if (error && !data) {
    return (
      <DriverShell>
        <p className="text-red-600">{error}</p>
      </DriverShell>
    );
  }

  if (loading || !data) {
    return (
      <DriverShell>
        <StatCardsSkeleton count={8} />
      </DriverShell>
    );
  }

  const { dashboard, performance, ratings, queues, route, vehicle } = data;
  const shiftActive = data.shiftActive;
  const deliveriesToday =
    performance.deliveries_today > 0 ? performance.deliveries_today : queues.todaysDeliveries;

  return (
    <DriverShell>
      <header className="flex flex-col gap-4 border-b border-[var(--primary)]/8 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[var(--muted)]">Driver Workspace</p>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            {data.profile?.full_name
              ? `Hello, ${data.profile.full_name.split(" ")[0]}`
              : "Dashboard"}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                dashboard.is_online
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-gray-200 text-gray-700"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${dashboard.is_online ? "bg-emerald-500 animate-pulse" : "bg-gray-400"}`}
              />
              {data.shiftStatus}
            </span>
            <span className="text-xs text-[var(--muted)]">
              Updated {formatLastUpdated(data.lastUpdated)}
              {refreshing && " · syncing…"}
            </span>
            <button
              type="button"
              onClick={() => refresh()}
              className="text-xs font-semibold text-[var(--secondary)] hover:underline"
            >
              Refresh
            </button>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-2xl bg-white px-4 py-3 shadow-sm">
          <Wallet className="h-5 w-5 text-[var(--secondary)]" />
          <div>
            <p className="text-xs text-[var(--muted)]">Wallet balance</p>
            <p className="text-lg font-bold">{formatCents(dashboard.wallet_balance_cents)}</p>
          </div>
        </div>
      </header>

      <section className="mt-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
          Today&apos;s Operations
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Today's Earnings"
            value={formatCents(dashboard.todays_earnings_cents)}
            icon={Wallet}
            accent
          />
          <MetricCard
            label="Today's Deliveries"
            value={String(deliveriesToday)}
            hint={`${queues.completedDeliveries} completed`}
            icon={Target}
          />
          <MetricCard
            label="Completed Deliveries"
            value={String(queues.completedDeliveries)}
            icon={CheckCircle2}
          />
          <MetricCard
            label="Shift Status"
            value={data.shiftStatus}
            hint={shiftActive ? `Working ${data.workingHours}` : dashboard.availability}
            icon={Clock}
          />
        </div>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <AssignmentPanel
            route={route}
            nextStop={queues.nextStop}
            apiNextStop={data.nextStop}
            pickupQueue={queues.pickupQueue}
            deliveryQueue={queues.deliveryQueue}
          />
        </div>
        <div className="space-y-6">
          <VehicleCard vehicle={vehicle} />
          <div className="rounded-2xl border border-transparent bg-white p-5 shadow-sm">
            <h2 className="text-lg font-bold">Shift & Route</h2>
            <dl className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <dt className="text-[var(--muted)]">Working Hours</dt>
                <dd className="font-semibold">{shiftActive ? data.workingHours : "—"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--muted)]">Distance Driven</dt>
                <dd className="font-semibold">{shiftActive ? data.mileageKm : data.distanceKm}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--muted)]">Fuel Estimate</dt>
                <dd className="font-semibold">{data.fuelEstimate}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--muted)]">Route Earnings</dt>
                <dd className="font-semibold">{route ? formatCents(route.earnings_cents) : "—"}</dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      <section className="mt-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
          Performance
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Performance Score"
            value={`${performance.score}%`}
            icon={TrendingUp}
            accent
          />
          <MetricCard
            label="Acceptance Rate"
            value={`${performance.acceptance_rate}%`}
            icon={ThumbsUp}
          />
          <MetricCard
            label="Completion Rate"
            value={`${performance.completion_percent}%`}
            icon={Gauge}
          />
          <MetricCard
            label="Customer Rating"
            value={ratings.rating.toFixed(1)}
            hint={`${ratings.total_reviews} reviews`}
            icon={Star}
          />
        </div>
      </section>

      <section className="mt-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
          Alerts
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <MetricCard
            label="Unread Notifications"
            value={String(data.unreadNotifications)}
            hint="Documents, bonuses, open tickets"
            icon={Bell}
          />
          <MetricCard
            label="Open Claims"
            value={String(data.openClaims)}
            hint="Damage, loss, and claim incidents"
            icon={MapPinned}
          />
        </div>
      </section>

      <section className="mt-6">
        <QuickActions
          isOnline={dashboard.is_online}
          shiftActive={shiftActive}
          hasRoute={Boolean(route?.route_id || dashboard.active_route_id)}
          actionPending={actionPending}
          onStartShift={startShift}
          onEndShift={endShift}
          onGoOnline={() => setOnline(true)}
          onGoOffline={() => setOnline(false)}
          onEmergency={triggerEmergency}
        />
      </section>
    </DriverShell>
  );
}
