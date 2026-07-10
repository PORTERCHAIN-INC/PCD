import Image from "next/image";
import type { FleetVehicleKey } from "@/data/fleet-specs";
import { cn } from "@/lib/utils";

/** Rooman12 vehicle pack — https://www.flaticon.com/authors/rooman12 */
export const FLEET_VEHICLE_ICONS: Record<FleetVehicleKey, string> = {
  sedan: "/icons/vehicles/sedan.png",
  suv: "/icons/vehicles/suv.png",
  pickup: "/icons/vehicles/pickup.png",
  cargoVan: "/icons/vehicles/cargo-van.png",
  highRoof: "/icons/vehicles/high-roof.png",
  box16: "/icons/vehicles/box-16.png",
  box20: "/icons/vehicles/box-20.png",
};

type Props = {
  vehicle: FleetVehicleKey;
  className?: string;
  size?: number;
};

export default function FleetVehicleIcon({ vehicle, className, size = 32 }: Props) {
  return (
    <Image
      src={FLEET_VEHICLE_ICONS[vehicle]}
      alt=""
      width={size}
      height={size}
      aria-hidden
      className={cn("shrink-0 object-contain", className)}
    />
  );
}
