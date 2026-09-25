"use client";

import { motion, useReducedMotion } from "framer-motion";
import FleetVehicleIcon from "@/components/marketing/shared/FleetVehicleIcon";
import type { FleetVehicleKey } from "@/data/fleet-specs";
import { cn } from "@/lib/utils";
import { springSnappy } from "@/lib/motion";

interface FleetVehicleTabProps {
  fleetKey: FleetVehicleKey;
  isActive: boolean;
  onSelect: () => void;
  name: string;
  payload: string;
  reduceMotion?: boolean;
}

/** Compact selector chip for the fleet showcase rail. */
export default function FleetVehicleTab({
  fleetKey,
  isActive,
  onSelect,
  name,
  payload,
  reduceMotion = false,
}: FleetVehicleTabProps) {
  const reduce = useReducedMotion() || reduceMotion;

  return (
    <motion.button
      type="button"
      role="tab"
      aria-selected={isActive}
      onClick={onSelect}
      whileHover={reduce ? undefined : { y: -2 }}
      whileTap={reduce ? undefined : { scale: 0.98 }}
      transition={springSnappy}
      className={cn(
        "group relative flex shrink-0 items-center gap-2.5 rounded-2xl border px-3 py-2.5 text-left transition-colors duration-200",
        "snap-start focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40 focus-visible:ring-offset-2",
        isActive
          ? "border-secondary/40 bg-secondary text-white shadow-lg shadow-secondary/25"
          : "border-primary/8 bg-white text-primary hover:border-secondary/30 hover:bg-secondary/[0.04]"
      )}
    >
      <span
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-xl border shrink-0",
          isActive ? "border-white/20 bg-white/15" : "border-primary/8 bg-gray-bg"
        )}
      >
        <FleetVehicleIcon vehicle={fleetKey} active={isActive} size={26} />
      </span>
      <span className="min-w-0 pr-1">
        <span
          className={cn(
            "block text-sm font-bold leading-tight tracking-tight truncate",
            isActive ? "text-white" : "text-primary"
          )}
        >
          {name}
        </span>
        <span
          className={cn(
            "mt-0.5 block text-[11px] font-semibold tabular-nums truncate",
            isActive ? "text-white/80" : "text-secondary"
          )}
        >
          {payload}
        </span>
      </span>
    </motion.button>
  );
}
