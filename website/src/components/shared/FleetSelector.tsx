"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
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
import Image from "next/image";
import BorderBeam from "@/components/magic/border-beam";
import FleetVehicleTab from "@/components/shared/FleetVehicleTab";
import { FLEET_VEHICLE_PHOTOS, fleetVehicleUsesPhoto } from "@/components/shared/FleetVehicleIcon";
import { BUSINESS_FLEET_KEYS } from "@/data/business";
import {
  FLEET_VEHICLE_SPECS,
  formatFleetDimension,
  formatFleetWeightLbs,
  type FleetVehicleKey,
} from "@/data/fleet-specs";
import { cn } from "@/lib/utils";
import { springSoft, easeOutQuart } from "@/lib/motion";
import { useFormFieldFocus } from "@/hooks/use-form-field-focus";

interface FleetSelectorProps {
  detailed?: boolean;
  showPreview?: boolean;
  className?: string;
}

function SpecStat({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-secondary/15 bg-white p-3 sm:p-3.5 shadow-sm min-w-0">
      <div className="flex items-center gap-1.5 text-secondary mb-1.5">
        <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
        <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-secondary/80 truncate">
          {label}
        </p>
      </div>
      <p className="text-base sm:text-lg font-bold text-primary tabular-nums tracking-tight truncate">
        {value}
      </p>
    </div>
  );
}

/** Compact vehicle card when preview stage is off (e.g. home teaser). */
function FleetThumbCard({
  fleetKey,
  isActive,
  onSelect,
  name,
  payload,
  reduceMotion,
}: {
  fleetKey: FleetVehicleKey;
  isActive: boolean;
  onSelect: () => void;
  name: string;
  payload: string;
  reduceMotion: boolean;
}) {
  return (
    <motion.button
      type="button"
      role="tab"
      aria-selected={isActive}
      onClick={onSelect}
      whileHover={reduceMotion ? undefined : { y: -4 }}
      transition={springSoft}
      className={cn(
        "group relative flex min-w-[9.5rem] sm:min-w-0 snap-start flex-col overflow-hidden rounded-2xl border bg-white text-left",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40 focus-visible:ring-offset-2",
        isActive
          ? "border-secondary/40 shadow-lg shadow-secondary/15 ring-1 ring-secondary/20"
          : "border-primary/8 shadow-sm hover:border-secondary/25"
      )}
    >
      <div
        className={cn(
          "relative flex aspect-[4/3] items-center justify-center overflow-hidden",
          fleetVehicleUsesPhoto(fleetKey)
            ? "bg-[#eef2f7]"
            : "bg-gradient-to-br from-[#eef4ff] via-white to-secondary/[0.08] p-4"
        )}
      >
        <Image
          src={FLEET_VEHICLE_PHOTOS[fleetKey]}
          alt=""
          width={fleetVehicleUsesPhoto(fleetKey) ? 320 : 120}
          height={fleetVehicleUsesPhoto(fleetKey) ? 180 : 120}
          className={
            fleetVehicleUsesPhoto(fleetKey)
              ? "h-full w-full object-cover object-center"
              : "h-[72%] w-auto max-w-[85%] object-contain drop-shadow-md"
          }
        />
        {isActive ? (
          <span
            className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-secondary via-accent to-secondary"
            aria-hidden
          />
        ) : null}
      </div>
      <div className="px-3 py-2.5 border-t border-primary/6">
        <p className="text-sm font-bold text-primary truncate">{name}</p>
        <p className="text-xs font-semibold text-secondary tabular-nums truncate">{payload}</p>
      </div>
    </motion.button>
  );
}

