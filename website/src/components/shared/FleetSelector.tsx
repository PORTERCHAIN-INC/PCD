"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useTranslations } from "next-intl";
import {
  ArrowLeftRight,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Info,
  Layers,
  Weight,
  type LucideIcon,
} from "lucide-react";
import VehicleIllustration from "@/components/illustrations/VehicleIllustration";
import FleetVehicleIcon from "@/components/shared/FleetVehicleIcon";
import { BUSINESS_FLEET_KEYS, FLEET_ILLUSTRATIONS } from "@/data/business";
import {
  FLEET_VEHICLE_SPECS,
  formatFleetDimension,
  formatFleetWeightLbs,
  type FleetVehicleKey,
} from "@/data/fleet-specs";
import { cn } from "@/lib/utils";

interface FleetSelectorProps {
  /** Show licence note (capacity ladder removed — rail covers vehicle scale) */
  detailed?: boolean;
  className?: string;
}

function FleetSpecTile({
  icon: Icon,
  label,
  value,
  compact,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  compact?: boolean;
}) {
  if (compact) {
    return (
      <div className="rounded-lg border border-secondary/15 bg-white/75 px-2 py-1.5 text-center min-w-0">
        <div className="flex items-center justify-center gap-1 text-secondary">
          <Icon className="h-3 w-3 shrink-0" aria-hidden />
          <p className="text-[8px] font-semibold uppercase tracking-[0.12em] text-secondary/75 truncate">
            {label}
          </p>
        </div>
        <p className="mt-0.5 text-[11px] sm:text-xs font-semibold text-primary tabular-nums truncate">
          {value}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-secondary/15 bg-white/70 px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary/12 text-secondary">
          <Icon className="h-4 w-4" aria-hidden />
        </span>
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-secondary/75">
            {label}
          </p>
          <p className="text-sm font-semibold text-primary tabular-nums">{value}</p>
        </div>
      </div>
    </div>
  );
}

export default function FleetSelector({ detailed = true, className }: FleetSelectorProps) {
  const t = useTranslations("businessPage.fleet");
  const total = BUSINESS_FLEET_KEYS.length;
  const [active, setActive] = useState(0);
  const activeKey = BUSINESS_FLEET_KEYS[active] as FleetVehicleKey;
  const activeSpec = FLEET_VEHICLE_SPECS[activeKey];

  const goTo = useCallback(
    (index: number) => {
      setActive((index + total) % total);
    },
    [total]
  );

  const goPrev = useCallback(() => goTo(active - 1), [active, goTo]);
  const goNext = useCallback(() => goTo(active + 1), [active, goTo]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        event.preventDefault();
        goPrev();
      }
      if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        event.preventDefault();
        goNext();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [goNext, goPrev]);

  const skidValue =
    activeSpec.skidCapacity > 0
      ? t("specSkidsCount", { count: activeSpec.skidCapacity })
      : t("specSkidsNone");

  return (
    <div
      className={cn(
        "fleet-fit flex flex-col gap-2 sm:gap-2.5 min-h-0",
        detailed ? "fleet-fit--detailed" : "fleet-fit--compact",
        className
      )}
    >
      <div className="fleet-fit__grid grid min-h-0 gap-2 sm:gap-3 lg:grid-cols-[minmax(0,1fr)_9.75rem] xl:grid-cols-[minmax(0,1fr)_10.75rem] lg:items-stretch">
        {/* Photo stage */}
        <div className="fleet-fit__stage relative min-h-0 rounded-2xl sm:rounded-3xl overflow-hidden border border-primary/8 bg-primary shadow-premium ring-1 ring-primary/[0.04]">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeKey}
              initial={{ opacity: 0, scale: 1.03 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-0"
            >
              <VehicleIllustration
                type={FLEET_ILLUSTRATIONS[activeKey]}
                id={`fleet-${activeKey}`}
                mode="photo"
                className="absolute inset-0"
              />
            </motion.div>
          </AnimatePresence>

          <div
            className="absolute inset-0 bg-gradient-to-t from-primary via-primary/45 to-primary/15"
            aria-hidden
          />
          <div
            className="absolute inset-0 bg-gradient-to-r from-primary/40 via-transparent to-transparent lg:from-primary/25"
            aria-hidden
          />

          <div className="absolute top-2.5 left-2.5 right-2.5 sm:top-3 sm:left-3 sm:right-3 flex items-center justify-between gap-2 z-10">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-black/25 px-2.5 py-1 text-[9px] sm:text-[10px] font-bold uppercase tracking-[0.16em] text-white backdrop-blur-md">
              <span className="text-accent">{String(active + 1).padStart(2, "0")}</span>
              <span className="text-white/50">/</span>
              <span>{String(total).padStart(2, "0")}</span>
            </span>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={goPrev}
                className="flex h-8 w-8 items-center justify-center rounded-full border border-white/15 bg-black/25 text-white backdrop-blur-md transition-colors hover:bg-white/15"
                aria-label="Previous vehicle"
              >
                <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
              </button>
              <button
                type="button"
                onClick={goNext}
                className="flex h-8 w-8 items-center justify-center rounded-full border border-white/15 bg-black/25 text-white backdrop-blur-md transition-colors hover:bg-white/15"
                aria-label="Next vehicle"
              >
                <ChevronRight className="h-3.5 w-3.5" aria-hidden />
              </button>
            </div>
          </div>

          {/* Cargo specs */}
          <div className="absolute top-11 sm:top-12 left-2.5 right-2.5 sm:left-3 sm:right-3 lg:left-auto lg:right-3 lg:max-w-[15.5rem] z-10">
            <AnimatePresence mode="wait">
              <motion.div
                key={`specs-${activeKey}`}
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.22 }}
                className="rounded-xl border border-secondary/25 bg-secondary/[0.12] p-2 sm:p-2.5 backdrop-blur-md shadow-lg shadow-primary/10"
              >
                <p className="mb-1.5 text-[9px] font-bold uppercase tracking-[0.16em] text-secondary">
                  {t("specTitle")}
                </p>
                <div className="grid grid-cols-4 gap-1 sm:gap-1.5">
                  <FleetSpecTile
                    compact
                    icon={ArrowUpDown}
                    label={t("specHeight")}
                    value={formatFleetDimension(activeSpec.heightIn)}
                  />
                  <FleetSpecTile
                    compact
                    icon={ArrowLeftRight}
                    label={t("specWidth")}
                    value={formatFleetDimension(activeSpec.widthIn)}
                  />
                  <FleetSpecTile
                    compact
                    icon={Weight}
                    label={t("specWeight")}
                    value={formatFleetWeightLbs(activeSpec.weightLbs)}
                  />
                  <FleetSpecTile compact icon={Layers} label={t("specSkids")} value={skidValue} />
                </div>
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="absolute bottom-0 left-0 right-0 z-10 p-3 sm:p-4 lg:p-5">
            <motion.div
              key={`meta-${activeKey}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28, delay: 0.04 }}
            >
              <h3 className="text-lg sm:text-xl lg:text-2xl font-semibold text-white tracking-tight leading-tight">
                {t(`items.${activeKey}.name`)}
              </h3>
              <p className="mt-1 text-xs sm:text-sm text-white/70 leading-snug line-clamp-2 max-w-xl">
                {t(`items.${activeKey}.useCase`)}
              </p>
              {detailed && (
                <p className="mt-1.5 text-[11px] sm:text-xs text-white/55">
                  {t(`items.${activeKey}.payload`)} · {t(`items.${activeKey}.cargo`)}
                </p>
              )}
            </motion.div>
          </div>
        </div>

        {/* Vehicle rail */}
        <div
          className="fleet-fit__rail flex gap-1.5 overflow-x-auto pb-0.5 snap-x snap-mandatory scrollbar-hide lg:flex-col lg:overflow-y-auto lg:overflow-x-hidden lg:pb-0 lg:min-h-0"
          role="tablist"
          aria-label={t("title")}
        >
          {BUSINESS_FLEET_KEYS.map((key, i) => {
            const isActive = i === active;
            const fleetKey = key as FleetVehicleKey;
            return (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => setActive(i)}
                className={cn(
                  "group relative flex shrink-0 snap-start items-center gap-2 rounded-xl border p-2 text-left transition-all duration-200",
                  "min-w-[7.25rem] sm:min-w-[8rem] lg:min-w-0 lg:w-full",
                  isActive
                    ? "border-secondary/30 bg-white shadow-premium ring-1 ring-secondary/10"
                    : "border-primary/8 bg-white/90 hover:border-secondary/20 hover:bg-white"
                )}
              >
                {isActive && (
                  <motion.span
                    layoutId="fleet-active-rail"
                    className="absolute left-0 top-2 bottom-2 w-0.5 rounded-full bg-gradient-to-b from-secondary to-accent"
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                )}
                <span
                  className={cn(
                    "relative ml-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border transition-colors",
                    isActive
                      ? "border-secondary/25 bg-secondary/[0.08]"
                      : "border-primary/8 bg-primary/[0.03] group-hover:border-secondary/15"
                  )}
                >
                  <FleetVehicleIcon vehicle={fleetKey} size={28} />
                </span>
                <span className="min-w-0 flex-1 pr-0.5">
                  <span className="block truncate text-xs font-semibold text-primary">
                    {t(`items.${key}.name`)}
                  </span>
                  <span className="mt-0.5 block truncate text-[10px] text-muted">
                    {t(`items.${key}.payload`)}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="fleet-fit__footer flex flex-wrap items-start gap-x-3 gap-y-1 text-[10px] sm:text-[11px] text-muted/75 shrink-0">
        {detailed && (
          <p className="inline-flex items-start gap-1.5 min-w-0 flex-1">
            <Info className="h-3.5 w-3.5 text-secondary shrink-0 mt-px" aria-hidden />
            <span className="line-clamp-2 sm:line-clamp-1">{t("licenceNote")}</span>
          </p>
        )}
        <p className={cn(detailed ? "shrink-0" : "w-full")}>
          {t("iconAttributionPrefix")}
          <a
            href="https://www.flaticon.com/authors/rooman12"
            target="_blank"
            rel="noopener noreferrer"
            className="underline decoration-muted/40 underline-offset-2 hover:text-secondary"
          >
            {t("iconAttributionLink")}
          </a>
        </p>
      </div>
    </div>
  );
}
