import {
  AlertTriangle,
  Car,
  LogIn,
  LogOut,
  Power,
  PowerOff,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function QuickActions({
  isOnline,
  shiftActive,
  hasRoute,
  actionPending,
  onStartShift,
  onEndShift,
  onGoOnline,
  onGoOffline,
  onEmergency,
}: {
  isOnline: boolean;
  shiftActive: boolean;
  hasRoute: boolean;
  actionPending: string | null;
  onStartShift: () => void;
  onEndShift: () => void;
  onGoOnline: () => void;
  onGoOffline: () => void;
  onEmergency: () => void;
}) {
  const busy = (id: string) => actionPending === id;

  return (
    <div className="rounded-2xl border border-transparent bg-white p-5 shadow-sm">
      <h2 className="text-lg font-bold">Quick Actions</h2>
      <p className="mt-1 text-sm text-[var(--muted)]">Shift and availability controls</p>
      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <ActionButton
          label="Start Shift"
          icon={LogIn}
          onClick={onStartShift}
          disabled={shiftActive || busy("start")}
          loading={busy("start")}
          variant="primary"
        />
        <ActionButton
          label="End Shift"
          icon={LogOut}
          onClick={onEndShift}
          disabled={!isOnline && !shiftActive}
          loading={busy("end")}
        />
        <ActionButton
          label={isOnline ? "Go Offline" : "Go Online"}
          icon={isOnline ? PowerOff : Power}
          onClick={isOnline ? onGoOffline : onGoOnline}
          disabled={busy("online") || busy("offline")}
          loading={busy("online") || busy("offline")}
          variant={isOnline ? "muted" : "success"}
        />
        <ActionButton
          label="Emergency"
          icon={AlertTriangle}
          onClick={onEmergency}
          loading={busy("emergency")}
          variant="danger"
          className="sm:col-span-2 lg:col-span-1"
        />
      </div>
    </div>
  );
}

function ActionButton({
  label,
  icon: Icon,
  onClick,
  disabled,
  loading,
  variant = "default",
  className,
}: {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: "default" | "primary" | "success" | "muted" | "danger";
  className?: string;
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
        variant === "muted" && "bg-gray-600 text-white hover:bg-gray-700",
        variant === "danger" && "bg-red-600 text-white hover:bg-red-700",
        variant === "default" && "border border-[var(--primary)]/10 bg-[var(--gray-bg)] text-[var(--primary)] hover:bg-white",
        className
      )}
    >
      <Icon className="h-4 w-4" />
      {loading ? "Working…" : label}
    </button>
  );
}

export function VehicleCard({
  vehicle,
}: {
  vehicle: {
    make_model: string;
    plate_number: string;
    vehicle_class: string;
    capacity_kg: number | null;
  } | null;
}) {
  return (
    <div className="rounded-2xl border border-transparent bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <Car className="h-5 w-5 text-[var(--secondary)]" />
        <h2 className="text-lg font-bold">Vehicle</h2>
      </div>
      {vehicle ? (
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Unit</dt>
            <dd className="font-semibold">{vehicle.make_model}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Plate</dt>
            <dd className="font-mono font-semibold">{vehicle.plate_number}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Class</dt>
            <dd className="capitalize">{vehicle.vehicle_class}</dd>
          </div>
          {vehicle.capacity_kg != null && (
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--muted)]">Capacity</dt>
              <dd>{vehicle.capacity_kg} kg</dd>
            </div>
          )}
        </dl>
      ) : (
        <p className="mt-4 text-sm text-[var(--muted)]">No active vehicle on file</p>
      )}
    </div>
  );
}
