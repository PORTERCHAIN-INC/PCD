import Image from "next/image";

export type VehicleIllustrationType =
  | "sedan"
  | "suv"
  | "pickup"
  | "cargo-van"
  | "high-roof"
  | "box-16"
  | "box-20";

type VehicleVariant = "light" | "dark";

interface VehicleIllustrationProps {
  type: VehicleIllustrationType;
  className?: string;
  id?: string;
  variant?: VehicleVariant;
}

const VEHICLE_ICON_SRC: Record<VehicleIllustrationType, string> = {
  sedan: "/icons/vehicles/sedan.png",
  suv: "/icons/vehicles/suv.png",
  pickup: "/icons/vehicles/pickup.png",
  "cargo-van": "/icons/vehicles/cargo-van.png",
  "high-roof": "/icons/vehicles/high-roof.png",
  "box-16": "/icons/vehicles/box-16.png",
  "box-20": "/icons/vehicles/box-20.png",
};

export function resolveVehicleIllustration(key: string): VehicleIllustrationType {
  const map: Record<string, VehicleIllustrationType> = {
    sedan: "sedan",
    suv: "suv",
    pickup: "pickup",
    "cargo-van": "cargo-van",
    cargoVan: "cargo-van",
    "high-roof": "high-roof",
    highRoof: "high-roof",
    "box-16": "box-16",
    box16: "box-16",
    "box-20": "box-20",
    box20: "box-20",
  };
  return map[key] ?? "sedan";
}

export default function VehicleIllustration({
  type,
  className = "",
  variant = "light",
}: VehicleIllustrationProps) {
  const filter =
    variant === "light"
      ? "brightness(0) invert(1)"
      : "brightness(0) saturate(100%)";

  return (
    <Image
      src={VEHICLE_ICON_SRC[type]}
      alt=""
      width={512}
      height={512}
      aria-hidden
      className={className}
      style={{ filter, objectFit: "contain" }}
    />
  );
}
