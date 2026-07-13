"use client";

import { motion } from "framer-motion";
import { ArrowLeftRight, ArrowUpDown, Layers, Weight, type LucideIcon } from "lucide-react";
import FleetVehicleIcon from "@/components/shared/FleetVehicleIcon";
import {
  FLEET_VEHICLE_SPECS,
  formatFleetDimension,
  formatFleetWeightLbs,
  type FleetVehicleKey,
} from "@/data/fleet-specs";
import { cn } from "@/lib/utils";

interface FleetVehicleCardProps {
  fleetKey: FleetVehicleKey;
  isActive: boolean;
  onSelect: () => void;
  name: string;
  payload: string;
  cargo: string;
  useCase: string;
  specLabels: {
    height: string;
    width: string;
    weight: string;
    skids: string;
  };
  skidDisplay: string;
  reduceMotion?: boolean;
}

function MiniSpec({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2 min-w-0">
      <Icon className="h-3.5 w-3.5 shrink-0 text-white/75" aria-hidden />
      <span className="text-[11px] font-medium text-white/65 truncate">{label}</span>
      <span className="text-xs font-bold text-white tabular-nums ml-auto shrink-0">{value}</span>
    </div>
  );
}

export default function FleetVehicleCard({
  fleetKey,
  isActive,
  onSelect,
  name,
  payload,
  cargo,
  useCase,
  specLabels,
  skidDisplay,
  reduceMotion = false,
}: FleetVehicleCardProps) {
  const spec = FLEET_VEHICLE_SPECS[fleetKey];

  return (
    <motion.button
      type="button"
      role="tab"
      aria-selected={isActive}
      onClick={onSelect}
      whileHover={reduceMotion ? undefined : { y: -4, scale: 1.02 }}
      transition={{ type: "spring", stiffness: 400, damping: 26 }}
      className={cn(
        "group relative flex flex-col items-stretch rounded-2xl sm:rounded-3xl border text-left transition-all duration-200",
        "min-w-[8.5rem] sm:min-w-0 snap-start",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60 focus-visible:ring-offset-2 focus-visible:ring-offset-secondary/30",
        isActive
          ? "border-white/30 bg-gradient-to-br from-[#3b82f6] via-secondary to-[#1d4ed8] shadow-xl shadow-secondary/45 ring-2 ring-white/25 scale-[1.02]"
          : "border-secondary/35 bg-gradient-to-br from-secondary/30 via-secondary/40 to-secondary/55 hover:from-secondary/35 hover:via-secondary/45 hover:to-secondary/60 hover:border-white/20 hover:shadow-lg hover:shadow-secondary/30"
      )}
    >
      <div
        className={cn(
          "absolute inset-x-4 top-0 h-1 rounded-full transition-opacity",
          isActive
            ? "bg-gradient-to-r from-white via-accent to-white opacity-100"
            : "opacity-0 group-hover:opacity-80 bg-white/40"
        )}
        aria-hidden
      />

      <div className="flex flex-col items-center px-4 pt-4 sm:pt-5 pb-3">
        <FleetVehicleIcon vehicle={fleetKey} active={isActive} size={56} />
        <span className="mt-3 w-full text-center text-sm sm:text-base font-bold leading-tight tracking-tight text-white">
          {name}
        </span>
        <span
          className={cn(
            "mt-1 w-full text-center text-xs sm:text-sm font-semibold tabular-nums",
            isActive ? "text-white/90" : "text-white/80"
          )}
        >
          {payload}
        </span>
      </div>

      <div
        className={cn(
          "overflow-hidden border-t transition-all duration-300",
          isActive ? "border-white/25" : "border-white/15",
          isActive ? "max-h-52 opacity-100" : "max-h-0 opacity-0",
          !reduceMotion &&
            "[@media(hover:hover)]:group-hover:max-h-52 [@media(hover:hover)]:group-hover:opacity-100"
        )}
      >
        <div className="px-4 py-3 sm:py-3.5 space-y-2.5 bg-black/10">
          <p className="text-xs sm:text-sm font-medium text-white/90 leading-snug line-clamp-2">
            {useCase}
          </p>
          <p className="text-[11px] sm:text-xs font-semibold text-white/70">{cargo}</p>
          <div className="space-y-1.5 pt-1 border-t border-white/15">
            <MiniSpec
              icon={ArrowUpDown}
              label={specLabels.height}
              value={formatFleetDimension(spec.heightIn)}
            />
            <MiniSpec
              icon={ArrowLeftRight}
              label={specLabels.width}
              value={formatFleetDimension(spec.widthIn)}
            />
            <MiniSpec
              icon={Weight}
              label={specLabels.weight}
              value={formatFleetWeightLbs(spec.weightLbs)}
            />
            <MiniSpec icon={Layers} label={specLabels.skids} value={skidDisplay} />
          </div>
        </div>
      </div>
    </motion.button>
  );
}