export default function FleetSelector({
  detailed = true,
  showPreview = true,
  className,
}: FleetSelectorProps) {
  const t = useTranslations("businessPage.fleet");
  const formFieldFocused = useFormFieldFocus();
  const reduceMotion = useReducedMotion();
  const total = BUSINESS_FLEET_KEYS.length;
  const [active, setActive] = useState(0);
  const activeKey = BUSINESS_FLEET_KEYS[active] as FleetVehicleKey;
  const activeSpec = FLEET_VEHICLE_SPECS[activeKey];
  const reduce = Boolean(formFieldFocused || reduceMotion);

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

  const motionFast = reduce ? { duration: 0 } : undefined;

  const tablist = (
    <div
      className="fleet-fit__picker flex gap-2 overflow-x-auto pb-1 snap-x snap-mandatory scrollbar-hide"
      role="tablist"
      aria-label={t("title")}
    >
      {BUSINESS_FLEET_KEYS.map((key, i) => (
        <FleetVehicleTab
          key={key}
          fleetKey={key as FleetVehicleKey}
          isActive={i === active}
          onSelect={() => setActive(i)}
          name={t(`items.${key}.name`)}
          payload={t(`items.${key}.payload`)}
          reduceMotion={reduce}
        />
      ))}
    </div>
  );

  const footer = detailed ? (
    <div className="fleet-fit__footer flex flex-wrap items-start gap-x-3 gap-y-1 text-[10px] sm:text-[11px] text-muted/75">
      <p className="inline-flex items-start gap-1.5 min-w-0 flex-1">
        <Info className="h-3.5 w-3.5 text-secondary shrink-0 mt-px" aria-hidden />
        <span className="line-clamp-2 sm:line-clamp-1">{t("licenceNote")}</span>
      </p>
    </div>
  ) : null;

  /* Compact: photo thumbnails — used on home teaser */
  if (!showPreview) {
    return (
      <div
        className={cn(
          "fleet-fit flex flex-col gap-3",
          formFieldFocused && "motion-paused",
          className
        )}
      >
        <div
          className="flex gap-3 overflow-x-auto pb-1 snap-x snap-mandatory scrollbar-hide sm:grid sm:grid-cols-4 md:grid-cols-7 sm:overflow-visible"
          role="tablist"
          aria-label={t("title")}
        >
          {BUSINESS_FLEET_KEYS.map((key, i) => (
            <FleetThumbCard
              key={key}
              fleetKey={key as FleetVehicleKey}
              isActive={i === active}
              onSelect={() => setActive(i)}
              name={t(`items.${key}.name`)}
              payload={t(`items.${key}.payload`)}
              reduceMotion={reduce}
            />
          ))}
        </div>
        {footer}
      </div>
    );
  }

  /* Full showcase: tabs + split photo / details */
  return (
    <div
      className={cn(
        "fleet-fit flex flex-col gap-4 sm:gap-5 min-h-0",
        formFieldFocused && "motion-paused",
        className
      )}
    >
      {tablist}

      <div className="fleet-fit__showcase relative overflow-hidden rounded-3xl border border-secondary/20 bg-white shadow-premium ring-1 ring-secondary/10">
        {!reduce ? (
          <BorderBeam size={260} duration={16} colorFrom="#2563eb" colorTo="#93c5fd" />
        ) : null}

        <div className="grid lg:grid-cols-[minmax(0,1.35fr)_minmax(18rem,0.9fr)] min-h-0">
          {/* Vehicle stage — local Flaticon vectors (reliable, always visible) */}
          <div className="fleet-fit__stage relative isolate flex flex-col overflow-hidden bg-gradient-to-br from-[#eef4ff] via-white to-[#f8fafc]">
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                backgroundImage:
                  "radial-gradient(ellipse 70% 55% at 50% 100%, rgba(37,99,235,0.16), transparent 70%), radial-gradient(circle at 20% 20%, rgba(59,130,246,0.1), transparent 40%)",
              }}
              aria-hidden
            />

            <div
              className="pointer-events-none absolute inset-x-[12%] bottom-[14%] h-[22%] rounded-[100%] bg-secondary/20 blur-3xl"
              aria-hidden
            />

            <div className="absolute top-3 left-3 z-10">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-secondary/20 bg-white/90 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] text-primary shadow-sm backdrop-blur-md">
                <span className="text-secondary">{String(active + 1).padStart(2, "0")}</span>
                <span className="text-muted/40">/</span>
                <span className="text-muted">{String(total).padStart(2, "0")}</span>
              </span>
            </div>

            <div className="relative z-[1] flex flex-1 items-center justify-center px-4 pb-14 pt-10 sm:px-8 sm:pt-12">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeKey}
                  initial={{ opacity: 0, x: 36, scale: 0.96 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  exit={{ opacity: 0, x: -28, scale: 0.96 }}
                  transition={motionFast ?? { duration: 0.4, ease: easeOutQuart }}
                  className={cn(
                    "relative flex items-center justify-center",
                    fleetVehicleUsesPhoto(activeKey) &&
                      "w-full overflow-hidden rounded-2xl border border-primary/8 bg-white shadow-sm"
                  )}
                >
                  <Image
                    src={FLEET_VEHICLE_PHOTOS[activeKey]}
                    alt={t(`items.${activeKey}.name`)}
                    width={fleetVehicleUsesPhoto(activeKey) ? 1024 : 420}
                    height={fleetVehicleUsesPhoto(activeKey) ? 585 : 420}
                    priority
                    className={
                      fleetVehicleUsesPhoto(activeKey)
                        ? "h-auto w-full max-h-[min(52vw,18rem)] sm:max-h-[min(36vw,20rem)] lg:max-h-[18rem] object-cover object-center"
                        : "h-auto w-[min(78vw,18rem)] sm:w-[min(42vw,22rem)] lg:w-[min(28vw,20rem)] object-contain drop-shadow-[0_18px_40px_rgba(15,23,42,0.18)]"
                    }
                  />
                </motion.div>
              </AnimatePresence>
            </div>

            <div className="absolute bottom-3 left-3 right-3 z-10 flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={goPrev}
                className="flex h-10 w-10 items-center justify-center rounded-full border border-secondary/20 bg-white/95 text-primary shadow-md backdrop-blur-md transition-colors hover:bg-secondary hover:text-white"
                aria-label="Previous vehicle"
              >
                <ChevronLeft className="h-4 w-4" aria-hidden />
              </button>
              <div className="flex items-center gap-1.5">
                {BUSINESS_FLEET_KEYS.map((key, i) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setActive(i)}
                    aria-label={t(`items.${key}.name`)}
                    className={cn(
                      "h-1.5 rounded-full transition-all",
                      i === active
                        ? "w-6 bg-secondary"
                        : "w-1.5 bg-primary/20 hover:bg-secondary/50"
                    )}
                  />
                ))}
              </div>
              <button
                type="button"
                onClick={goNext}
                className="flex h-10 w-10 items-center justify-center rounded-full border border-secondary/20 bg-white/95 text-primary shadow-md backdrop-blur-md transition-colors hover:bg-secondary hover:text-white"
                aria-label="Next vehicle"
              >
                <ChevronRight className="h-4 w-4" aria-hidden />
              </button>
            </div>
          </div>

          {/* Details panel */}
          <div className="relative flex flex-col justify-center gap-5 border-t lg:border-t-0 lg:border-l border-secondary/10 bg-gradient-to-b from-white to-gray-bg/60 p-5 sm:p-6 lg:p-7">
            <AnimatePresence mode="wait">
              <motion.div
                key={`detail-${activeKey}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={motionFast ?? { duration: 0.28, ease: easeOutQuart }}
                className="space-y-5"
              >
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-secondary mb-2">
                    {t("specTitle")}
                  </p>
                  <h3 className="text-2xl sm:text-3xl font-semibold text-primary tracking-tight leading-tight">
                    {t(`items.${activeKey}.name`)}
                  </h3>
                  <p className="mt-2 text-sm text-muted leading-relaxed">
                    {t(`items.${activeKey}.useCase`)}
                  </p>
                  {detailed ? (
                    <p className="mt-3 inline-flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-semibold text-secondary">
                      <span>{t(`items.${activeKey}.payload`)}</span>
                      <span className="text-secondary/30">·</span>
                      <span>{t(`items.${activeKey}.cargo`)}</span>
                    </p>
                  ) : null}
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <SpecStat
                    icon={ArrowUpDown}
                    label={t("specHeight")}
                    value={formatFleetDimension(activeSpec.heightIn)}
                  />
                  <SpecStat
                    icon={ArrowLeftRight}
                    label={t("specWidth")}
                    value={formatFleetDimension(activeSpec.widthIn)}
                  />
                  <SpecStat
                    icon={Weight}
                    label={t("specWeight")}
                    value={formatFleetWeightLbs(activeSpec.weightLbs)}
                  />
                  <SpecStat icon={Layers} label={t("specSkids")} value={skidValue} />
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>

      {footer}
    </div>
  );
}
