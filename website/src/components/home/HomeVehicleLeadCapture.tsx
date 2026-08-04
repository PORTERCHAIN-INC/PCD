"use client";

import { motion, useReducedMotion } from "framer-motion";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { FLEET_VEHICLE_ICONS, FLEET_VEHICLE_PHOTOS } from "@/components/shared/FleetVehicleIcon";
import type { FleetVehicleKey } from "@/data/fleet-specs";
import { Link } from "@/i18n/navigation";
import { HUB_FROM } from "@/lib/marketing/config";
import { easeOutExpo } from "@/lib/motion";
import { ANALYTICS_EVENTS, track } from "@/lib/seo/analytics";
import { cn } from "@/lib/utils";

type LeadVehicleId = "sedan" | "van" | "boxTruck";

const LEAD_VEHICLES: {
  id: LeadVehicleId;
  fleetKey: FleetVehicleKey;
  photoKey: FleetVehicleKey;
  vehicleParam: string;
}[] = [
  { id: "sedan", fleetKey: "sedan", photoKey: "sedan", vehicleParam: "sedan" },
  { id: "van", fleetKey: "cargoVan", photoKey: "cargoVan", vehicleParam: "cargo-van" },
  { id: "boxTruck", fleetKey: "box16", photoKey: "box16", vehicleParam: "box-16" },
];

export default function HomeVehicleLeadCapture() {
  const t = useTranslations("homeChooser.vehicleLead");
  const reduce = useReducedMotion();

  function trackVehicle(id: LeadVehicleId) {
    track(ANALYTICS_EVENTS.CTA_CLICK, {
      sourceSection: "home-vehicle-lead",
      from: HUB_FROM.chooser,
      cta_label: `vehicle_${id}`,
    });
  }

  return (
    <div className="mt-8 w-full max-w-md">
      <p className="text-sm font-medium text-white/70">{t("prompt")}</p>
      <div className="mt-4 grid grid-cols-3 gap-2.5 sm:gap-3" role="list">
        {LEAD_VEHICLES.map((vehicle, index) => {
          const photo = FLEET_VEHICLE_PHOTOS[vehicle.photoKey];
          const icon = FLEET_VEHICLE_ICONS[vehicle.fleetKey];
          const href = `/business?from=${HUB_FROM.chooser}&vehicle=${vehicle.vehicleParam}#inquiry`;

          return (
            <motion.div
              key={vehicle.id}
              initial={reduce ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: reduce ? 0 : 0.08 + index * 0.06,
                duration: 0.5,
                ease: easeOutExpo,
              }}
            >
              <Link
                href={href}
                onClick={() => trackVehicle(vehicle.id)}
                className={cn(
                  "group relative flex h-full flex-col overflow-hidden rounded-2xl border border-white/15",
                  "bg-white/[0.08] text-left shadow-[0_8px_32px_-12px_rgba(0,0,0,0.45)]",
                  "backdrop-blur-md transition-[border-color,background-color,box-shadow,transform] duration-300",
                  "hover:-translate-y-1 hover:border-white/35 hover:bg-white/[0.14]",
                  "hover:shadow-[0_16px_40px_-12px_rgba(37,99,235,0.35)]",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:ring-offset-2 focus-visible:ring-offset-primary"
                )}
              >
                <span className="relative aspect-[5/4] w-full overflow-hidden bg-white/90">
                  <Image
                    src={photo}
                    alt=""
                    fill
                    className="object-cover object-center transition-transform duration-500 group-hover:scale-105"
                    sizes="120px"
                  />
                  <span
                    className="absolute inset-0 bg-gradient-to-t from-white/40 via-transparent to-transparent"
                    aria-hidden
                  />
                  <span className="absolute bottom-1.5 left-1.5 flex h-7 w-7 items-center justify-center rounded-lg bg-white/90 shadow-sm sm:h-8 sm:w-8">
                    <span
                      aria-hidden
                      className="block h-4 w-4 bg-primary/80 sm:h-5 sm:w-5"
                      style={{
                        WebkitMaskImage: `url(${icon})`,
                        maskImage: `url(${icon})`,
                        WebkitMaskSize: "contain",
                        maskSize: "contain",
                        WebkitMaskRepeat: "no-repeat",
                        maskRepeat: "no-repeat",
                        WebkitMaskPosition: "center",
                        maskPosition: "center",
                      }}
                    />
                  </span>
                </span>
                <span className="px-2 py-2.5 sm:px-2.5 sm:py-3">
                  <span className="block text-center text-[11px] font-semibold tracking-tight text-white sm:text-xs">
                    {t(`vehicles.${vehicle.id}.name`)}
                  </span>
                  <span className="mt-0.5 block text-center text-[10px] leading-snug text-white/50 sm:text-[11px]">
                    {t(`vehicles.${vehicle.id}.hint`)}
                  </span>
                </span>
              </Link>
            </motion.div>
          );
        })}
      </div>
      <p className="mt-4 text-xs leading-relaxed text-white/45">{t("continueHint")}</p>
    </div>
  );
}
