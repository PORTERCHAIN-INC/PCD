"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  Car,
  Clock,
  Coffee,
  Gauge,
  LogIn,
  LogOut,
  MapPinned,
  Pause,
  Play,
  RefreshCw,
  Route,
} from "lucide-react";
import DriverShell from "@/components/DriverShell";
import { PretripGate } from "@/components/dashboard/PretripGate";
import { useDriverShift } from "@/hooks/useDriverShift";
import { hasDriverSession } from "@/lib/api";
import { actionErrorMessage } from "@/lib/jobs";
import { emptyPretrip, pretripComplete, type PretripChecks } from "@/lib/pretrip";
import { availabilityColor, availabilityLabel, formatActivityTime } from "@/lib/shift";
import { mileageCaption } from "@/lib/telemetryLabels";
import { cn, formatCents } from "@/lib/utils";

export default function ShiftClient() {
  const router = useRouter();
  const {
    data,
    error,
    loading,
    refreshing,
    actionPending,
    refresh,
    startShift,
    endShift,
    startBreak,
    resumeShift,
    setAvailability,
  } = useDriverShift();
  const [pretrip, setPretrip] = useState<PretripChecks>(emptyPretrip());

  useEffect(() => {
    hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
    });
  }, [router]);

  if (error && !data) {
    return (
      <DriverShell>
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {actionErrorMessage(error)}
        </p>
        <button
          type="button"
          onClick={() => refresh()}
          className="mt-4 rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white"
        >
          Retry
        </button>
      </DriverShell>
    );
  }

  if (loading || !data) {
    return (
      <DriverShell>
        <div className="animate-pulse space-y-4">
          <div className="h-10 w-48 rounded-xl bg-white" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-32 rounded-2xl bg-white" />
            ))}
          </div>
        </div>
      </DriverShell>
    );
  }

  const snap = data;
  const onBreak = snap.shift?.status === "on_break";
  const busy = (id: string) => actionPending === id;

  return (
    <DriverShell>
      <header className="flex flex-col gap-3 border-b border-[var(--primary)]/8 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Shift</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Availability, working hours, and activity
          </p>
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-xl border border-[var(--primary)]/10 bg-white px-4 py-2 text-sm font-medium"
        >
          <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
          {refreshing ? "Syncing…" : "Sync now"}
        </button>
      </header>

      {error && (
        <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {actionErrorMessage(error)}
        </p>
      )}

      <section className="mt-6 rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={cn(
              "inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold text-white",
              availabilityColor(snap.availability)
            )}
          >
            <span className="h-2 w-2 rounded-full bg-white/80" />
            {availabilityLabel(snap.availability)}
          </span>
          {snap.shift_active ? (
            <span className="text-sm font-medium text-[var(--primary)]">
              Shift active · {onBreak ? "On break" : "Working"}
            </span>
          ) : (
            <span className="text-sm text-[var(--muted)]">No active shift</span>
          )}
          <span className="ml-auto text-xs text-[var(--muted)]">
            Updated {new Date(snap.last_updated).toLocaleTimeString()}
          </span>
        </div>

        {!snap.shift_active ? (
          <div className="mt-5">
            <PretripGate checks={pretrip} onChange={setPretrip} />
          </div>
        ) : null}

        <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <ShiftButton
            label="Start Shift"
            icon={LogIn}
            onClick={() => startShift(snap.current_route?.route_id, pretrip)}
            disabled={snap.shift_active || busy("start") || !pretripComplete(pretrip)}
            loading={busy("start")}
            variant="primary"
          />
          <ShiftButton
            label="End Shift"
            icon={LogOut}
            onClick={() => endShift()}
            disabled={!snap.shift_active || busy("end")}
            loading={busy("end")}
          />
          <ShiftButton
            label="Break"
            icon={Coffee}
            onClick={() => startBreak()}
            disabled={!snap.shift_active || onBreak || busy("break")}
            loading={busy("break")}
          />
          <ShiftButton
            label="Resume"
            icon={Play}
            onClick={() => resumeShift()}
            disabled={!onBreak || busy("resume")}
            loading={busy("resume")}
            variant="success"
          />
        </div>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-bold">Availability</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          {snap.shift_active
            ? "Set how dispatch sees your status"
            : "Start shift (30-second vehicle check) before going online"}
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {(["online", "offline", "busy", "idle"] as const).map((mode) => (
            <ShiftButton
              key={mode}
              label={mode === "online" ? "Online" : mode.charAt(0).toUpperCase() + mode.slice(1)}
              icon={mode === "offline" ? Pause : Activity}
              onClick={() => setAvailability(mode)}
              disabled={
                busy(mode) ||
                snap.availability === (mode === "online" ? "available" : mode) ||
                (mode !== "offline" && !snap.shift_active)
              }
              loading={busy(mode)}
              variant={
                snap.availability === (mode === "online" ? "available" : mode)
                  ? "primary"
                  : "default"
              }
            />
          ))}
        </div>
      </section>

      <section className="mt-6 grid gap-4 lg:grid-cols-3">
        <InfoCard title="Working Hours" icon={Clock}>
          <p className="text-3xl font-bold">{snap.working_hours_label}</p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {snap.shift?.started_at
              ? `Started ${new Date(snap.shift.started_at).toLocaleTimeString()}`
              : "Start a shift to track time"}
          </p>
          {snap.shift && snap.shift.break_minutes > 0 && (
            <p className="mt-2 text-sm text-[var(--muted)]">
              Break time: {snap.shift.break_minutes} min
            </p>
          )}
        </InfoCard>
        <InfoCard title="Mileage" icon={Gauge}>
          <p className="text-3xl font-bold">{snap.mileage_km.toFixed(1)} km</p>
          <p className="mt-1 text-sm text-[var(--muted)]">{mileageCaption(snap.mileage_source)}</p>
        </InfoCard>
        <InfoCard title="Capacity" icon={MapPinned}>
          {snap.capacity.max_kg != null ? (
            <>
              <p className="text-3xl font-bold">
                {snap.capacity.used_kg} / {snap.capacity.max_kg} kg
              </p>
              <p className="mt-1 text-sm text-[var(--muted)]">
                {snap.capacity.stops_count} stops ·{" "}
                {snap.capacity.utilization_percent != null
                  ? `${snap.capacity.utilization_percent}% utilized`
                  : "—"}
              </p>
            </>
          ) : (
            <p className="text-sm text-[var(--muted)]">No vehicle capacity on file</p>
          )}
        </InfoCard>
      </section>

      <section className="mt-6 grid gap-4 lg:grid-cols-2">
        <InfoCard title="Current Vehicle" icon={Car}>
          {snap.current_vehicle ? (
            <dl className="space-y-2 text-sm">
              <Row label="Unit" value={snap.current_vehicle.make_model} />
              <Row label="Plate" value={snap.current_vehicle.plate_number} />
              <Row label="Class" value={snap.current_vehicle.vehicle_class} />
            </dl>
          ) : (
            <p className="text-sm text-[var(--muted)]">No active vehicle</p>
          )}
        </InfoCard>
        <InfoCard title="Current Route" icon={Route}>
          {snap.current_route ? (
            <dl className="space-y-2 text-sm">
              <Row label="Route" value={snap.current_route.route_id} />
              <Row label="Status" value={snap.current_route.status} />
              <Row label="Stops" value={String(snap.current_route.stops_count)} />
              <Row label="Earnings" value={formatCents(snap.current_route.earnings_cents)} />
            </dl>
          ) : (
            <p className="text-sm text-[var(--muted)]">No assigned route</p>
          )}
        </InfoCard>
      </section>

      <section className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">Shift Timeline</h2>
          <ul className="mt-4 space-y-3">
            {snap.timeline.length === 0 ? (
              <li className="text-sm text-[var(--muted)]">No events yet this shift</li>
            ) : (
              snap.timeline.map((item) => (
                <li
                  key={item.id}
                  className="flex gap-3 border-l-2 border-[var(--secondary)]/30 pl-4"
                >
                  <div>
                    <p className="text-sm font-semibold">{item.label}</p>
                    <p className="text-xs text-[var(--muted)]">
                      {formatActivityTime(item.created_at)}
                    </p>
                  </div>
                </li>
              ))
            )}
          </ul>
        </div>
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">Activity Log</h2>
          <ul className="mt-4 max-h-80 space-y-2 overflow-y-auto">
            {snap.activity_log.length === 0 ? (
              <li className="text-sm text-[var(--muted)]">No activity recorded</li>
            ) : (
              [...snap.activity_log].reverse().map((item) => (
                <li
                  key={item.id}
                  className="flex items-center justify-between gap-4 rounded-xl bg-[var(--gray-bg)] px-3 py-2 text-sm"
                >
                  <span className="font-medium">{item.label}</span>
                  <span className="text-xs text-[var(--muted)]">
                    {formatActivityTime(item.created_at)}
                  </span>
                </li>
              ))
            )}
          </ul>
        </div>
      </section>
    </DriverShell>
  );
}

function InfoCard({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <Icon className="h-5 w-5 text-[var(--secondary)]" />
        <h2 className="text-lg font-bold">{title}</h2>
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-[var(--muted)]">{label}</dt>
      <dd className="font-semibold capitalize">{value}</dd>
    </div>
  );
}

function ShiftButton({
  label,
  icon: Icon,
  onClick,
  disabled,
  loading,
  variant = "default",
}: {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: "default" | "primary" | "success";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
      className={cn(
        "flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-[var(--primary)] text-white hover:bg-[var(--primary)]/90",
        variant === "success" && "bg-emerald-600 text-white hover:bg-emerald-700",
        variant === "default" &&
          "border border-[var(--primary)]/10 bg-[var(--gray-bg)] text-[var(--primary)] hover:bg-white"
      )}
    >
      <Icon className="h-4 w-4" />
      {loading ? "Working…" : label}
    </button>
  );
}
