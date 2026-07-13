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
import FleetVehicleCard from "@/components/shared/FleetVehicleCard";
import { BUSINESS_FLEET_KEYS, FLEET_ILLUSTRATIONS } from "@/data/business";
import {
  FLEET_VEHICLE_SPECS,
  formatFleetDimension,
  formatFleetWeightLbs,
  type FleetVehicleKey,
} from "@/data/fleet-specs";
import { cn } from "@/lib/utils";
import { useFormFieldFocus } from "@/hooks/use-form-field-focus";

interface FleetSelectorProps {
  /** Show payload/cargo spec tiles, capacity ladder, and licence note */
  detailed?: boolean;
  /** Large photo preview stage above the vehicle cards */
  showPreview?: boolean;
  className?: string;
}

function FleetSpecTile({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
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

export default function FleetSelector({
  detailed = true,
  showPreview = true,
  className,
}: FleetSelectorProps) {
  const t = useTranslations("businessPage.fleet");
  const formFieldFocused = useFormFieldFocus();
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
      if (formFieldFocused) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest('input, textarea, select, [contenteditable="true"]')) return;

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
  }, [formFieldFocused, goNext, goPrev]);

  const skidValue =
    activeSpec.skidCapacity > 0
      ? t("specSkidsCount", { count: activeSpec.skidCapacity })
      : t("specSkidsNone");

  const specLabels = {
    height: t("specHeight"),
    width: t("specWidth"),
    weight: t("specWeight"),
    skids: t("specSkids"),
  };

  const motionFast = formFieldFocused ? { duration: 0 } : undefined;

  return (
    <div
      className={cn(
        "fleet-fit flex flex-col gap-3 sm:gap-4 min-h-0",
        formFieldFocused && "motion-paused",
        className
      )}
    >
      {/* Preview stage */}
      {showPreview && (
        <div className="fleet-fit__stage relative min-h-0 rounded-2xl sm:rounded-3xl overflow-hidden border border-primary/8 bg-primary shadow-premium ring-1 ring-primary/[0.04]">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeKey}
              initial={{ opacity: 0, scale: 1.03 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={motionFast ?? { duration: 0.35, ease: [0.22, 1, 0.36, 1] as const }}
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
            className="absolute inset-0 bg-gradient-to-r from-primary/30 via-transparent to-transparent"
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

          <div className="absolute top-11 sm:top-12 right-2.5 sm:right-3 left-2.5 sm:left-auto sm:max-w-[16rem] z-10">
            <AnimatePresence mode="wait">
              <motion.div
                key={`specs-${activeKey}`}
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={motionFast ?? { duration: 0.22 }}
                className="rounded-xl border border-secondary/25 bg-secondary/[0.12] p-2 sm:p-2.5 backdrop-blur-md shadow-lg shadow-primary/10"
              >
                <p className="mb-1.5 text-[9px] font-bold uppercase tracking-[0.16em] text-secondary">
                  {t("specTitle")}
                </p>
                <div className="grid grid-cols-4 gap-1 sm:gap-1.5">
                  <FleetSpecTile
                    icon={ArrowUpDown}
                    label={t("specHeight")}
                    value={formatFleetDimension(activeSpec.heightIn)}
                  />
                  <FleetSpecTile
                    icon={ArrowLeftRight}
                    label={t("specWidth")}
                    value={formatFleetDimension(activeSpec.widthIn)}
                  />
                  <FleetSpecTile
                    icon={Weight}
                    label={t("specWeight")}
                    value={formatFleetWeightLbs(activeSpec.weightLbs)}
                  />
                  <FleetSpecTile icon={Layers} label={t("specSkids")} value={skidValue} />
                </div>
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="absolute bottom-0 left-0 right-0 z-10 p-3 sm:p-4 lg:p-5">
            <motion.div
              key={`meta-${activeKey}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={motionFast ?? { duration: 0.28, delay: formFieldFocused ? 0 : 0.04 }}
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
      )}

      {/* Vehicle selection cards */}
      <div
        className="fleet-fit__picker flex gap-3 sm:gap-3.5 overflow-x-auto pb-2 snap-x snap-mandatory scrollbar-hide sm:grid sm:grid-cols-4 md:grid-cols-7 sm:overflow-visible sm:pb-0"
        role="tablist"
        aria-label={t("title")}
      >
        {BUSINESS_FLEET_KEYS.map((key, i) => {
          const fleetKey = key as FleetVehicleKey;
          const spec = FLEET_VEHICLE_SPECS[fleetKey];
          const skidDisplay =
            spec.skidCapacity > 0
              ? t("specSkidsCount", { count: spec.skidCapacity })
              : t("specSkidsNone");
          return (
            <FleetVehicleCard
              key={key}
              fleetKey={fleetKey}
              isActive={i === active}
              onSelect={() => setActive(i)}
              name={t(`items.${key}.name`)}
              payload={t(`items.${key}.payload`)}
              cargo={t(`items.${key}.cargo`)}
              useCase={t(`items.${key}.useCase`)}
              specLabels={specLabels}
              skidDisplay={skidDisplay}
              reduceMotion={formFieldFocused}
            />
          );
        })}
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
