import type { FleetVehicleKey } from "@/data/fleet-specs";
import { getVehicleImage } from "@/data/site-images";
import { cn } from "@/lib/utils";

/** Rooman12 vehicle pack — https://www.flaticon.com/authors/rooman12 (mask glyphs for tabs) */
export const FLEET_VEHICLE_ICONS: Record<FleetVehicleKey, string> = {
  sedan: "/icons/vehicles/sedan.png",
  suv: "/icons/vehicles/suv.png",
  pickup: "/icons/vehicles/pickup.png",
  cargoVan: "/icons/vehicles/cargo-van.png",
  highRoof: "/icons/vehicles/high-roof.png",
  box16: "/icons/vehicles/box-16.png",
  box20: "/icons/vehicles/box-20.png",
};

/** Branded photos for fleet showcase — full PorterChain liveries. */
export const FLEET_VEHICLE_PHOTOS: Record<FleetVehicleKey, string> = {
  sedan: getVehicleImage("sedan").src,
  suv: getVehicleImage("suv").src,
  pickup: getVehicleImage("pickup").src,
  cargoVan: getVehicleImage("cargo-van").src,
  highRoof: getVehicleImage("high-roof").src,
  box16: getVehicleImage("box-16").src,
  box20: getVehicleImage("box-20").src,
};

export function fleetVehicleUsesPhoto(_vehicle: FleetVehicleKey): boolean {
  return true;
}

type Props = {
  vehicle: FleetVehicleKey;
  className?: string;
  size?: number;
  active?: boolean;
};

export default function FleetVehicleIcon({ vehicle, className, size = 56, active = false }: Props) {
  const src = FLEET_VEHICLE_ICONS[vehicle];

  return (
    <span
      className={cn(
        "fleet-vehicle-icon inline-flex shrink-0 items-center justify-center transition-all duration-200 drop-shadow-sm",
        active && "scale-110",
        className
      )}
      style={{ width: size, height: size }}
    >
      <span
        aria-hidden
        className={cn(
          "fleet-vehicle-icon__glyph block shrink-0 transition-colors duration-200",
          active ? "bg-white" : "bg-primary/85 group-hover:bg-primary"
        )}
        style={{
          width: size,
          height: size,
          WebkitMaskImage: `url(${src})`,
          maskImage: `url(${src})`,
          WebkitMaskSize: "contain",
          maskSize: "contain",
          WebkitMaskRepeat: "no-repeat",
          maskRepeat: "no-repeat",
          WebkitMaskPosition: "center",
          maskPosition: "center",
        }}
      />
    </span>
  );
}
