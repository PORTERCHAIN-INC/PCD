"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, Info, Package, Weight } from "lucide-react";
import VehicleIllustration from "@/components/illustrations/VehicleIllustration";
import { BUSINESS_FLEET_KEYS, FLEET_ILLUSTRATIONS } from "@/data/business";
import { cn } from "@/lib/utils";

interface FleetSelectorProps {
  /** Show payload/cargo spec tiles, capacity ladder, and licence note */
  detailed?: boolean;
  className?: string;
}

export default function FleetSelector({ detailed = true, className }: FleetSelectorProps) {
  const t = useTranslations("businessPage.fleet");
  const total = BUSINESS_FLEET_KEYS.length;
  const [active, setActive] = useState(0);
  const activeKey = BUSINESS_FLEET_KEYS[active];

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

  return (
    <div className={cn("space-y-6", className)}>
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_17.5rem] xl:grid-cols-[minmax(0,1fr)_19rem] lg:gap-6 xl:gap-8 lg:items-stretch">
        {/* Cinematic stage */}
        <div className="relative min-h-[min(72vw,320px)] sm:min-h-[360px] lg:min-h-[min(520px,68vh)] rounded-3xl overflow-hidden border border-primary/8 bg-primary shadow-premium ring-1 ring-primary/[0.04]">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeKey}
              initial={{ opacity: 0, scale: 1.04 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
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
            className="absolute inset-0 bg-gradient-to-t from-primary via-primary/40 to-primary/10"
            aria-hidden
          />
          <div
            className="absolute inset-0 bg-gradient-to-r from-primary/50 via-transparent to-transparent lg:from-primary/35"
            aria-hidden
          />

          <div className="absolute top-4 left-4 right-4 flex items-center justify-between gap-3 z-10">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/25 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-white backdrop-blur-md">
              <span className="text-accent">{String(active + 1).padStart(2, "0")}</span>
              <span className="text-white/50">/</span>
              <span className="text-white/80">{String(total).padStart(2, "0")}</span>
              <span className="hidden sm:inline text-white/40">·</span>
              <span className="hidden sm:inline text-white/70">{t("classLabel")}</span>
            </span>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={goPrev}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-black/25 text-white backdrop-blur-md transition-colors hover:bg-white/15"
                aria-label="Previous vehicle"
              >
                <ChevronLeft className="h-4 w-4" aria-hidden />
              </button>
              <button
                type="button"
                onClick={goNext}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-black/25 text-white backdrop-blur-md transition-colors hover:bg-white/15"
                aria-label="Next vehicle"
              >
                <ChevronRight className="h-4 w-4" aria-hidden />
              </button>
            </div>
          </div>

          <div className="absolute bottom-0 left-0 right-0 z-10 p-5 sm:p-7 lg:p-8">
            <motion.div
              key={`meta-${activeKey}`}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.05 }}
            >
              <h3 className="text-2xl sm:text-3xl lg:text-[2rem] font-semibold text-white tracking-tight leading-tight">
                {t(`items.${activeKey}.name`)}
              </h3>
              <p className="mt-2 text-sm sm:text-base text-white/70 leading-relaxed max-w-xl">
                {t(`items.${activeKey}.useCase`)}
              </p>

              {detailed && (
                <div className="mt-5 flex flex-wrap gap-2.5">
                  <div className="inline-flex items-center gap-2 rounded-xl border border-white/12 bg-white/10 px-3.5 py-2.5 backdrop-blur-md">
                    <Weight className="h-4 w-4 text-accent shrink-0" aria-hidden />
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-white/55">
                        {t("payload")}
                      </p>
                      <p className="text-sm font-semibold text-white">
                        {t(`items.${activeKey}.payload`)}
                      </p>
                    </div>
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-xl border border-white/12 bg-white/10 px-3.5 py-2.5 backdrop-blur-md">
                    <Package className="h-4 w-4 text-accent shrink-0" aria-hidden />
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-white/55">
                        {t("cargoSpace")}
                      </p>
                      <p className="text-sm font-semibold text-white">
                        {t(`items.${activeKey}.cargo`)}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        </div>

        {/* Vehicle rail */}
        <div
          className="flex gap-2.5 overflow-x-auto pb-1 snap-x snap-mandatory scrollbar-hide lg:flex-col lg:overflow-y-auto lg:overflow-x-hidden lg:max-h-[min(520px,68vh)] lg:pb-0"
          role="tablist"
          aria-label={t("title")}
        >
          {BUSINESS_FLEET_KEYS.map((key, i) => {
            const isActive = i === active;
            return (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => setActive(i)}
                className={cn(
                  "group relative flex shrink-0 snap-start items-center gap-3 rounded-2xl border p-2.5 text-left transition-all duration-300 min-w-[11.5rem] sm:min-w-[13rem] lg:min-w-0 lg:w-full",
                  isActive
                    ? "border-secondary/30 bg-white shadow-premium ring-1 ring-secondary/10"
                    : "border-primary/8 bg-white/90 hover:border-secondary/20 hover:bg-white hover:shadow-sm"
                )}
              >
                {isActive && (
                  <motion.span
                    layoutId="fleet-active-rail"
                    className="absolute left-0 top-3 bottom-3 w-1 rounded-full bg-gradient-to-b from-secondary to-accent"
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                )}
                <span
                  className={cn(
                    "relative ml-1 h-14 w-14 shrink-0 overflow-hidden rounded-xl border",
                    isActive ? "border-secondary/20" : "border-primary/8"
                  )}
                >
                  {isActive ? (
                    <VehicleIllustration
                      type={FLEET_ILLUSTRATIONS[key]}
                      id={`fleet-thumb-${key}`}
                      mode="photo"
                      className="absolute inset-0"
                    />
                  ) : (
                    <span
                      className="absolute inset-0 bg-gradient-to-br from-primary/8 to-primary/4"
                      aria-hidden
                    />
                  )}
                </span>
                <span className="min-w-0 flex-1 pr-1">
                  <span className="flex items-baseline justify-between gap-2">
                    <span
                      className={cn(
                        "truncate text-sm font-semibold",
                        isActive ? "text-primary" : "text-primary/85"
                      )}
                    >
                      {t(`items.${key}.name`)}
                    </span>
                    <span className="shrink-0 text-[10px] font-bold text-muted/80 tabular-nums">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                  </span>
                  <span className="mt-0.5 block truncate text-xs text-muted">
                    {t(`items.${key}.payload`)}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Capacity ladder */}
      {detailed && (
        <div className="rounded-2xl border border-primary/8 bg-white p-5 sm:p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted mb-4">
            {t("capacityLabel")}
          </p>
          <div className="flex items-end justify-between gap-1 sm:gap-2 h-[4.5rem] sm:h-20">
            {BUSINESS_FLEET_KEYS.map((key, i) => {
              const heightPct = 28 + (i / (total - 1)) * 72;
              const isActive = i === active;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setActive(i)}
                  className="group flex flex-1 flex-col items-center gap-2 min-w-0"
                  aria-label={t(`items.${key}.name`)}
                >
                  <div className="relative w-full flex items-end justify-center h-14 sm:h-16">
                    <div
                      className={cn(
                        "w-full max-w-[2.5rem] rounded-t-lg transition-all duration-300",
                        isActive
                          ? "bg-gradient-to-t from-secondary to-accent shadow-glow-blue"
                          : "bg-primary/10 group-hover:bg-primary/15"
                      )}
                      style={{ height: `${heightPct}%` }}
                    />
                  </div>
                  <span
                    className={cn(
                      "w-full truncate text-center text-[9px] sm:text-[10px] font-medium leading-none",
                      isActive ? "text-secondary font-semibold" : "text-muted"
                    )}
                  >
                    {t(`items.${key}.name`).split(" ")[0]}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {detailed && (
        <div className="flex items-start gap-3 rounded-2xl border border-secondary/15 bg-secondary/[0.06] p-4 sm:p-5 max-w-3xl">
          <Info className="h-4 w-4 text-secondary shrink-0 mt-0.5" aria-hidden />
          <p className="text-sm text-primary/80 leading-relaxed">{t("licenceNote")}</p>
        </div>
      )}
    </div>
  );
}
