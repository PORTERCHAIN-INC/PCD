"use client";

import { useRef } from "react";
import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, Info, Check } from "lucide-react";
import SectionHeader from "@/components/ui/SectionHeader";
import Button from "@/components/ui/Button";
import Container from "@/components/ui/Container";
import VehicleIllustration from "@/components/illustrations/VehicleIllustration";
import { vehicles } from "@/data/vehicles";
import { useBooking } from "@/context/BookingContext";
import { cn } from "@/lib/utils";

export default function Vehicles() {
  const t = useTranslations("vehicles");
  const { catalogSelectedId, selectVehicleFromCatalog } = useBooking();
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: "left" | "right") => {
    if (!scrollRef.current) return;
    const amount = direction === "left" ? -340 : 340;
    scrollRef.current.scrollBy({ left: amount, behavior: "smooth" });
  };

  return (
    <section id="pricing" className="site-section bg-white">
      <Container>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between mb-8 sm:mb-10 md:mb-12">
          <SectionHeader
            label={t("label")}
            title={t("title")}
            subtitle={t("subtitle")}
            align="left"
            className="mb-0"
          />
          <p className="text-muted type-small sm:hidden -mt-2">{t("swipeHint")}</p>
          <div className="hidden sm:flex gap-2 shrink-0">
            <button
              onClick={() => scroll("left")}
              className="touch-target w-11 h-11 rounded-xl border border-gray-200 flex items-center justify-center hover:bg-gray-bg transition-colors cursor-pointer"
              aria-label={t("scrollLeft")}
            >
              <ChevronLeft className="w-5 h-5 text-primary" />
            </button>
            <button
              onClick={() => scroll("right")}
              className="touch-target w-11 h-11 rounded-xl border border-gray-200 flex items-center justify-center hover:bg-gray-bg transition-colors cursor-pointer"
              aria-label={t("scrollRight")}
            >
              <ChevronRight className="w-5 h-5 text-primary" />
            </button>
          </div>
        </div>

        <div
          ref={scrollRef}
          className="scroll-bleed flex gap-4 sm:gap-5 overflow-x-auto scrollbar-hide pb-4 snap-x snap-mandatory"
        >
          {vehicles.map((vehicle, i) => {
            const isSelected = catalogSelectedId === vehicle.id;

            return (
              <motion.div
                key={vehicle.id}
                initial={{ opacity: 0, x: 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className={cn(
                  "snap-start shrink-0 w-[min(82vw,280px)] sm:w-[300px] md:w-[320px] rounded-2xl border bg-white shadow-premium overflow-hidden group transition-all duration-300",
                  isSelected
                    ? "border-secondary ring-2 ring-secondary/30 shadow-lg shadow-secondary/15"
                    : "border-gray-200/80 hover:shadow-lg hover:border-secondary/20"
                )}
              >
                <div className="h-44 relative overflow-hidden">
                  <VehicleIllustration
                    type={vehicle.illustration}
                    id={vehicle.id}
                    mode="photo"
                    className="absolute inset-0"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-black/15 to-transparent" />
                </div>

                <div className="p-5 space-y-4">
                  <h3 className="type-h3 font-bold text-primary">
                    {t(`items.${vehicle.id}.name`)}
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="type-caption text-muted">{t("capacity")}</p>
                      <p className="type-small font-medium text-primary mt-0.5">
                        {t(`items.${vehicle.id}.capacity`)}
                      </p>
                    </div>
                    <div>
                      <p className="type-caption text-muted">{t("weight")}</p>
                      <p className="type-small font-medium text-primary mt-0.5">
                        {t(`items.${vehicle.id}.weight`)}
                      </p>
                    </div>
                  </div>
                  <div>
                    <p className="type-caption text-muted">{t("bestFor")}</p>
                    <p className="type-small text-primary/80 mt-0.5 leading-relaxed">
                      {t(`items.${vehicle.id}.bestFor`)}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant={isSelected ? "primary" : "ghost"}
                    size="sm"
                    onClick={() => selectVehicleFromCatalog(vehicle.id)}
                    className={cn(
                      "w-full rounded-xl",
                      isSelected
                        ? "shadow-md shadow-secondary/25"
                        : "border border-gray-200 hover:border-secondary hover:text-secondary"
                    )}
                  >
                    {isSelected ? (
                      <>
                        <Check className="w-4 h-4" />
                        {t("vehicleSelected")}
                      </>
                    ) : (
                      t("selectVehicle")
                    )}
                  </Button>
                </div>
              </motion.div>
            );
          })}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mt-8 flex items-start gap-3 p-4 rounded-xl bg-secondary/5 border border-secondary/10"
        >
          <Info className="w-5 h-5 text-secondary shrink-0 mt-0.5" />
          <p className="type-small text-primary/80 leading-relaxed">
            <span className="font-semibold text-primary">{t("licenceNote")}</span>{" "}
            {t("licenceDetail")}
          </p>
        </motion.div>
      </Container>
    </section>
  );
}
