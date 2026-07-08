import SiteImage from "@/components/ui/SiteImage";
import { getVehicleImage } from "@/data/site-images";
import { cn } from "@/lib/utils";

export type VehicleIllustrationType =
  "sedan" | "suv" | "pickup" | "cargo-van" | "high-roof" | "box-16" | "box-20";

interface VehicleIllustrationProps {
  type: VehicleIllustrationType;
  className?: string;
  id?: string;
  variant?: "light" | "dark";
  mode?: "photo" | "icon";
}

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
  mode = "photo",
}: VehicleIllustrationProps) {
  const image = getVehicleImage(type);

  if (mode === "photo") {
    return (
      <div className={cn("relative overflow-hidden", className)}>
        <SiteImage
          image={image}
          fill
          className="object-cover"
          sizes="(max-width: 640px) 80vw, 320px"
        />
      </div>
    );
  }

  if (mode === "icon") {
    return (
      <span className={cn("relative inline-block overflow-hidden rounded", className)}>
        <SiteImage image={image} fill className="object-cover" sizes="48px" />
      </span>
    );
  }

  return null;
}
